# Services 知识库

## 概述

外部服务集成：LLM (DashScope)、TTS (SiliconFlow)、播客 Feed 生成。

## 结构

```
services/
├── llm/
│   ├── DashScopeService.ts    # LLM 集成
│   └── index.ts
├── tts/
│   ├── SiliconFlowService.ts  # TTS 集成
│   └── index.ts
└── feed/
    ├── PodcastFeedGenerator.ts # RSS feed 生成
    └── index.ts
```

## 查找指南

| 任务 | 位置 |
|------|------|
| 修改 LLM 提示词 | `llm/DashScopeService.ts` (buildSummaryPrompt, buildScriptPrompt) |
| 更改 TTS 声音 | `tts/SiliconFlowService.ts` (构造函数配置) |
| 调整音频分段 | `tts/SiliconFlowService.ts` (segmentText 方法) |
| 修改 feed 格式 | `feed/PodcastFeedGenerator.ts` |

## 代码约定

- **服务接口** - 每个服务实现定义的接口 (LLMService, TTSService)
- **重试逻辑** - 指数退避 (3 次重试，基础 1 秒)
- **配置注入** - 服务从构造函数接收配置
- **日志记录** - 所有请求使用 pino 记录

## 反模式

- ❌ 不要硬编码 API 密钥 - 使用 config
- ❌ 不要跳过重试逻辑 - API 有速率限制
- ❌ 不要直接从 CLI/API 调用服务 - 使用 PipelineOrchestrator

## 独特风格

- **TTS 分段** - 自动分割超过 2:43 的文本 (SiliconFlow 限制)
- **双语解析** - 脚本段支持英文/中文说话人标签
