# TUI Commands Module Knowledge Base

## Overview

7 个命令处理器模块，封装 CLI 命令供 TUI 调用，实现 UI 与后端逻辑的解耦。

## Structure

```
commands/
├── groups.ts           # 组管理命令 (list, create, edit, delete)
├── system.ts           # 系统状态命令 (status, db:stats)
├── generation.ts       # 流水线执行命令 (generate:run, generate:history)
├── fever.ts            # Fever API 命令 (fever:test, fever:sync-feeds, fever:cache-articles)
├── llm.ts              # LLM 调试命令 (llm:test, llm:chat)
├── tts.ts              # TTS 调试命令 (tts:test)
└── index.ts            # 命令注册表导出
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 添加新命令 | `commands/` 目录创建新模块 | 在 `index.ts` 中导出 |
| 修改命令逻辑 | 对应命令文件 | 每个命令是独立异步函数 |
| 修改命令参数 | 对应命令文件 | 更新函数签名和参数 |

## 命令处理器详情

### 1. groups.ts (组管理)

**文件**: `groups.ts` (4149 行)

**命令**:
- `listGroups()` - 列出所有组
- `createGroup(name, sourceIds, triggerType, triggerConfig)` - 创建新组
- `editGroup(id, updates)` - 编辑组配置
- `deleteGroup(id)` - 删除组
- `enableGroup(id)` - 启用组
- `disableGroup(id)` - 禁用组

**返回类型**:
```typescript
interface GroupInfo {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
  triggerType: string;
  articleCount?: number;
}
```

### 2. system.ts (系统状态)

**文件**: `system.ts`

**命令**:
- `getSystemStatus()` - 获取系统状态（版本、数据库、API 配置）
- `getDatabaseStats()` - 获取数据库统计（表行数）

**返回类型**:
```typescript
interface SystemStatus {
  version: string;
  nodeVersion: string;
  databasePath: string;
  feverConfigured: boolean;
  llmConfigured: boolean;
  ttsConfigured: boolean;
  stats: {
    groups: number;
    articles: number;
    episodes: number;
  };
}
```

### 3. generation.ts (流水线执行)

**文件**: `generation.ts`

**命令**:
- `runPipeline(groupId)` - 为指定组运行流水线
- `getPipelineHistory()` - 获取流水线执行历史
- `getTriggerStatus(groupId)` - 获取触发器状态

**特点**: 流水线运行时通过 EventBus 发射进度事件，TUI 订阅更新进度条。

### 4. fever.ts (Fever API)

**文件**: `fever.ts`

**命令**:
- `testFeverConnection()` - 测试 Fever API 连接
- `syncFeeds()` - 同步订阅源列表
- `cacheArticles(limit)` - 缓存指定数量的文章

**返回类型**:
```typescript
interface FeverTestResult {
  success: boolean;
  message: string;
  feedCount?: number;
}
```

### 5. llm.ts (LLM 调试)

**文件**: `llm.ts`

**命令**:
- `testLLMConnection()` - 测试 LLM 连接
- `chatWithLLM(message)` - 与 LLM 对话

**返回类型**:
```typescript
interface LLMChatResponse {
  content: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
  };
}
```

### 6. tts.ts (TTS 调试)

**文件**: `tts.ts`

**命令**:
- `testTTSConnection()` - 测试 TTS 连接

**返回类型**:
```typescript
interface TTSTestResult {
  success: boolean;
  message: string;
  audioPath?: string;
}
```

## 代码约定

### 短生命周期 DB 连接

每个命令独立管理 DB 连接（打开 → 查询 → 关闭）：

```typescript
// commands/groups.ts
export async function listGroups(): Promise<GroupInfo[]> {
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  const groups = groupRepo.findAll();
  dbManager.close();  // 每次调用都打开/关闭
  return groups;
}
```

**优点**: 避免连接泄漏
**缺点**: 频繁打开/关闭开销

### 命令模式

每个命令是返回结果的异步函数：

```typescript
export async function commandName(params: CommandParams): Promise<CommandResult> {
  // 1. 初始化 DB 和配置
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  
  try {
    // 2. 执行命令逻辑
    const result = await doSomething(params);
    
    // 3. 返回结果
    return result;
  } finally {
    // 4. 清理资源
    dbManager.close();
  }
}
```

### 错误处理

命令不吞掉错误，记录日志后重新抛出：

```typescript
try {
  const result = await service.call();
  return result;
} catch (error) {
  logger.error({ error }, 'Command failed');
  throw error;  // 让 TUI 层处理错误显示
}
```

## 反模式

- ❌ 不要使用 `console.log` - 使用 pino logger
- ❌ 不要在命令中混合 UI 逻辑 - 命令只返回数据
- ❌ 不要阻塞事件循环 - 所有命令都是异步的
- ❌ 不要忘记清理 DB 连接 - 使用 try-finally
- ❌ 不要吞掉错误 - 记录日志后重新抛出

## 独特风格

### 命令与 CLI 命令一一对应

每个 TUI 命令对应一个 CLI 命令，但返回结构化数据而非文本输出：

| CLI 命令 | TUI 命令 |
|---------|---------|
| `group:list` | `listGroups()` |
| `group:create` | `createGroup()` |
| `status` | `getSystemStatus()` |
| `fever:test` | `testFeverConnection()` |

### EventBus 集成

`generation.ts` 中的命令与 EventBus 集成，TUI 订阅进度事件：

```typescript
// TUI 订阅
const unsubscribe = eventBus.subscribe(
  'pipeline:audio:segment-completed',
  (event) => {
    if (payload?.groupId === groupId) {
      setCurrentSegment(segmentIndex);
      setProgress(newProgress);
    }
  }
);

