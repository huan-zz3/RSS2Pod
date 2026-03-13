export interface LLMConfig {
  provider: 'dashscope' | 'openai';
  apiKey: string;
  model: string;
  baseUrl?: string;
  maxTokens?: number;
  temperature?: number;
}

export interface LLMResponse {
  content: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export interface LLMService {
  generateSummary(text: string, options?: SummaryOptions): Promise<LLMResponse>;
  generateScript(context: string, options?: ScriptOptions): Promise<LLMResponse>;
  testConnection(): Promise<boolean>;
}

export interface SummaryOptions {
  sourceName?: string;
  articleCount?: number;
  style?: 'macro' | 'technical' | 'balanced';
}

export interface ScriptOptions {
  groupStructure?: 'single' | 'dual';
  learningMode?: 'normal' | 'word_explanation' | 'sentence_translation';
  hostName?: string;
  guestName?: string;
}
