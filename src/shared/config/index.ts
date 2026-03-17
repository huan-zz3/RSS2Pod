import { z } from 'zod';
import { readFileSync, existsSync, writeFileSync } from 'fs';
import { dirname } from 'path';
import { fileURLToPath } from 'url';
import pino from 'pino';

const logger = pino({
  name: 'config',
  timestamp: () => `,"time":"${new Date(new Date().getTime() + 8 * 3600 * 1000).toISOString().replace('Z', '+08:00')}"`,
});

const ConfigSchema = z.object({
  database: z.object({
    path: z.string().default('./data/rss2pod.db'),
  }),
  fever: z.object({
    baseUrl: z.string().url(),
    email: z.string(),
    password: z.string(),
  }),
  llm: z.object({
    provider: z.enum(['dashscope', 'openai']).default('dashscope'),
    apiKey: z.string(),
    model: z.string().default('qwen3.5-plus'),
    baseUrl: z.string().optional(),
    maxTokens: z.number().default(2000),
    temperature: z.number().default(0.7),
    prompts: z.object({
      summary: z.object({
        systemRole: z.string().optional(),
        styles: z.record(z.string(), z.object({
          instruction: z.string(),
          requirements: z.array(z.string()).optional(),
        })).optional(),
      }).optional(),
      script: z.object({
        systemRole: z.string().optional(),
        structures: z.record(z.string(), z.object({
          instruction: z.string(),
          format: z.enum(['monologue', 'dialogue']).optional(),
          speakerLabels: z.object({
            en: z.array(z.string()).optional(),
            zh: z.array(z.string()).optional(),
          }).optional(),
        })).optional(),
        learningModes: z.record(z.string(), z.object({
          instruction: z.string(),
          includeTranslations: z.boolean().optional(),
          includeWordExplanations: z.boolean().optional(),
          translationLanguage: z.string().optional(),
        })).optional(),
        requirements: z.array(z.string()).optional(),
      }).optional(),
    }).optional(),
  }),
  tts: z.object({
    provider: z.enum(['siliconflow']).default('siliconflow'),
    apiKey: z.string(),
    model: z.string().default('FunAudioLLM/CosyVoice2-0.5B'),
    voice: z.string().default('claire'),
    baseUrl: z.string().default('https://api.siliconflow.cn/v1'),
  }),
  scheduler: z.object({
    checkInterval: z.number().default(60),
    maxConcurrentGroups: z.number().default(3),
  }),
  sync: z.object({
    enabled: z.boolean().default(true),
    interval: z.number().default(600),
    maxArticlesPerSync: z.number().default(100),
  }),
  pipeline: z.object({
    maxArticlesPerRun: z.number().default(10),
  }),
  logging: z.object({
    level: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  }),
  media: z.object({
    basePath: z.string().default('./data/media'),
    retentionDays: z.number().default(30),
  }),
  api: z.object({
    host: z.string().default('0.0.0.0'),
    port: z.number().default(3000),
    baseUrl: z.string().url().default('http://localhost:3000'),
  }),
});

export type Config = z.infer<typeof ConfigSchema>;

const defaultConfig: Config = {
  database: { path: './data/rss2pod.db' },
  fever: { baseUrl: '', email: '', password: '' },
  llm: { provider: 'dashscope', apiKey: '', model: 'qwen3.5-plus', maxTokens: 2000, temperature: 0.7 },
  tts: { provider: 'siliconflow', apiKey: '', model: 'FunAudioLLM/CosyVoice2-0.5B', voice: 'claire', baseUrl: 'https://api.siliconflow.cn/v1' },
  scheduler: { checkInterval: 60, maxConcurrentGroups: 3 },
  sync: { enabled: true, interval: 600, maxArticlesPerSync: 100 },
  pipeline: { maxArticlesPerRun: 10 },
  logging: { level: 'info' },
  media: { basePath: './data/media', retentionDays: 30 },
  api: { host: '0.0.0.0', port: 3000, baseUrl: 'http://localhost:3000' },
};

