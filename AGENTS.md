# RSS2Pod 知识库

**生成时间:** 2026-03-13
**技术栈:** TypeScript + Node.js + ESM + Fastify + SQLite + LLM (DashScope) + TTS (SiliconFlow)

## 概述

RSS 转播客转换器，具备 AI 驱动的内容增强功能。7 阶段处理流程：获取 → 摘要 → 聚合 → 脚本 → 音频 → 节目 → 订阅源。

## 项目结构

```
RSS2Pod/
├── src/
│   ├── cli/              # CLI 入口 (Commander)
│   ├── api/              # REST API (Fastify)
│   ├── features/         # 核心业务逻辑 (EventBus, Pipeline)
│   ├── services/         # 外部服务 (LLM, TTS, Feed)
│   ├── repositories/     # 数据访问 (SQLite)
│   ├── infrastructure/   # 数据库、外部客户端
│   └── shared/           # 类型、配置、工具
├── test/                 # Vitest 测试
├── data/                 # SQLite 数据库、媒体文件 (已 gitignore)
└── dist/                 # 编译输出
```

## 查找指南

| 任务 | 位置 | 说明 |
|------|------|------|
| 运行 CLI 命令 | `src/cli/index.ts` | 命令：init, db:init, group:*, pipeline:run |
| 修改流水线阶段 | `src/features/pipeline/PipelineOrchestrator.ts` | 7 阶段，LLM/TTS 集成 |
| 添加外部 API | `src/infrastructure/external/` | FeverClient 模式 |
| 添加服务 | `src/services/` | LLM, TTS, Feed 生成器 |
| 数据库模式 | `src/infrastructure/database/DatabaseManager.ts` | 7 张表 |
| 类型定义 | `src/shared/types/` | events.ts, feed.ts, llm.ts, tts.ts |
| 配置 | `src/shared/config/index.ts` | Zod 验证 |
| REST API | `src/api/index.ts` | Fastify 路由 |

## 代码地图

| 符号 | 类型 | 位置 | 作用 |
|------|------|------|------|
| `PipelineOrchestrator` | 类 | `src/features/pipeline/` | 7 阶段流水线执行 |
| `EventBus` | 类 | `src/features/events/` | 事件驱动通信 |
| `DashScopeService` | 类 | `src/services/llm/` | LLM 集成 |
| `SiliconFlowService` | 类 | `src/services/tts/` | TTS 集成 |
| `FeverClient` | 类 | `src/infrastructure/external/` | Fever API 客户端 |
| `DatabaseManager` | 类 | `src/infrastructure/database/` | SQLite 初始化 |

## 代码约定

- **仅使用 ESM 模块** - `package.json` 中 `"type": "module"`
- **显式 .js 扩展名** - 所有导入必须使用 `.js` 扩展名
- **严格 TypeScript** - `noUncheckedIndexedAccess`, `strict: true`
- **服务模式** - 每个外部 API 有独立的服务类
- **仓库模式** - 数据访问在 `src/repositories/`

## 本项目反模式

- ❌ 不要使用 CommonJS `require()` - 仅 ESM
- ❌ 不要在导入中省略 `.js` 扩展名
- ❌ 不要在 CLI/API 层放置业务逻辑 - 使用服务
- ❌ 不要跳过配置验证 - 需要 Zod schema
- ❌ 不要硬编码 API 密钥 - 使用 `config.json`
- ❌ 不要直接调用流水线阶段 - 使用 `PipelineOrchestrator.runForGroup()`

## 独特风格

- **多入口架构**: `src/index.ts` (主), `src/cli/index.ts`, `src/api/index.ts`
- **事件驱动流水线**: EventBus 在每个阶段发出事件
- **TTS 分段**: 自动分割超过 2:43 的文本以适应 SiliconFlow API 限制
- **双语脚本解析**: 支持英文 (Host/Guest) 和中文 (主持人/嘉宾)

## 命令

```bash
npm install              # 安装依赖
npm run dev              # 开发模式 (tsx watch)
npm run build            # 生产构建 (tsc)
npm run start            # 运行编译后的应用
npm run cli -- <cmd>     # CLI 命令
npm run api              # 启动 Fastify 服务器
npm run test             # 运行 vitest 测试
npm run typecheck        # 仅类型检查
npm run lint             # ESLint 检查
```

## 注意事项

- **需要 ffmpeg** 用于音频合成 - 使用 `apt-get install ffmpeg` 或 `brew install ffmpeg` 安装
- **config.json** 不在 git 中 - 使用 `npm run cli -- init` 创建模板
- **SQLite 数据库** 位于 `data/rss2pod.db` (已 gitignore)
- **媒体文件** 存储在 `data/media/{groupId}/episode_{timestamp}/`
- **API 速率限制** - DashScopeService 有 3 次重试，指数退避
