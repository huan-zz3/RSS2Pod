# Services Knowledge Base

## Overview

外部服务集成：LLM (DashScope)、TTS (SiliconFlow)、播客 Feed 生成。提供 AI 能力和内容输出功能。

## Structure

```
services/
├── llm/
│   ├── DashScopeService.ts    # LLM 集成 (DashScope API)
│   └── index.ts
├── tts/
│   ├── SiliconFlowService.ts  # TTS 集成 (SiliconFlow API)
│   └── index.ts
└── feed/
    ├── PodcastFeedGenerator.ts # RSS Feed 生成
    ├── validate.ts             # Feed 验证工具
    └── index.ts
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 修改 LLM 提示词 | `llm/DashScopeService.ts` (`buildSummaryPrompt`, `buildScriptPrompt`) | 调整 Prompt 模板 |
| 更改 TTS 声音 | `tts/SiliconFlowService.ts` (构造函数配置) | 修改 voice 参数 |
| 调整音频分段 | `tts/SiliconFlowService.ts` (`segmentText` 方法) | 修改分段逻辑 |
| 修改 Feed 格式 | `feed/PodcastFeedGenerator.ts` | 调整 RSS/iTunes 标签 |
| 添加新服务 | `services/` 目录 | 遵循现有服务模式 |

## 服务接口模式

**LLM 服务接口**：
```typescript
export interface LLMService {
  generateSummary(text: string, options?: SummaryOptions): Promise<LLMResponse>;
  generateScript(context: string, options?: ScriptOptions): Promise<LLMResponse>;
  testConnection(): Promise<boolean>;
}

export class DashScopeService implements LLMService {
  private client: AxiosInstance;
  private config: LLMConfig;
  
  constructor(config: LLMConfig) {
    this.config = config;
    this.client = axios.create({ /* ... */ });
  }
}
```

**TTS 服务接口**：
```typescript
export interface TTSService {
  synthesize(text: string, outputPath: string): Promise<TTSResult>;
  testConnection(): Promise<boolean>;
}

export class SiliconFlowService implements TTSService {
  private config: TTSConfig;
  
  async synthesize(text: string, outputPath: string): Promise<TTSResult> {
    // 自动分段超过 2:43 的文本
    const segments = this.segmentText(text);
    // 分别合成每段
    // 合并音频文件
  }
}
```

## LLM 服务详情

**DashScopeService** (`llm/DashScopeService.ts`)：
- **模型**: Qwen/Qwen2.5-72B-Instruct-128K
- **重试策略**: 5 次重试，指数退避 (2s 基础)
- **429 处理**: 检测到速率限制时额外等待
- **日志记录**: 记录所有请求和响应

**提示词构建**：
```typescript
private buildSummaryPrompt(articles: Article[]): string {
  return `你是一名专业的新闻摘要助手。请为以下文章生成简洁的摘要：

${articles.map(a => `## ${a.title}\n${a.content}`).join('\n\n')}

要求：
1. 提取关键信息
2. 保持客观中立
3. 控制在 500 字以内
`;
}
```

## TTS 服务详情

**SiliconFlowService** (`tts/SiliconFlowService.ts`)：
- **模型**: FunAudioLLM/CosyVoice2-0.5B
- **声音**: claire (可配置)
- **分段限制**: 每段不超过 2:43 (163 秒)
- **输出格式**: MP3, 44.1kHz, 128kbps

**文本分段逻辑**：
```typescript
private segmentText(text: string): string[] {
  const MAX_DURATION = 163; // 2:43 in seconds
  const CHARS_PER_SECOND = 15; // 估算
  const MAX_CHARS = MAX_DURATION * CHARS_PER_SECOND;
  
  const segments: string[] = [];
  let current = '';
  
  for (const paragraph of text.split('\n\n')) {
    if (current.length + paragraph.length > MAX_CHARS) {
      segments.push(current);
      current = paragraph;
    } else {
      current += '\n\n' + paragraph;
    }
  }
  
  if (current) segments.push(current);
  return segments;
}
```

## Feed 生成服务

**PodcastFeedGenerator** (`feed/PodcastFeedGenerator.ts`)：
- **格式**: RSS 2.0 + iTunes Podcast 标签
- **验证**: 使用 `podcast` npm 包验证格式
- **输出**: XML 文件保存到 `data/media/feeds/{groupId}.xml`

**生成流程**：
```typescript
async generate(groupId: string, episodes: Episode[]): Promise<string> {
  const feed = new Feed({
    title: group.name,
    description: group.description,
    language: 'zh-cn',
    // ...
  });
  
  for (const episode of episodes) {
    feed.addItem({
      title: episode.title,
      description: episode.description,
      enclosure: {
        url: episode.audioUrl,
        type: 'audio/mpeg',
        length: episode.fileSize,
      },
      itunes: {
        duration: episode.duration,
        episodeType: 'full',
      },
    });
  }
  
  const xml = feed.rss2();
  await fs.writeFile(outputPath, xml, 'utf-8');
  return outputPath;
}
```

## 代码约定

- **服务接口** - 每个服务实现定义的接口 (LLMService, TTSService)
- **重试逻辑** - 指数退避 (5 次重试，2s 基础)
- **配置注入** - 服务通过构造函数接收配置
- **日志记录** - 所有请求使用 pino 记录

## 反模式

- ❌ 不要硬编码 API 密钥 - 使用 config.json
- ❌ 不要跳过重试逻辑 - API 有速率限制
- ❌ 不要直接从 CLI/API 调用服务 - 使用 PipelineOrchestrator
- ❌ 不要吞掉错误 - 记录日志后重新抛出

## 独特风格

- **TTS 分段** - 自动分割超过 2:43 的文本以适应 SiliconFlow API 限制
- **双语解析** - 脚本分段支持英文 (Host/Guest) 和中文 (主持人/嘉宾) 说话人标签
- **Prompt 模板化** - LLM 提示词使用独立方法构建，便于调整

## API 重试策略

```typescript
async callLLM(prompt: string): Promise<LLMResponse> {
  const maxRetries = 5;
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await this.client.post(endpoint, { prompt });
    } catch (error: unknown) {
      lastError = error instanceof Error ? error : new Error(String(error));
      
      if (axios.isAxiosError(error) && error.response?.status === 429) {
        const waitTime = Math.pow(2, attempt) * 2000;
        logger.warn({ attempt }, 'Rate limited, waiting');
        await this.sleep(waitTime);
        continue;
      }
      
      if (attempt < maxRetries) {
        await this.sleep(Math.pow(2, attempt) * 2000);
      }
    }
  }
  
  throw lastError;
}
```

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `features/pipeline/` | 在流水线阶段中调用服务 |
| `shared/config/` | 从 config.json 读取 API 密钥和配置 |
| `shared/types/` | 使用 LLM/TTS 类型定义 |

## 测试服务

```bash
# 测试 LLM 连接
npm run cli -- llm:test

# 测试 TTS 连接
npm run cli -- tts:test

# 运行服务测试
npm run test test/services/
```
