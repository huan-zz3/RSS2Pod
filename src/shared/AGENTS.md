# Shared Module Knowledge Base

## Overview

共享工具：TypeScript 类型定义、Zod 配置验证、日志工具函数。为整个项目提供基础类型和配置支持。

## Structure

```
shared/
├── config/
│   └── index.ts          # Zod schema 配置验证
├── types/
│   ├── events.ts         # 事件总线类型定义
│   ├── feed.ts           # RSS/播客 Feed 类型
│   ├── llm.ts            # LLM 服务类型
│   └── tts.ts            # TTS 服务类型
└── utils/
    ├── index.ts          # 工具函数导出
    └── logger.ts         # Pino 日志配置
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 添加新类型 | `types/` 目录 | 新建 `.ts` 文件或在现有文件中添加 |
| 修改配置验证 | `config/index.ts` | 更新 Zod schema |
| 添加配置项 | `config/index.ts` | 在 schema 中添加字段，更新默认值 |
| 修改日志格式 | `utils/logger.ts` | 调整 pino 配置 |

## 类型定义模式

**事件类型** (`types/events.ts`)：
```typescript
export type EventType =
  | 'pipeline:started'
  | 'pipeline:completed'
  | 'pipeline:failed'
  | 'stage:started'
  | 'stage:completed';

export interface AppEvent<T = unknown> {
  id: string;
  type: EventType;
  payload: T;
  timestamp: number;
}
```

**LLM 类型** (`types/llm.ts`)：
```typescript
export interface LLMConfig {
  provider: 'dashscope';
  apiKey: string;
  model: string;
}

export interface LLMResponse {
  content: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
  };
}
```

**TTS 类型** (`types/tts.ts`)：
```typescript
export interface TTSConfig {
  provider: 'siliconflow';
  apiKey: string;
  model: string;
  voice: string;
}

export interface TTSSegment {
  text: string;
  audioPath: string;
  duration: number;
}
```

## 配置验证模式

**Zod Schema** (`config/index.ts`)：
```typescript
const FeverConfigSchema = z.object({
  baseUrl: z.string().url(),
  email: z.string().email(),
  password: z.string().min(1),
});

const AppConfigSchema = z.object({
  fever: FeverConfigSchema,
  llm: LLMConfigSchema,
  tts: TTSConfigSchema,
  // ...
});

export function loadConfig(): z.infer<typeof AppConfigSchema> {
  const configPath = path.resolve(process.cwd(), 'config.json');
  const raw = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  return AppConfigSchema.parse(raw);
}
```

## 日志配置

**Pino Logger** (`utils/logger.ts`)：
```typescript
const logger = pino({
  name: 'rss2pod',
  level: config?.logging?.level || 'info',
  timestamp: () => `,"time":"${new Date().toISOString().replace('Z', '+08:00')}"`,
  transport: {
    target: 'pino-pretty',
    options: { colorize: true },
  },
});
```

## 代码约定

- **类型导出** - 使用 `export interface` 和 `export type`
- **配置验证** - 所有外部配置必须通过 Zod schema 验证
- **日志统一** - 所有模块使用 `shared/utils/logger.ts` 导出的 logger
- **类型导入** - 使用 `import type` 导入纯类型

## 反模式

- ❌ 不要使用 `any` 类型 - 使用明确的接口或 `unknown`
- ❌ 不要跳过配置验证 - 必须使用 `loadConfig()` 和 Zod schema
- ❌ 不要直接使用 `console.log` - 使用 pino logger
- ❌ 不要在类型文件中放置运行时逻辑 - 仅类型定义

## 独特风格

- **UTC+8 时间戳** - 所有日志时间戳转换为北京时间
- **Zod 推导类型** - 使用 `z.infer<typeof Schema>` 从 schema 推导类型
- **事件驱动类型安全** - `AppEvent<T>` 泛型确保事件 payload 类型安全

## 与其他模块的关系

| 模块 | 依赖 shared 的内容 |
|------|-------------------|
| `features/` | `types/events.ts`, `utils/logger.ts` |
| `services/` | `types/llm.ts`, `types/tts.ts`, `config/index.ts` |
| `infrastructure/` | `utils/logger.ts`, `config/index.ts` |
| `repositories/` | `types/` 中的实体类型 |
