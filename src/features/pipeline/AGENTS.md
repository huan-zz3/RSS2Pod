# Pipeline Module Knowledge Base

## Overview

6 阶段流水线编排器：事件驱动的核心业务逻辑，协调 LLM 摘要、TTS 合成和 Feed 生成。支持并发控制和实时进度跟踪。

## Structure

```
pipeline/
└── PipelineOrchestrator.ts    # 流水线编排器 (554 行)
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 修改阶段执行逻辑 | `PipelineOrchestrator.ts` (`executeStage` 方法) | 每个阶段的具体实现 |
| 添加新阶段 | `PipelineOrchestrator.ts` (`PipelineStage` 类型 + `executeStage`) | 更新阶段枚举和执行逻辑 |
| 修改并发控制 | `PipelineOrchestrator.ts` (`checkConcurrency` 方法) | 并发限制逻辑 |
| 停止流水线 | `PipelineOrchestrator.ts` (`stopPipeline` 方法) | 取消运行中的流水线 |

## 6 阶段流水线

```typescript
enum PipelineStage {
  SOURCE_SUMMARY = 'source-summary',      // 1. 源摘要：为每个源生成摘要 (LLM)
  GROUP_AGGREGATE = 'group-aggregate',    // 2. 组聚合：合并为组级摘要
  SCRIPT = 'script',                       // 3. 脚本：生成播客脚本 (LLM)
  AUDIO = 'audio',                         // 4. 音频：合成音频 (TTS)
  EPISODE = 'episode',                     // 5. 节目：保存节目元数据
  FEED = 'feed',                           // 6. Feed：更新播客 RSS Feed
}
```

**执行流程**:
1. `PipelineOrchestrator.runForGroup(groupId)` 启动流水线
2. 每个阶段顺序执行，前一个完成后才能继续
3. 每个阶段发射 `stage:completed` 事件
4. 错误时发射 `pipeline:failed` 事件

## 阶段详情

### 1. Source Summary (源摘要)
**方法**: `executeSourceSummary()`

**功能**:
- 获取未处理文章（最多 `maxArticlesPerRun` 篇）
- 按源分组
- 为每个源调用 LLM 生成摘要
- 保存到 `source_summaries` 表

**零文章检测**:
```typescript
if (unprocessed.length === 0) {
  throw new Error('No unprocessed articles found...');
}
```

**效果**: 立即失败，不卡住，错误消息包含解决建议

### 2. Group Aggregation (组聚合)
**方法**: `executeGroupAggregation()`

**功能**:
- 读取所有源摘要
- 合并为组级摘要
- 保存到 `group_summaries` 表

### 3. Script (脚本)
**方法**: `executeScript()`

**功能**:
- 使用组摘要生成播客脚本
- 支持双语说话人标签（Host/Guest 或 主持人/嘉宾）
- 保存到 `episodes.script` 字段（JSON 格式）

**脚本格式**:
```json
{
  "segments": [
    {
      "speaker": "Host",
      "text": "欢迎收听今天的科技新闻..."
    },
    {
      "speaker": "Guest",
      "text": "今天我们来看看 AI 领域的最新进展..."
    }
  ]
}
```

### 4. Audio (音频)
**方法**: `executeAudio()`

**功能**:
- 解析脚本中的说话人分段
- 调用 TTS 合成每段音频
- 自动分割超过 2:43 的文本（SiliconFlow API 限制）
- 合并音频文件
- 保存到 `data/media/{groupId}/episode_{timestamp}/`

**TTS 分段逻辑**:
```typescript
// 每段不超过 2:43 (163 秒)
const MAX_DURATION = 163;
const CHARS_PER_SECOND = 15;
const MAX_CHARS = MAX_DURATION * CHARS_PER_SECOND;
```

### 5. Episode (节目)
**方法**: `executeEpisode()`

**功能**:
- 保存节目元数据到 `episodes` 表
- 生成 GUID
- 记录音频路径、时长、文件大小

### 6. Feed (订阅源)
**方法**: `executeFeed()`

**功能**:
- 查询组内最近 10 个 episodes
- 使用 `PodcastFeedGenerator` 生成 RSS Feed
- 保存到 `data/media/feeds/{groupId}.xml`

**URL 构造**:
```typescript
const appConfig = getConfig();
const baseUrl = appConfig.api.baseUrl;

const config: FeedConfig = {
  groupId: group.id,
  siteUrl: baseUrl,
  // ...
};

