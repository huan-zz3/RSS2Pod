# CLI Module Knowledge Base

## Overview

命令行界面入口：使用 Commander.js 实现 24 个命令，支持组管理、订阅源管理、Fever API 调试、LLM/TTS 测试和流水线执行。

## Structure

```
cli/
├── index.ts              # CLI 入口 (723 行，24 个命令)
└── commands/             # 命令定义目录
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 添加新命令 | `index.ts` | 在 `program.command()` 中注册 |
| 修改命令逻辑 | `index.ts` | 每个命令的 `.action()` 回调 |
| 查看命令列表 | `index.ts` | 搜索 `program.command(` |

## 命令分类

| 分类 | 命令数 | 关键命令 |
|------|--------|----------|
| 系统状态 | 2 | `status`, `db:stats` |
| 配置管理 | 3 | `init`, `config:show`, `config:set` |
| 组管理 | 7 | `group:list`, `group:create`, `group:edit`, `group:delete` |
| 订阅源 | 2 | `source:list`, `source:show` |
| Fever API | 3 | `fever:test`, `fever:sync-feeds`, `fever:cache-articles` |
| LLM 调试 | 2 | `llm:test`, `llm:chat` |
| TTS 调试 | 1 | `tts:test` |
| 生成流程 | 4 | `generate:run`, `generate:history`, `trigger:status`, `pipeline:stop` |

## 代码约定

- **命令定义** - 使用 `program.command('<name> <args>')` 定义
- **帮助信息** - 每个命令使用 `.description()` 和 `.option()` 提供文档
- **错误处理** - try-catch 包裹，使用 `logger.error()` 记录
- **日志输出** - 使用 `pino` logger，非 TUI 模式下输出到控制台

## 反模式

- ❌ 不要在 CLI 层放置业务逻辑 - 调用服务层
- ❌ 不要直接调用流水线阶段 - 使用 `PipelineOrchestrator.runForGroup()`
- ❌ 不要硬编码配置 - 使用 `loadConfig()` 从 config.json 读取
- ❌ 不要跳过错误处理 - 所有异步操作必须 try-catch

## 独特风格

- **组 ID 双模式** - 支持索引 (0-based) 和真实 ID (`grp-xxx`) 引用组
- **命令链接** - 复杂操作提供分步指导（如 `init` 后提示编辑 config.json）

## 命令示例

```bash
# 系统状态
npm run cli -- status
npm run cli -- db:stats

# 组管理
npm run cli -- group:list
npm run cli -- group:create "科技新闻" -s "1,2,3"
npm run cli -- group:edit <id> -n "新名称"
npm run cli -- group:delete <id>

# Fever API
npm run cli -- fever:test
npm run cli -- fever:sync-feeds
npm run cli -- fever:cache-articles -l 100

# 流水线
npm run cli -- generate:run <groupId>
npm run cli -- generate:history
npm run cli -- pipeline:runs <groupId>
npm run cli -- pipeline:stop <runId>
```

## 与其他入口的关系

| 入口 | 关系 |
|------|------|
| `src/index.ts` | 共享核心初始化逻辑（数据库、事件总线） |
| `src/api/index.ts` | 独立运行，无直接调用 |
| `src/tui/index.tsx` | TUI 调用相同的后端服务 |

## 测试

```bash
# 运行 CLI 测试
npm run test test/cli/

# 测试特定命令
npx vitest test/cli/group-edit.test.ts
```
