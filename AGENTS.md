# RSS2Pod Knowledge Base

**Generated:** 2026-03-16
**Commit:** $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
**Branch:** $(git branch --show-current 2>/dev/null || echo "unknown")
**Tech Stack:** TypeScript + Node.js + ESM + Fastify + SQLite + LLM (DashScope) + TTS (SiliconFlow) + React Ink (TUI) + node-cron

## Overview

RSS 转播客转换器，具备 AI 驱动的内容增强功能。6 阶段流水线：源摘要 → 组聚合 → 脚本 → 音频 → 节目 → Feed。SyncService 独立同步文章（600s 间隔）。支持三种触发器（时间/数量/LLM）和混合触发模式。

## Project Structure

```
RSS2Pod/
├── src/
│   ├── cli/              # CLI 入口 (Commander, 24 命令)
│   ├── api/              # REST API (Fastify 路由)
│   ├── tui/              # TUI 交互界面 (React Ink, 键盘导航)
│   ├── features/         # 核心业务逻辑 (EventBus, 6 阶段流水线，SyncService)
│   ├── services/         # 外部服务集成 (LLM, TTS, Feed 生成)
│   ├── repositories/     # 数据访问层 (SQLite, better-sqlite3)
│   ├── infrastructure/   # 数据库 + 外部 API 客户端 (Fever)
│   └── shared/           # 类型定义，配置 (Zod), 工具函数
├── test/                 # Vitest 测试
├── data/                 # SQLite 数据库，媒体文件 (gitignored)
└── dist/                 # 编译输出
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 运行 CLI 命令 | `src/cli/index.ts` | 24 个命令：init, db:init, group:*, pipeline:run, trigger:*, scheduler:*, sync:* |
| 修改流水线阶段 | `src/features/pipeline/PipelineOrchestrator.ts` | 6 阶段，LLM/TTS 集成，事件发射 |
| 添加同步功能 | `src/features/sync/` | SyncService，独立文章同步（600s 间隔） |
| 添加调度器功能 | `src/features/scheduler/` | 触发器评估、定时检查、自动执行 |
| 添加外部 API 客户端 | `src/infrastructure/external/` | 遵循 FeverClient 模式 |
| 添加新服务 | `src/services/` | LLM, TTS, Feed 生成器 |
| 修改数据库模式 | `src/infrastructure/database/DatabaseManager.ts` | 9 张表，迁移 |
| 类型定义 | `src/shared/types/` | events.ts, feed.ts, llm.ts, tts.ts, scheduler.ts, sync.ts |
| 配置管理 | `src/shared/config/index.ts` | Zod 验证 |
| REST API 路由 | `src/api/index.ts` | Fastify 服务器 |
| TUI 界面 | `src/tui/` | React Ink, 键盘导航 |

## Code Map

| 符号 | 类型 | 位置 | 作用 |
|------|------|------|------|
| `PipelineOrchestrator` | 类 | `src/features/pipeline/` | 6 阶段流水线执行 |
| `SyncService` | 类 | `src/features/sync/` | 独立同步服务，600s 间隔从 Fever API 获取文章 |
| `EventBus` | 类 | `src/features/events/` | 事件驱动通信 |
| `SchedulerService` | 类 | `src/features/scheduler/` | 调度器主服务，每分钟检查触发器 |
| `TriggerEvaluator` | 类 | `src/features/scheduler/` | 触发器工厂和评估器 |
| `CronScheduler` | 类 | `src/features/scheduler/triggers/` | 时间触发器 (Cron 表达式) |
| `CountTrigger` | 类 | `src/features/scheduler/triggers/` | 数量触发器 (文章阈值) |
| `LLMTrigger` | 类 | `src/features/scheduler/triggers/` | LLM 触发器 (内容评估) |
| `MixedTrigger` | 类 | `src/features/scheduler/triggers/` | 混合触发器 (时间 + 数量 + LLM) |
| `DashScopeService` | 类 | `src/services/llm/` | LLM 集成 (DashScope) |
| `SiliconFlowService` | 类 | `src/services/tts/` | TTS 集成 (SiliconFlow) |
| `FeverClient` | 类 | `src/infrastructure/external/` | Fever API 客户端 (TT-RSS) |
| `DatabaseManager` | 类 | `src/infrastructure/database/` | SQLite 初始化 |
| `GroupRepository` | 类 | `src/repositories/` | 组数据访问 |
| `ArticleRepository` | 类 | `src/repositories/` | 文章数据访问 |

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
- ❌ 不要手动触发流水线 - 使用 SchedulerService 自动触发（除非调试）

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
npm run cli -- <cmd>     # CLI 命令 (24 个可用命令)
npm run api              # 启动 Fastify 服务器
npm run test             # 运行 vitest 测试
npm run typecheck        # 仅类型检查
npm run lint             # ESLint 检查
```

