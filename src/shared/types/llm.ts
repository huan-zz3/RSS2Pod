export interface LLMConfig {
  provider: 'dashscope' | 'openai';
  apiKey: string;
  model: string;
  baseUrl?: string;
  maxTokens?: number;
  temperature?: number;
  prompts?: PromptConfig;
}

export interface PromptConfig {
  summary?: SummaryPromptConfig;
  script?: ScriptPromptConfig;
}

export interface SummaryPromptConfig {
  systemRole?: string;
  styles?: Record<string, PromptStyleConfig>;
}

export interface ScriptPromptConfig {
  systemRole?: string;
  structures?: Record<string, PromptStructureConfig>;
  learningModes?: Record<string, PromptLearningModeConfig>;
  requirements?: string[];
}

export interface PromptStyleConfig {
  instruction: string;
  requirements?: string[];
}

export interface PromptStructureConfig {
  instruction: string;
  format?: 'monologue' | 'dialogue';
  speakerLabels?: {
    en?: string[];
    zh?: string[];
  };
}

export interface PromptLearningModeConfig {
  instruction: string;
  includeTranslations?: boolean;
  includeWordExplanations?: boolean;
  translationLanguage?: string;
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
