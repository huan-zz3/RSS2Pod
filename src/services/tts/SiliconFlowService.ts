import axios, { AxiosInstance } from 'axios';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { dirname } from 'path';
import pino from 'pino';
import { TTSService, TTSConfig, TTSResponse, TTSOptions } from '../../shared/types/tts.js';

const logger = pino({ name: 'siliconflow-service' });

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
    const startTime = Date.now();

    const response = await this.client.post('/audio/speech', {
      model: this.config.model,
      input: text,
      voice,
      response_format: 'mp3',
      speed: speed || 1.0,
    }, {
      responseType: 'arraybuffer',
    });

    this.ensureDirectory(outputPath);
    writeFileSync(outputPath, Buffer.from(response.data));

    const duration = this.estimateDuration(text);
    const elapsed = (Date.now() - startTime) / 1000;

    logger.info({ outputPath, duration, elapsed }, 'TTS synthesis completed');

    return {
      audioPath: outputPath,
      duration,
    };
  }

  private async synthesizeSegmented(text: string, outputPath: string, voice: string, speed: number): Promise<TTSResponse> {
    const segments = this.segmentText(text);
    const segmentResponses: TTSResponse[] = [];

    const baseName = outputPath.replace(/\.[^.]+$/, '');

    for (let i = 0; i < segments.length; i++) {
      const segmentPath = `${baseName}_segment_${String(i + 1).padStart(3, '0')}.mp3`;
      const response = await this.synthesizeSingle(segments[i]!, segmentPath, voice, speed);
      segmentResponses.push(response);
    }

    const totalDuration = segmentResponses.reduce((sum, r) => sum + r.duration, 0);

    logger.info({ segments: segments.length, totalDuration }, 'TTS segmented synthesis completed');

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
      
      if (this.estimateDuration(testSegment) > MAX_SEGMENT_DURATION && currentSegment) {
        segments.push(currentSegment);
        currentSegment = paragraph;
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

  private ensureDirectory(filePath: string): void {
    const dir = dirname(filePath);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
  }
}
