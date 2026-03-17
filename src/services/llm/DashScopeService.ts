import axios, { AxiosInstance } from 'axios';
import pino from 'pino';
import { LLMService, LLMConfig, LLMResponse, SummaryOptions, ScriptOptions } from '../../shared/types/llm.js';

const logger = pino({
  name: 'dashscope-service',
  timestamp: () => `,"time":"${new Date(new Date().getTime() + 8 * 3600 * 1000).toISOString().replace('Z', '+08:00')}"`,
});

export class DashScopeService implements LLMService {
  private client: AxiosInstance;
  private config: LLMConfig;

  constructor(config: LLMConfig) {
    this.config = config;
    this.client = axios.create({
      baseURL: config.baseUrl || 'https://dashscope.aliyuncs.com/api/v1',
      timeout: 120000, // 120 秒超时，适应长内容处理
      headers: {
        'Authorization': `Bearer ${config.apiKey}`,
        'Content-Type': 'application/json',
      },
    });
  }

  async generateSummary(text: string, options?: SummaryOptions): Promise<LLMResponse> {
    const style = options?.style || 'balanced';
    const prompt = this.buildSummaryPrompt(text, options?.sourceName, options?.articleCount, style);
    
    return this.callLLM(prompt);
  }

  async generateScript(context: string, options?: ScriptOptions): Promise<LLMResponse> {
    const prompt = this.buildScriptPrompt(context, options);
    return this.callLLM(prompt);
  }

  async testConnection(): Promise<boolean> {
    try {
      const response = await this.callLLM('Hello', { maxTokens: 10 });
      return response.content.length > 0;
    } catch {
      return false;
    }
  }

  private async callLLM(prompt: string, overrides?: { maxTokens?: number }): Promise<LLMResponse> {
    const maxRetries = 5;
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        // Check if using OpenAI-compatible endpoint (SiliconFlow or DashScope OpenAI-compatible)
        const isOpenAICompatible = this.config.baseUrl?.includes('siliconflow') || 
                                   this.config.baseUrl?.includes('/v1/chat/completions');
        
        const requestBody = isOpenAICompatible
          ? {
              model: this.config.model,
              messages: [
                { role: 'system', content: 'You are a helpful assistant for podcast content generation.' },
                { role: 'user', content: prompt },
              ],
              max_tokens: overrides?.maxTokens || this.config.maxTokens || 2000,
              temperature: this.config.temperature || 0.7,
            }
          : {
              model: this.config.model,
              input: {
                messages: [
                  { role: 'system', content: 'You are a helpful assistant for podcast content generation.' },
                  { role: 'user', content: prompt },
                ],
              },
              parameters: {
                max_tokens: overrides?.maxTokens || this.config.maxTokens || 2000,
                temperature: this.config.temperature || 0.7,
              },
            };

        const endpoint = isOpenAICompatible ? '' : '/services/aigc/text-generation/generation';
        const response = await this.client.post(endpoint, requestBody);

        let content: string;
        let usage: any;

        if (isOpenAICompatible) {
          content = response.data?.choices?.[0]?.message?.content || '';
          usage = response.data?.usage;
        } else {
          content = response.data?.output?.text || '';
          usage = response.data?.usage;
        }

        logger.info({ model: this.config.model, tokens: usage?.total_tokens }, 'LLM request completed');

        return {
          content,
          usage: usage ? {
            promptTokens: usage.prompt_tokens,
            completionTokens: usage.completion_tokens,
            totalTokens: usage.total_tokens,
          } : undefined,
        };
      } catch (error: unknown) {
        lastError = error instanceof Error ? error : new Error(String(error));
        
        if (axios.isAxiosError(error)) {
          const status = error.response?.status;
          
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
          
          if (status && status >= 400 && status < 500) {
            logger.error({ status, data: error.response?.data }, 'LLM API error');
            throw new Error(`LLM API error: ${status}`);
          }
        }

        if (attempt < maxRetries) {
          const waitTime = Math.pow(2, attempt) * 2000;
          logger.warn({ attempt, error: lastError.message, waitTime }, 'Retrying...');
          await this.sleep(waitTime);
        }
      }
    }

    throw lastError || new Error('LLM request failed after retries');
  }

  private buildSummaryPrompt(text: string, sourceName?: string, articleCount?: number, style?: string): string {
    const selectedStyle = style || 'balanced';
    
    const configuredStyles = this.config.prompts?.summary?.styles;
    const styleConfig = configuredStyles?.[selectedStyle];
    
    const instruction = styleConfig?.instruction ?? this.getDefaultStyleInstruction(selectedStyle);
    const requirements = styleConfig?.requirements ?? this.getDefaultStyleRequirements();

    return `Generate a concise summary of the following ${articleCount || 'multiple'} article${articleCount !== 1 ? 's' : ''}${sourceName ? ` from ${sourceName}` : ''}.

${instruction}

${requirements.length > 0 ? 'Requirements:\n- ' + requirements.join('\n- ') + '\n' : ''}
Articles:
${text}

Summary:`;
  }

  private getDefaultStyleInstruction(style: string): string {
    if (style === 'macro') return 'Focus on high-level trends, themes, and implications. Avoid technical details.';
    if (style === 'technical') return 'Focus on technical details, implementations, and specific technologies mentioned.';
    return 'Balance between high-level insights and important technical details.';
  }

  private getDefaultStyleRequirements(): string[] {
    return [
      'Keep it concise (300-500 words)',
      'Highlight key points and main themes',
      'Maintain logical flow',
      'Use clear, accessible language',
    ];
  }

  private buildScriptPrompt(context: string, options?: ScriptOptions): string {
    const structure = options?.groupStructure || 'single';
    const learningMode = options?.learningMode || 'normal';

    const structureInstructions = this.getStructureInstruction(structure);
    const learningInstructions = this.getLearningModeInstruction(learningMode);
    const requirements = this.getScriptRequirements();

    return `Create a podcast script based on the following content summary.

Format: ${structureInstructions}
Learning Mode: ${learningInstructions}

${requirements.length > 0 ? 'Requirements:\n- ' + requirements.join('\n- ') + '\n' : ''}
Content Summary:
${context}

Podcast Script:`;
  }

  private getStructureInstruction(structure: string): string {
    const configured = this.config.prompts?.script?.structures?.[structure];
    if (configured?.instruction) return configured.instruction;
    
    if (structure === 'dual') {
      return 'Create a dialogue between two hosts (Host and Guest) with natural conversation flow, alternating speakers every 2-3 paragraphs.';
    }
    return 'Create a monologue script for a single host delivering news in a clear, engaging manner.';
  }

  private getLearningModeInstruction(learningMode: string): string {
    const configured = this.config.prompts?.script?.learningModes?.[learningMode];
    if (configured?.instruction) return configured.instruction;
    
    if (learningMode === 'word_explanation') {
      return 'After complex sentences, briefly explain difficult words or phrases in simple terms.';
    }
    if (learningMode === 'sentence_translation') {
      return 'After each sentence, provide a natural Chinese translation before continuing.';
    }
    return 'Deliver content in natural English without translations.';
  }

  private getScriptRequirements(): string[] {
    const configured = this.config.prompts?.script?.requirements;
    if (configured && configured.length > 0) return configured;
    
    return [
      'Start with a brief introduction/welcome',
      'Cover all key points from the summary',
      'Use conversational, engaging language',
      'Include natural transitions between topics',
      'End with a brief conclusion',
      'Keep total length appropriate for 5-10 minute read',
    ];
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
