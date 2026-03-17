import axios, { AxiosInstance } from 'axios';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import pino from 'pino';
import { formatLogText } from '../../shared/utils/logger.js';
import { TTSService, TTSConfig, TTSResponse, TTSOptions } from '../../shared/types/tts.js';

const logger = pino({
  name: 'siliconflow-service',
  timestamp: () => `,"time":"${new Date(new Date().getTime() + 8 * 3600 * 1000).toISOString().replace('Z', '+08:00')}"`,
});

const MAX_SEGMENT_DURATION = 163; // 2:43 in seconds

export class SiliconFlowService implements TTSService {
  private client: AxiosInstance;
  private config: TTSConfig;

  constructor(config: TTSConfig) {
    this.config = config;
    this.client = axios.create({
      baseURL: config.baseUrl,
      timeout: 120000,
      headers: {
        'Authorization': `Bearer ${config.apiKey}`,
        'Content-Type': 'application/json',
      },
    });
  }

  async synthesize(text: string, outputPath: string, options?: TTSOptions): Promise<TTSResponse> {
    const voice = options?.voice || this.config.voice;
    const speed = options?.speed || 1.0;

    if (options?.segment || this.estimateDuration(text) > MAX_SEGMENT_DURATION) {
      return this.synthesizeSegmented(text, outputPath, voice, speed);
    }

    return this.synthesizeSingle(text, outputPath, voice, speed);
  }

  async testConnection(): Promise<boolean> {
    try {
      const response = await this.client.post('/audio/speech', {
        model: this.config.model,
        input: 'Hello',
        voice: this.config.voice,
        response_format: 'mp3',
      }, {
        responseType: 'arraybuffer',
      });

      return response.status === 200 && response.data.byteLength > 0;
    } catch {
      return false;
    }
  }

