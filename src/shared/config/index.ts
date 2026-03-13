import { z } from 'zod';
import { readFileSync, existsSync, writeFileSync } from 'fs';
import { dirname } from 'path';
import { fileURLToPath } from 'url';
import pino from 'pino';

const logger = pino({ name: 'config' });

const ConfigSchema = z.object({
  database: z.object({
    path: z.string().default('./data/rss2pod.db'),
  }),
  fever: z.object({
    baseUrl: z.string().url(),
    email: z.string().email(),
    password: z.string(),
  }),
  llm: z.object({
    provider: z.enum(['dashscope', 'openai']).default('dashscope'),
    apiKey: z.string(),
    model: z.string().default('qwen3.5-plus'),
    baseUrl: z.string().optional(),
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
  logging: z.object({
    level: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  }),
  media: z.object({
    basePath: z.string().default('./data/media'),
    retentionDays: z.number().default(30),
  }),
  server: z.object({
    host: z.string().default('0.0.0.0'),
    port: z.number().default(3000),
  }),
});

export type Config = z.infer<typeof ConfigSchema>;

const defaultConfig: Config = {
  database: { path: './data/rss2pod.db' },
  fever: { baseUrl: '', email: '', password: '' },
  llm: { provider: 'dashscope', apiKey: '', model: 'qwen3.5-plus' },
  tts: { provider: 'siliconflow', apiKey: '', model: 'FunAudioLLM/CosyVoice2-0.5B', voice: 'claire', baseUrl: 'https://api.siliconflow.cn/v1' },
  scheduler: { checkInterval: 60, maxConcurrentGroups: 3 },
  logging: { level: 'info' },
  media: { basePath: './data/media', retentionDays: 30 },
  server: { host: '0.0.0.0', port: 3000 },
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
    llm: { ...defaultConfig.llm, ...parsed.llm },
    tts: { ...defaultConfig.tts, ...parsed.tts },
    scheduler: { ...defaultConfig.scheduler, ...parsed.scheduler },
    logging: { ...defaultConfig.logging, ...parsed.logging },
    media: { ...defaultConfig.media, ...parsed.media },
    server: { ...defaultConfig.server, ...parsed.server },
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
    llm: { provider: 'dashscope', apiKey: 'your-dashscope-api-key', model: 'qwen3.5-plus' },
    tts: { provider: 'siliconflow', apiKey: 'your-siliconflow-api-key', model: 'FunAudioLLM/CosyVoice2-0.5B', voice: 'claire', baseUrl: 'https://api.siliconflow.cn/v1' },
    scheduler: { checkInterval: 60, maxConcurrentGroups: 3 },
    logging: { level: 'info' },
    media: { basePath: './data/media', retentionDays: 30 },
    server: { host: '0.0.0.0', port: 3000 },
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
