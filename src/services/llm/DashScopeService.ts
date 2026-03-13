import axios, { AxiosInstance } from 'axios';
import pino from 'pino';
import { LLMService, LLMConfig, LLMResponse, SummaryOptions, ScriptOptions } from '../../shared/types/llm.js';

const logger = pino({ name: 'dashscope-service' });

export class DashScopeService implements LLMService {
  private client: AxiosInstance;
  private config: LLMConfig;

  constructor(config: LLMConfig) {
    this.config = config;
    this.client = axios.create({
      baseURL: config.baseUrl || 'https://dashscope.aliyuncs.com/api/v1',
      timeout: 60000,
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
    const maxRetries = 3;
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const response = await this.client.post('/services/aigc/text-generation/generation', {
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
        });

        const content = response.data?.output?.text || '';
        const usage = response.data?.usage;

        logger.info({ model: this.config.model, tokens: usage?.total_tokens }, 'LLM request completed');

        return {
          content,
          usage: usage ? {
            promptTokens: usage.input_tokens,
            completionTokens: usage.output_tokens,
            totalTokens: usage.total_tokens,
          } : undefined,
        };
      } catch (error: unknown) {
        lastError = error instanceof Error ? error : new Error(String(error));
        
        if (axios.isAxiosError(error)) {
          const status = error.response?.status;
          
          if (status === 429) {
            const waitTime = Math.pow(2, attempt - 1) * 1000;
            logger.warn({ attempt, waitTime }, 'Rate limited, retrying...');
            await this.sleep(waitTime);
            continue;
          }
          
          if (status && status >= 400 && status < 500) {
            logger.error({ status, data: error.response?.data }, 'LLM API error');
            throw new Error(`LLM API error: ${status}`);
          }
        }

        if (attempt < maxRetries) {
          const waitTime = Math.pow(2, attempt - 1) * 1000;
          logger.warn({ attempt, error: lastError.message, waitTime }, 'Retrying...');
          await this.sleep(waitTime);
        }
      }
    }

    throw lastError || new Error('LLM request failed after retries');
  }

  private buildSummaryPrompt(text: string, sourceName?: string, articleCount?: number, style?: string): string {
    const styleInstructions: Record<string, string> = {
      macro: 'Focus on high-level trends, themes, and implications. Avoid technical details.',
      technical: 'Focus on technical details, implementations, and specific technologies mentioned.',
      balanced: 'Balance between high-level insights and important technical details.',
    };

    const instruction = styleInstructions[style || 'balanced'];

    return `Generate a concise summary of the following ${articleCount || 'multiple'} article${articleCount !== 1 ? 's' : ''}${sourceName ? ` from ${sourceName}` : ''}.

${instruction}

Requirements:
- Keep it concise (300-500 words)
- Highlight key points and main themes
- Maintain logical flow
- Use clear, accessible language

Articles:
${text}

Summary:`;
  }

  private buildScriptPrompt(context: string, options?: ScriptOptions): string {
    const structure = options?.groupStructure || 'single';
    const learningMode = options?.learningMode || 'normal';

    const structureInstructions = structure === 'dual'
      ? 'Create a dialogue between two hosts (Host and Guest) with natural conversation flow, alternating speakers every 2-3 paragraphs.'
      : 'Create a monologue script for a single host delivering news in a clear, engaging manner.';

    const learningInstructions = {
      normal: 'Deliver content in natural English without translations.',
      word_explanation: 'After complex sentences, briefly explain difficult words or phrases in simple terms.',
      sentence_translation: 'After each sentence, provide a natural Chinese translation before continuing.',
    };

    return `Create a podcast script based on the following content summary.

Format: ${structureInstructions}
Learning Mode: ${learningInstructions[learningMode]}

Requirements:
- Start with a brief introduction/welcome
- Cover all key points from the summary
- Use conversational, engaging language
- Include natural transitions between topics
- End with a brief conclusion
- Keep total length appropriate for 5-10 minute read

Content Summary:
${context}

Podcast Script:`;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
