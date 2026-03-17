# Scheduler Module Knowledge Base

## Overview

调度器核心逻辑：每分钟检查所有启用组的触发器状态，自动触发流水线执行。采用策略模式，支持 4 种触发器类型。

## Structure

```
scheduler/
├── SchedulerService.ts      # 调度器主服务，每分钟检查触发器
├── TriggerEvaluator.ts      # 触发器工厂和评估器
├── types.ts                 # 调度器类型定义
└── triggers/                # 4 种触发器实现（策略模式）
    ├── CronScheduler.ts     # 时间触发器
    ├── CountTrigger.ts      # 数量触发器
    ├── LLMTrigger.ts        # LLM 触发器
    └── MixedTrigger.ts      # 混合触发器
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 修改调度器间隔 | `SchedulerService.ts` | 修改 `checkInterval` 配置 |
| 添加新触发器类型 | `triggers/` 目录创建新类 | 实现 `Trigger` 接口 |
| 修改触发器评估逻辑 | `TriggerEvaluator.ts` | 更新 `getTrigger()` 工厂方法 |
| 修改触发器配置 | `types.ts` | 更新 `TriggerConfig` 类型 |

## 调度器核心服务

### SchedulerService (调度器主服务)

**文件**: `SchedulerService.ts` (2580 行)

**职责**:
- 每分钟检查所有启用组的触发器状态
- 调用 `TriggerEvaluator` 获取对应触发器
- 触发条件满足时自动启动流水线
- 并发控制，遵守 `maxConcurrentGroups` 限制

**主循环**:
```typescript
export class SchedulerService {
  private interval: NodeJS.Timeout | null = null;
  
  start(): void {
    this.interval = setInterval(async () => {
      await this.checkAllGroups();
    }, this.config.checkInterval * 1000);  // 默认 60 秒
  }
  
  stop(): void {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  }
  
  private async checkAllGroups(): Promise<void> {
    const groups = await this.groupRepo.findAllEnabled();
    
    for (const group of groups) {
      try {
        const trigger = this.triggerEvaluator.getTrigger(group);
        const result = await trigger.evaluate(group.id);
        
        if (result.triggered) {
          logger.info({ groupId: group.id }, 'Trigger condition met');
          await this.pipelineOrchestrator.runForGroup(group.id);
        }
      } catch (error) {
        logger.error({ groupId: group.id, error }, 'Failed to check trigger');
      }
    }
  }
}
```

### TriggerEvaluator (触发器工厂)

**文件**: `TriggerEvaluator.ts` (2808 行)

**职责**: 根据组的 `triggerType` 创建对应的触发器实例。

**工厂方法**:
```typescript
export class TriggerEvaluator {
  getTrigger(group: Group): Trigger {
    switch (group.triggerType) {
      case 'time':
        return new CronScheduler(group.triggerConfig);
      case 'count':
        return new CountTrigger(group.triggerConfig);
      case 'llm':
        return new LLMTrigger(group.triggerConfig, this.articleRepo, this.llmService);
      case 'mixed':
        return new MixedTrigger(group.triggerConfig, this.articleRepo, this.llmService);
      default:
        throw new Error(`Unknown trigger type: ${group.triggerType}`);
    }
  }
}
```

## 触发器接口

所有触发器实现统一的 `Trigger` 接口：

```typescript
export interface Trigger {
  evaluate(groupId: string): Promise<TriggerResult>;
}

