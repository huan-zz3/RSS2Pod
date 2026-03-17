# Features Module Knowledge Base

## Overview

核心业务逻辑：事件总线（事件驱动架构）和 6 阶段流水线编排器。包含组管理、LLM 处理、TTS 处理、调度器等业务功能。

## Structure

```
features/
├── events/
│   └── EventBus.ts          # 事件总线实现
├── pipeline/
│   └── PipelineOrchestrator.ts  # 6 阶段流水线编排器 (418 行)
├── groups/                  # 组管理逻辑
├── feeds/                   # 订阅源管理逻辑
├── llm/                     # LLM 处理逻辑
├── tts/                     # TTS 处理逻辑
├── podcast/                 # 播客逻辑
└── scheduler/               # 调度器逻辑
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 修改流水线阶段 | `pipeline/PipelineOrchestrator.ts` | 6 阶段定义和执行逻辑 |
| 添加事件类型 | `events/EventBus.ts`, `../shared/types/events.ts` | 事件定义和发射 |
| 修改阶段执行 | `pipeline/PipelineOrchestrator.ts` (`executeStage` 方法) | 每个阶段的具体实现 |
| 修改组逻辑 | `groups/` 目录 | 组 CRUD 和触发器配置 |
| 修改调度器 | `scheduler/` 目录 | 定时任务和触发器检查 |

## 6 阶段流水线

```typescript
enum PipelineStage {
  FETCH = 'fetch',           // 1. 获取：从 Fever API 获取文章
  SOURCE_SUMMARY = 'sourceSummary',  // 2. 源摘要：为每个源生成摘要 (LLM)
  GROUP_AGGREGATION = 'groupAggregation',  // 3. 组聚合：合并为组级摘要
  SCRIPT = 'script',         // 4. 脚本：生成播客脚本 (LLM)
  AUDIO = 'audio',           // 5. 音频：合成音频 (TTS)
  EPISODE = 'episode',       // 6. 节目：保存节目元数据
  FEED = 'feed',             // 7. 订阅源：更新播客 RSS Feed
}
```

**执行流程**：
1. `PipelineOrchestrator.runForGroup(groupId)` 启动流水线
2. 每个阶段顺序执行，前一个完成后才能继续
3. 每个阶段开始时发射 `stage:started` 事件
4. 每个阶段完成后发射 `stage:completed` 事件
5. 错误时发射 `pipeline:failed` 事件，标记为失败

## 事件驱动架构

**EventBus** (`events/EventBus.ts`)：
```typescript
export class EventBus {
  private emitter: EventEmitter2;
  
  // 发射事件
  emit<T extends EventType>(type: T, payload: EventPayloadMap[T]): void;
  
  // 订阅事件
  on<T extends EventType>(type: T, handler: (event: AppEvent<T>) => void): void;
  
  // 一次性订阅
  once<T extends EventType>(type: T, handler: (event: AppEvent<T>) => void): void;
}
```

**事件类型** (`../shared/types/events.ts`)：
```typescript
export type EventType =
  | 'pipeline:started'
  | 'pipeline:completed'
  | 'pipeline:failed'
  | 'stage:started'
  | 'stage:completed'
  | 'stage:failed';
```

**TUI 订阅事件**：
```typescript
eventBus.on('pipeline:started', (event) => {
  // 更新 UI 显示进度
});

eventBus.on('stage:completed', (event) => {
  // 更新阶段状态
});
```

## 代码约定

- **流水线阶段顺序执行** - 每个阶段必须完成后才能继续
- **事件发射** - 在阶段开始/完成时发射事件
- **错误传播** - 错误向上抛出，运行标记为失败
- **并发控制** - 强制执行 `maxConcurrentGroups` 限制

## 反模式

- ❌ 不要直接调用流水线阶段 - 使用 `PipelineOrchestrator.runForGroup()`
- ❌ 不要跳过事件发射 - TUI 依赖事件更新状态
- ❌ 不要在未更新 `PipelineStage` 类型的情况下修改阶段顺序
- ❌ 不要绕过编排器直接调用服务 - 破坏事件驱动架构

## 独特风格

- **LLM/TTS 集成在流水线阶段中** - 不是单独的服务调用
- **脚本分段解析** - 支持双语说话人标签（英文 Host/Guest，中文 主持人/嘉宾）
- **音频自动分段** - 自动分割超过 2:43 的文本以适应 SiliconFlow API 限制

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `services/` | 调用 LLM/TTS/Feed 服务完成各阶段任务 |
| `infrastructure/` | 通过 repositories 访问数据库 |
| `shared/types/` | 使用事件类型和配置类型 |
| `tui/` | 通过事件通知 TUI 更新进度 |

## 并发控制

```typescript
// PipelineOrchestrator.ts
private async checkConcurrency(): Promise<void> {
  const runningCount = await this.getRunningCount();
  if (runningCount >= this.config.maxConcurrentGroups) {
    throw new Error(`Concurrency limit reached: ${runningCount}`);
  }
}
```

## 错误处理

```typescript
try {
  await this.executeStage(stage, run, group);
  run.stages[stage] = 'completed';
} catch (error) {
  run.stages[stage] = 'failed';
  const errorMessage = error instanceof Error ? error.message : String(error);
  logger.error({ stage, groupId: group.id, error: errorMessage }, 'Stage failed');
  throw error;  // 重新抛出，让上层处理
}
```

## 流水线管理

### 停止正在运行的流水线

使用 `PipelineOrchestrator.stopPipeline(runId)` 方法停止正在运行的流水线：

```typescript
const orchestrator = new PipelineOrchestrator(dbManager, config);

try {
  const result = orchestrator.stopPipeline(runId);
  console.log(`Pipeline ${result.runId} cancelled`);
} catch (error) {
  console.error(`Failed to stop pipeline: ${error.message}`);
}
```

**注意**：
- 只能停止状态为 `running` 的流水线
- 会更新数据库状态为 `cancelled`
- 发射 `pipeline:cancelled` 事件
- 正在进行的 LLM/TTS API 调用会继续完成（但结果被忽略）

### 零文章检测

在 `executeSourceSummary()` 阶段自动检测：

```typescript
if (unprocessed.length === 0) {
  throw new Error('No unprocessed articles found...');
}
```

**效果**：
- 立即失败，不卡住
- 错误消息包含解决建议
- 数据库状态标记为 `failed`

## 测试

```bash
# 运行 features 相关测试
npm run test test/features/

# 运行流水线测试
npx vitest test/pipeline/
```