  private async synthesizeSingle(text: string, outputPath: string, voice: string, speed: number): Promise<TTSResponse> {
    const maxRetries = 5;
    let lastError: Error | null = null;
    const textPreview = text.length > 100 ? text.substring(0, 100) + '...' : text;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const startTime = Date.now();

        const response = await this.client.post('/audio/speech', {
          model: this.config.model,
          input: text,
          voice,
          response_format: 'mp3',
          speed: speed || 1.0,
        }, {
          responseType: 'arraybuffer',
          timeout: 120000,
        });

        if (response.status !== 200) {
          logger.error({ status: response.status, statusText: response.statusText }, 'TTS API returned non-200 status');
          throw new Error(`TTS API returned status ${response.status}: ${response.statusText}`);
        }

        this.ensureDirectory(outputPath);
        writeFileSync(outputPath, Buffer.from(response.data));

        const duration = this.estimateDuration(text);
        const elapsed = (Date.now() - startTime) / 1000;

        logger.info({ outputPath, duration, elapsed, textLength: text.length }, 'TTS synthesis completed');

        return {
          audioPath: outputPath,
          duration,
        };
      } catch (error: any) {
        lastError = error instanceof Error ? error : new Error(String(error));
        
        if (axios.isAxiosError(error)) {
          const status = error.response?.status;
          
          // Handle 429 Rate Limiting
          if (status === 429) {
            // Check for Retry-After header
            const retryAfter = error.response?.headers?.['retry-after'];
            let waitTime: number;
            
            if (retryAfter) {
              waitTime = parseInt(retryAfter, 10) * 1000;
              logger.warn({ attempt, retryAfter, waitTime }, 'Rate limited, respecting Retry-After header');
            } else {
              // Exponential backoff: 2^attempt * 2000ms (2s, 4s, 8s, 16s, 32s)
              waitTime = Math.pow(2, attempt) * 2000;
              logger.warn({ attempt, waitTime }, 'Rate limited, applying exponential backoff');
            }
            
            if (attempt < maxRetries) {
              await this.sleep(waitTime);
              continue;
            }
          }
          
          // Handle other 4xx errors (don't retry)
          if (status && status >= 400 && status < 500) {
            logger.error({ 
              status, 
              data: error.response?.data?.toString(),
              textPreview,
              textLength: text.length,
              model: this.config.model,
              voice 
            }, 'TTS API client error');
            throw new Error(`TTS API error: ${status}`);
          }
        }

        // Retry for 5xx errors or network errors
        if (attempt < maxRetries) {
          const waitTime = Math.pow(2, attempt) * 2000;
          logger.warn({ 
            attempt, 
            error: lastError.message, 
            waitTime,
            textPreview 
          }, 'Retrying TTS request...');
          await this.sleep(waitTime);
        }
      }
    }

    logger.error({ 
      error: lastError?.message, 
      textPreview,
      textLength: text.length,
      model: this.config.model,
      voice,
      attempts: maxRetries
    }, 'TTS synthesis failed after all retries');
    throw lastError || new Error('TTS synthesis failed after retries');
  }

  private async synthesizeSegmented(text: string, outputPath: string, voice: string, speed: number): Promise<TTSResponse> {
    const segments = this.segmentText(text);
    const segmentResponses: TTSResponse[] = [];
    const segmentPaths: string[] = [];

    const baseName = outputPath.replace(/\.[^.]+$/, '');

    logger.info({ totalSegments: segments.length, textLength: text.length }, 'Starting segmented TTS synthesis');

    for (let i = 0; i < segments.length; i++) {
      const segmentPath = `${baseName}_segment_${String(i + 1).padStart(3, '0')}.mp3`;
      try {
        const response = await this.synthesizeSingle(segments[i]!, segmentPath, voice, speed);
        segmentResponses.push(response);
        segmentPaths.push(segmentPath);
      logger.info({ 
        segment: i + 1, 
        total: segments.length,
        duration: response.duration,
        path: segmentPath,
        preview: formatLogText(segments[i]!, { maxLength: 100, preserveNewlines: false })
      }, `Segment ${i + 1}/${segments.length} synthesized`);
      } catch (error) {
        logger.error({ segment: i + 1, error }, `Failed to synthesize segment ${i + 1}`);
        throw new Error(`TTS segment ${i + 1} failed: ${error instanceof Error ? error.message : error}`);
      }
    }

    // Merge all segments using ffmpeg
    await this.mergeAudioSegments(segmentPaths, outputPath);

    const totalDuration = segmentResponses.reduce((sum, r) => sum + r.duration, 0);

    logger.info({ 
      segments: segments.length, 
      totalDuration,
      outputPath 
    }, 'TTS segmented synthesis completed');

    return {
      audioPath: outputPath,
      duration: totalDuration,
      segments: segmentResponses,
    };
  }

  private segmentText(text: string): string[] {
    const paragraphs = text.split(/\n\n+/).filter(p => p.trim().length > 0);
    const segments: string[] = [];
    let currentSegment = '';

    for (const paragraph of paragraphs) {
      const testSegment = currentSegment ? `${currentSegment}\n\n${paragraph}` : paragraph;
      const estimatedDuration = this.estimateDuration(testSegment);
      
      if (estimatedDuration > MAX_SEGMENT_DURATION && currentSegment) {
        segments.push(currentSegment);
        currentSegment = paragraph;
      } else if (estimatedDuration > MAX_SEGMENT_DURATION && !currentSegment) {
        const sentences = paragraph.match(/[^.!?]+[.!?]+/g) || [paragraph];
        let sentenceSegment = '';
        
        for (const sentence of sentences) {
          const testSentence = sentenceSegment ? `${sentenceSegment} ${sentence}` : sentence;
          if (this.estimateDuration(testSentence) > MAX_SEGMENT_DURATION && sentenceSegment) {
            segments.push(sentenceSegment);
            sentenceSegment = sentence;
          } else {
            sentenceSegment = testSentence;
          }
        }
        
        if (sentenceSegment) {
          currentSegment = sentenceSegment;
        }
      } else {
        currentSegment = testSegment;
      }
    }

    if (currentSegment) {
      segments.push(currentSegment);
    }

    return segments.length > 0 ? segments : [text];
  }

  private estimateDuration(text: string): number {
    const words = text.split(/\s+/).length;
    const wordsPerMinute = 150;
    return Math.ceil((words / wordsPerMinute) * 60);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private ensureDirectory(filePath: string): void {
    const dir = dirname(filePath);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
  }

  private async mergeAudioSegments(segmentPaths: string[], outputPath: string): Promise<void> {
    const { exec } = await import('child_process');
    const { writeFileSync, mkdirSync } = await import('fs');
    const { dirname } = await import('path');
    
    const outputDir = dirname(outputPath);
    const fileListPath = join(outputDir, 'segments.txt');
    const fileListContent = segmentPaths.map(p => `file '${p.replace(/'/g, "'\\''")}'`).join('\n');
    
    mkdirSync(outputDir, { recursive: true });
    writeFileSync(fileListPath, fileListContent);
    
    logger.info({ fileListPath, segments: segmentPaths.length }, 'Merging audio segments with ffmpeg');
    
    return new Promise((resolve, reject) => {
      const cmd = `ffmpeg -y -f concat -safe 0 -i "${fileListPath}" -c copy "${outputPath}"`;
      exec(cmd, (error, _stdout, stderr) => {
        if (error) {
          logger.error({ error, stderr, fileListPath, segments: segmentPaths }, 'FFmpeg merge failed');
          reject(new Error(`FFmpeg merge failed: ${stderr}`));
        } else {
          logger.info({ segments: segmentPaths.length, outputPath, duration: this.parseFFmpegDuration(stderr) }, 'Audio segments merged successfully');
          resolve();
        }
      });
    });
  }

  private parseFFmpegDuration(stderr: string): number {
    const match = stderr.match(/time=(\d+):(\d+):(\d+)/);
    if (match?.[1] && match?.[2] && match?.[3]) {
      return parseInt(match[1]) * 3600 + parseInt(match[2]) * 60 + parseInt(match[3]);
    }
    return 0;
  }
}