// 清理订阅
if (unsubscribe) unsubscribe();
```

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `tui/screens/` | 屏幕组件调用这些命令获取数据 |
| `cli/index.ts` | CLI 命令和 TUI 命令调用相同的后端服务 |
| `features/` | 命令通过服务层间接调用业务逻辑 |
| `infrastructure/` | 命令通过 DatabaseManager 访问数据库 |

## 添加新命令步骤

1. 在 `commands/` 目录创建新模块或添加到现有模块
2. 实现异步函数，返回结构化数据
3. 在 `index.ts` 中导出新命令
4. 在 `tui/screens/` 中的屏幕组件中调用

## 命令使用示例

**组管理命令**:
```typescript
import { listGroups, createGroup, deleteGroup } from '../commands/groups';

// 列出所有组
const groups = await listGroups();

// 创建新组
await createGroup('科技新闻', ['1', '2'], 'count', { threshold: 10 });

// 删除组
await deleteGroup(groupId);
```

**系统状态命令**:
```typescript
import { getSystemStatus, getDatabaseStats } from '../commands/system';

const status = await getSystemStatus();
console.log(`Version: ${status.version}`);
console.log(`Groups: ${status.stats.groups}`);
```

**Fever API 命令**:
```typescript
import { testFeverConnection, syncFeeds } from '../commands/fever';

const result = await testFeverConnection();
if (result.success) {
  await syncFeeds();
}
```

**LLM 命令**:
```typescript
import { testLLMConnection, chatWithLLM } from '../commands/llm';

const response = await chatWithLLM('你好，请介绍一下自己');
console.log(response.content);
```

## 测试

```bash
# 启动 TUI（手动测试命令）
npm run tui

# 运行 CLI 命令测试（覆盖相同逻辑）
npm run test test/cli/
```

## 与 CLI 的区别

| 方面 | CLI | TUI Commands |
|------|-----|--------------|
| 输出 | 文本到控制台 | 结构化数据到 UI |
| 错误处理 | 打印错误消息 | 抛出错误让 UI 显示对话框 |
| 进度显示 | 文本进度条 | EventBus 事件驱动更新 |
| 交互方式 | 命令行参数 | 函数调用 |