## CLI 命令分类

| 分类 | 命令数 | 关键命令 |
|------|--------|----------|
| 系统状态 | 2 | status, db:stats |
| 配置管理 | 3 | init, config:show, config:set |
| 组管理 | 7 | group:list, group:create, group:edit, group:delete |
| 订阅源 | 2 | source:list, source:show |
| Fever API | 3 | fever:test, fever:sync-feeds, fever:cache-articles |
| LLM 调试 | 2 | llm:test, llm:chat |
| TTS 调试 | 1 | tts:test |
| 生成流程 | 3 | generate:run, generate:history, trigger:status |
| 调度器 | 3 | trigger:check, scheduler:start, scheduler:stop |

## 重要说明

- **ffmpeg 必需** - 音频合成需要：`apt-get install ffmpeg` 或 `brew install ffmpeg`
- **config.json 不在 git 中** - 使用 `npm run cli -- init` 创建模板
- **SQLite 数据库** - 位于 `data/rss2pod.db` (gitignored)
- **媒体文件** - 存储在 `data/media/{groupId}/episode_{timestamp}/`
- **API 配置** - `config.json` 中 `api.baseUrl` 控制 Feed 生成的公开 URL
- **API 重试** - DashScopeService 有 5 次重试，指数退避 (2s 基础)
- **推荐 TUI** - 使用 `npm run tui` 获得交互式界面和键盘导航
- **Scheduler 自动启动** - `npm run dev` 时调度器自动启动，每分钟检查触发器
- **node-cron 依赖** - 时间触发器使用 node-cron v4.x，时区 Asia/Shanghai
- **严格 TypeScript** - `noUncheckedIndexedAccess: true`，数组访问需检查 undefined

## 模块级 AGENTS.md

以下子目录有专属 AGENTS.md 文档：

| 模块 | 文档 | 内容 |
|------|------|------|
| `src/tui/` | `src/tui/AGENTS.md` | TUI 界面组件和键盘导航 |
| `src/tui/screens/` | `src/tui/screens/AGENTS.md` | 11 个界面组件，模式驱动 UI |
| `src/tui/components/` | `src/tui/components/AGENTS.md` | 6 个可复用 UI 组件（Select, Input, Table 等） |
| `src/tui/commands/` | `src/tui/commands/AGENTS.md` | 7 个命令处理器（组管理、系统状态等） |
| `src/features/` | `src/features/AGENTS.md` | 核心业务逻辑和事件驱动架构 |
| `src/features/scheduler/` | `src/features/scheduler/AGENTS.md` | 调度器核心服务，每分钟检查触发器 |
| `src/features/scheduler/triggers/` | `src/features/scheduler/triggers/AGENTS.md` | 4 种触发器（策略模式） |
| `src/features/sync/` | `src/features/sync/AGENTS.md` | 独立同步服务，600s 间隔从 Fever API 获取文章 |
| `src/services/` | `src/services/AGENTS.md` | 外部服务集成 (LLM/TTS/Feed) |
| `src/infrastructure/` | `src/infrastructure/AGENTS.md` | 数据库层和外部 API 客户端 |
| `src/cli/` | `src/cli/AGENTS.md` | CLI 命令和入口点 |
| `src/shared/` | `src/shared/AGENTS.md` | 类型定义和配置管理 |
| `src/repositories/` | `src/repositories/AGENTS.md` | 数据访问层，SQLite CRUD 封装 |