const feedItems = episodes.map((episode) => ({
  enclosure: {
    url: `${baseUrl}/api/media/${relativePath}`,
    // ...
  }
}));
```

## 代码约定

### 事件发射
每个阶段开始和完成时发射事件：
```typescript
// 阶段开始
this.eventBus.emit('pipeline:stage:started', {
  runId: run.id,
  groupId: group.id,
  stage: stage,
}, 'PipelineOrchestrator');

// 阶段完成
this.eventBus.emit('pipeline:stage:completed', {
  runId: run.id,
  groupId: group.id,
  stage: stage,
  payload: { /* 阶段特定数据 */ },
}, 'PipelineOrchestrator');
```

### 并发控制
强制执行 `maxConcurrentGroups` 限制：
```typescript
private async checkConcurrency(): Promise<void> {
  const runningCount = await this.getRunningCount();
  if (runningCount >= this.config.maxConcurrentGroups) {
    throw new Error(`Concurrency limit reached: ${runningCount}`);
  }
}
```

### 错误处理
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

## 反模式

- ❌ 不要直接调用流水线阶段 - 使用 `runForGroup()`
- ❌ 不要跳过事件发射 - TUI 依赖事件更新状态
- ❌ 不要在未更新 `PipelineStage` 类型的情况下修改阶段顺序
- ❌ 不要绕过编排器直接调用服务 - 破坏事件驱动架构
- ❌ 不要忽略并发限制 - 可能导致资源耗尽
- ❌ 不要忘记清理活跃运行 Map - 内存泄漏风险

## 独特风格

### 配置注入
构造函数中加载配置：
```typescript
constructor(dbManager: DatabaseManager, config: PipelineConfig) {
  this.dbManager = dbManager;
  this.maxConcurrentGroups = config.maxConcurrentGroups;
  
  const appConfig = loadConfig();
  this.maxArticlesPerRun = appConfig.pipeline.maxArticlesPerRun;
  this.llmService = new DashScopeService(appConfig.llm);
  this.ttsService = new SiliconFlowService(appConfig.tts);
  
  const db = dbManager.getDb();
  this.groupRepo = new GroupRepository(db);
}
```

### 活跃运行跟踪
使用 Map 跟踪正在运行的流水线：
```typescript
private activeRuns: Map<string, PipelineRun> = new Map();

async runForGroup(groupId: string): Promise<PipelineRun> {
  await this.checkConcurrency();
  
  const run: PipelineRun = {
    id: `run-${Date.now()}`,
    groupId,
    status: 'running',
    stages: { /* ... */ },
    articlesCount: articles.length,
  };
  
  this.activeRuns.set(run.id, run);
  // ...
}
```

### 停止流水线
支持取消运行中的流水线：
```typescript
stopPipeline(runId: string): { runId: string; groupId: string } {
  const run = this.activeRuns.get(runId);
  if (!run || run.status !== 'running') {
    throw new Error(`Pipeline ${runId} is not running`);
  }
  
  run.status = 'cancelled';
  this.activeRuns.delete(runId);
  
  // 更新数据库状态
  this.db.prepare(`
    UPDATE pipeline_runs SET status = 'cancelled' WHERE id = ?
  `).run(runId);
  
  this.eventBus.emit('pipeline:cancelled', { runId, groupId: run.groupId }, 'PipelineOrchestrator');
  
  return { runId, groupId: run.groupId };
}
```

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `services/llm/` | 调用 `DashScopeService` 生成摘要和脚本 |
| `services/tts/` | 调用 `SiliconFlowService` 合成音频 |
| `services/feed/` | 调用 `PodcastFeedGenerator` 生成 RSS |
| `features/events/` | 使用 `EventBus` 发射进度事件 |
| `repositories/` | 通过 Repository 访问数据库 |
| `shared/config/` | 从 `config.json` 读取配置 |

## 流水线管理

### 启动流水线
```typescript
const orchestrator = new PipelineOrchestrator(dbManager, { maxConcurrentGroups: 3 });
await orchestrator.runForGroup(groupId);
```

### 停止流水线
```typescript
const result = orchestrator.stopPipeline(runId);
console.log(`Pipeline ${result.runId} cancelled`);
```

### 查看运行历史
```bash
# CLI 命令
npm run cli -- pipeline:runs <groupId>
```

## 调试命令

```bash
# 手动运行流水线
npm run cli -- generate:run <groupId>

# 查看运行历史
npm run cli -- pipeline:runs <groupId>

# 停止运行中的流水线
npm run cli -- pipeline:stop <runId>

# 查看未处理文章
npm run cli -- article:unprocessed <groupId>
```

## 测试

```bash
# 运行流水线测试
npm run test test/pipeline/

# 手动测试（生产环境）
npm run cli -- generate:run <groupId>
```