export function loadConfig(configPath?: string): Config {
  const path = configPath ?? dirname(fileURLToPath(import.meta.url)) + '/../../../config.json';
  
  if (!existsSync(path)) {
    logger.warn('Config file not found, using defaults');
    return defaultConfig;
  }
  
  const content = readFileSync(path, 'utf-8');
  const parsed = JSON.parse(content);
  
  const merged = {
    ...defaultConfig,
    ...parsed,
    fever: { ...defaultConfig.fever, ...parsed.fever },
    llm: { 
      ...defaultConfig.llm, 
      ...parsed.llm,
      prompts: parsed.llm?.prompts ? {
        summary: parsed.llm.prompts.summary,
        script: parsed.llm.prompts.script,
      } : undefined,
    },
    tts: { ...defaultConfig.tts, ...parsed.tts },
    scheduler: { ...defaultConfig.scheduler, ...parsed.scheduler },
    pipeline: { ...defaultConfig.pipeline, ...parsed.pipeline },
    logging: { ...defaultConfig.logging, ...parsed.logging },
    media: { ...defaultConfig.media, ...parsed.media },
    api: { ...defaultConfig.api, ...parsed.api },
    database: { ...defaultConfig.database, ...parsed.database },
  };
  
  return ConfigSchema.parse(merged);
}

export function saveConfig(config: Config, configPath?: string): void {
  const path = configPath ?? dirname(fileURLToPath(import.meta.url)) + '/../../../config.json';
  
  const safeConfig = {
    ...config,
    fever: { ...config.fever, password: '***REDACTED***' },
    llm: { ...config.llm, apiKey: '***REDACTED***' },
    tts: { ...config.tts, apiKey: '***REDACTED***' },
  };
  
  writeFileSync(path, JSON.stringify(safeConfig, null, 2));
}

export function createConfigTemplate(configPath?: string): void {
  const path = configPath ?? dirname(fileURLToPath(import.meta.url)) + '/../../../config.json.template';
  
  const template = {
    database: { path: './data/rss2pod.db' },
    fever: { baseUrl: 'https://your-ttrss-instance/plugins/fever', email: 'your-email', password: 'your-password' },
    llm: { 
      provider: 'dashscope', 
      apiKey: 'your-dashscope-api-key', 
      model: 'qwen3.5-plus',
      maxTokens: 2000,
      temperature: 0.7,
      // Optional: Custom prompts for LLM
      // prompts: {
      //   summary: {
      //     styles: {
      //       macro: { instruction: 'Focus on high-level trends...', requirements: ['Keep it concise'] },
      //       technical: { instruction: 'Focus on technical details...' },
      //       balanced: { instruction: 'Balance insights and details...' },
      //     }
      //   },
      //   script: {
      //     structures: {
      //       single: { instruction: 'Create a monologue...', format: 'monologue' },
      //       dual: { instruction: 'Create a dialogue...', format: 'dialogue' },
      //     },
      //     learningModes: {
      //       normal: { instruction: 'Natural English without translations' },
      //       word_explanation: { instruction: 'Explain difficult words after sentences' },
      //       sentence_translation: { instruction: 'Provide Chinese translation after each sentence' },
      //     },
      //     requirements: ['Start with introduction', 'End with conclusion'],
      //   }
      // }
    },
    tts: { provider: 'siliconflow', apiKey: 'your-siliconflow-api-key', model: 'FunAudioLLM/CosyVoice2-0.5B', voice: 'claire', baseUrl: 'https://api.siliconflow.cn/v1' },
    scheduler: { checkInterval: 60, maxConcurrentGroups: 3 },
    pipeline: { maxArticlesPerRun: 10 },
    logging: { level: 'info' },
    media: { basePath: './data/media', retentionDays: 30 },
    api: { 
      host: '0.0.0.0', 
      port: 3000,
      baseUrl: 'http://localhost:3000',
    },
  };
  
  writeFileSync(path, JSON.stringify(template, null, 2));
}

let configInstance: Config | null = null;

export function getConfig(): Config {
  if (!configInstance) {
    configInstance = loadConfig();
  }
  return configInstance;
}

export function resetConfig(): void {
  configInstance = null;
}