export interface TriggerResult {
  triggered: boolean;
  triggerType: string;
  reason: string;
  timestamp: Date;
}
```

## 触发器类型详情

### 1. time (时间触发)

**实现**: `triggers/CronScheduler.ts`

**触发条件**: 当前时间匹配 Cron 表达式

**配置**:
```typescript
{
  cron: '0 9 * * *',  // 每天早上 9 点
  timezone: 'Asia/Shanghai'
}
```

**独特实现**: 反向检查技巧 - 检查上次执行时间是否在过去 60 秒内，而非等待 cron 触发。

### 2. count (数量触发)

**实现**: `triggers/CountTrigger.ts`

**触发条件**: 未处理文章数量 >= 阈值

**配置**:
```typescript
{
  threshold: 10  // 10 篇文章触发
}
```

### 3. llm (LLM 触发)

**实现**: `triggers/LLMTrigger.ts`

**触发条件**: LLM 评估文章具有重要性

**配置**:
```typescript
{
  enabled: true,
  promptTemplate?: string  // 可选的自定义提示词
}
```

**⚠️ 风险**: LLM 响应解析简单（查找 YES），如果返回非预期格式会错误解析。

### 4. mixed (混合触发)

**实现**: `triggers/MixedTrigger.ts` (185 行)

**触发条件**: 时间/数量/LLM 任一条件满足

**评估顺序**: 时间 → 数量 → LLM（短路求值）

**配置**:
```typescript
{
  cron: '0 */6 * * *',  // 每 6 小时
  threshold: 5,          // 或 5 篇文章
  llmEnabled: true       // 或 LLM 判断
}
```

**设计理由**:
- **时间优先**: 最快，无外部依赖
- **数量次之**: 数据库查询，开销小
- **LLM 最后**: 最慢，需要 API 调用

## 代码约定

### 策略模式

所有触发器实现相同接口，通过 `TriggerEvaluator` 工厂类选择具体实现。

### 配置注入

触发器通过构造函数接收配置和依赖：

```typescript
export class MixedTrigger implements Trigger {
  constructor(
    config: TriggerConfig,
    articleRepo: ArticleRepository,
    llmService: DashScopeService,
  ) {
    this.config = config;
    this.articleRepo = articleRepo;
    this.llmService = llmService;
  }
}
```

### 并发控制

调度器遵守 `maxConcurrentGroups` 限制：

```typescript
// SchedulerService.ts
private async checkConcurrency(): Promise<void> {
  const runningCount = await this.getRunningCount();
  if (runningCount >= this.config.maxConcurrentGroups) {
    logger.warn('Concurrency limit reached, skipping trigger check');
    return;
  }
}
```

## 反模式

- ❌ 不要跳过触发器接口实现 - 必须实现 `evaluate()` 方法
- ❌ 不要在触发器中直接调用流水线 - 仅返回 `TriggerResult`
- ❌ 不要硬编码 Cron 时区 - 使用 `Asia/Shanghai`
- ❌ 不要忽略 LLM 响应解析错误 - 添加错误处理
- ❌ 不要在触发器中保存状态 - 每次评估都是独立的
- ❌ 不要忘记清理定时器 - `stop()` 时调用 `clearInterval`

## 独特风格

### 反向 Cron 检查

不是等待 cron 触发，而是检查上次执行时间：

```typescript
private getLastExecutionTime(cronExpression: string): Date {
  const now = new Date();
  const oneMinuteAgo = new Date(now.getTime() - 60000);
  
  const task = schedule(cronExpression, () => {}, {
    timezone: 'Asia/Shanghai',
  });
  task.stop();
  
  // 反向查找：从 1 分钟前开始，检查 cron 是否应该执行
  let checkTime = new Date(oneMinuteAgo);
  checkTime.setSeconds(0, 0);
  
  for (let i = 0; i < 60; i++) {
    const nextRun = task.getNextRun();
    if (nextRun && Math.abs(nextRun.getTime() - checkTime.getTime()) < 60000) {
      task.destroy();
      return checkTime;
    }
    checkTime = new Date(checkTime.getTime() - 60000);
  }
  
  task.destroy();
  return now;
}
```

**原因**: `SchedulerService` 每分钟调用一次 `checkAllGroups()`，所以检查过去 60 秒是否应该执行。

### 短路求值顺序

混合触发器按速度排序评估：

1. **时间触发** - 本地计算，无 I/O
2. **数量触发** - 数据库查询，快速
3. **LLM 触发** - API 调用，最慢

**优点**: 最小化 API 调用，提高评估效率。

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `features/pipeline/PipelineOrchestrator` | 触发条件满足时调用 `runForGroup()` |
| `repositories/GroupRepository` | 查询启用组列表 |
| `repositories/ArticleRepository` | 数量触发器查询未处理文章数 |
| `services/llm/DashScopeService` | LLM 触发器调用 |
| `shared/types/scheduler.ts` | 触发器类型定义 |

## 添加新触发器步骤

1. 在 `triggers/` 目录创建新类 `NewTrigger.ts`
2. 实现 `Trigger` 接口：`export class NewTrigger implements Trigger`
3. 实现 `evaluate(groupId: string): Promise<TriggerResult>` 方法
4. 在 `TriggerEvaluator.ts` 的 `getTrigger()` 方法中添加新 case
5. 在 `shared/types/scheduler.ts` 中添加新的 triggerType 类型
6. 在 `src/cli/index.ts` 的 `group:edit` 命令中支持新触发器类型

## 调度器配置

**config.json**:
```json
{
  "scheduler": {
    "checkInterval": 60,        // 检查间隔（秒）
    "maxConcurrentGroups": 3    // 最大并发流水线数
  }
}
```

## 调试命令

```bash
# 手动检查触发条件
npm run cli -- trigger:check <groupId>

# 启动调度器服务
npm run cli -- scheduler:start

# 停止调度器服务
npm run cli -- scheduler:stop

# 显示调度器配置和启用的组
npm run cli -- scheduler:status
```

## 测试

```bash
# 运行调度器测试
npm run test test/scheduler/

# 运行特定触发器测试
npx vitest test/scheduler/trigger-evaluator.test.ts
```
