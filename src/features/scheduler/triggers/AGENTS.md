# Scheduler Triggers Module Knowledge Base

## Overview

4 种触发器实现，采用策略模式，支持时间触发、数量触发、LLM 智能触发和混合触发模式。

## Structure

```
triggers/
├── CronScheduler.ts       # 时间触发器（Cron 表达式）
├── CountTrigger.ts        # 数量触发器（文章阈值）
├── LLMTrigger.ts          # LLM 触发器（内容评估）
└── MixedTrigger.ts        # 混合触发器（三种条件组合）
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 添加新触发器类型 | `triggers/` 目录创建新类 | 实现 `Trigger` 接口 |
| 修改时间触发逻辑 | `CronScheduler.ts` | Cron 表达式验证和执行时间计算 |
| 修改数量触发逻辑 | `CountTrigger.ts` | 未处理文章数量阈值判断 |
| 修改 LLM 触发逻辑 | `LLMTrigger.ts` | LLM 提示词和响应解析 |
| 修改混合触发评估顺序 | `MixedTrigger.ts` | 时间 → 数量 → LLM 的短路求值 |

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

## 触发器详情

### 1. CronScheduler（时间触发）

**文件**: `CronScheduler.ts` (92 行)

**触发条件**: 当前时间匹配 Cron 表达式

**独特实现**: 反向检查技巧
```typescript
// 不是等待 cron 触发，而是检查上次执行时间是否在过去 60 秒内
const lastExecution = this.getLastExecutionTime(cronExpression);
const timeDiff = Math.abs(now.getTime() - lastExecution.getTime());
const shouldTrigger = timeDiff < 60000;  // 60 秒窗口
```

**原因**: `SchedulerService` 每分钟调用一次 `checkAllGroups()`，所以检查过去 60 秒是否应该执行。

**配置示例**:
```typescript
const trigger = new CronScheduler({
  cron: '0 9 * * *',  // 每天早上 9 点
  timezone: 'Asia/Shanghai'
});
```

### 2. CountTrigger（数量触发）

**文件**: `CountTrigger.ts`

**触发条件**: 未处理文章数量 >= 阈值

**实现**:
```typescript
const threshold = this.config.threshold ?? 10;
const count = this.articleRepo.countUnprocessed(groupId);
const shouldTrigger = count >= threshold;
```

**配置示例**:
```typescript
const trigger = new CountTrigger({
  threshold: 10  // 10 篇文章触发
});
```

### 3. LLMTrigger（智能触发）

**文件**: `LLMTrigger.ts`

**触发条件**: LLM 评估文章具有重要性

**实现**:
```typescript
// 获取未处理文章（最多 10 篇）
const articles = await this.articleRepo.findUnprocessed(groupId, 10);

// 构建评估提示
const prompt = this.buildEvaluationPrompt(articles);

// 调用 LLM
const response = await this.llmService.generateSummary(prompt);

// 解析响应（简单 YES/NO）
const shouldTrigger = this.parseLLMResponse(response.content);
```

**提示词模板**:
```
Evaluate if these {N} articles form a coherent topic worth a podcast episode:

- {article1}
- {article2}
...

Answer YES or NO with brief reasoning:
```

**响应解析**:
```typescript
private parseLLMResponse(content: string): boolean {
  return content.toUpperCase().includes('YES');
}
```

**⚠️ 风险**: 没有错误处理，如果 LLM 返回非预期格式（如空响应、中文"是"），会错误解析。

### 4. MixedTrigger（混合触发）

**文件**: `MixedTrigger.ts` (185 行)

**触发条件**: 时间/数量/LLM 任一条件满足

**评估顺序**: 时间 → 数量 → LLM（短路求值）

```typescript
async evaluate(groupId: string): Promise<TriggerResult> {
  // 1. 时间触发（最快，无 API 调用）
  if (this.config.cron) {
    const timeResult = await this.evaluateTimeTrigger(now);
    if (timeResult.triggered) {
      return { triggered: true, triggerType: 'mixed', ... };  // 短路
    }
  }

  // 2. 数量触发（数据库查询）
  if (this.config.threshold) {
    const countResult = this.evaluateCountTrigger(groupId);
    if (countResult.triggered) {
      return { triggered: true, triggerType: 'mixed', ... };  // 短路
    }
  }

  // 3. LLM 触发（最慢，需要 API 调用）
  if (this.config.llmEnabled) {
    const llmResult = await this.evaluateLLMTrigger(groupId);
    if (llResult.triggered) {
      return { triggered: true, triggerType: 'mixed', ... };  // 短路
    }
  }

  return { triggered: false, ... };
}
```

**设计理由**:
- **时间优先**: 最快，无外部依赖
- **数量次之**: 数据库查询，开销小
- **LLM 最后**: 最慢，需要 API 调用，仅在前两者都不满足时才调用

## 代码约定

### 策略模式

所有触发器实现相同接口，通过 `TriggerEvaluator` 工厂类选择具体实现：

```typescript
// TriggerEvaluator.ts
getTrigger(group: Group): Trigger {
  switch (group.triggerType) {
    case 'time':
      return new CronScheduler(group.triggerConfig);
    case 'count':
      return new CountTrigger(group.triggerConfig);
    case 'llm':
      return new LLMTrigger(group.triggerConfig, ...);
    case 'mixed':
      return new MixedTrigger(group.triggerConfig, ...);
  }
}
```

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

## 反模式

- ❌ 不要跳过触发器接口实现 - 必须实现 `evaluate()` 方法
- ❌ 不要在触发器中直接调用流水线 - 仅返回 `TriggerResult`
- ❌ 不要硬编码 Cron 时区 - 使用 `Asia/Shanghai`
- ❌ 不要忽略 LLM 响应解析错误 - 添加错误处理
- ❌ 不要在触发器中保存状态 - 每次评估都是独立的

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

### 短路求值顺序

混合触发器按速度排序评估：

1. **时间触发** - 本地计算，无 I/O
2. **数量触发** - 数据库查询，快速
3. **LLM 触发** - API 调用，最慢

**优点**: 最小化 API 调用，提高评估效率。

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `features/scheduler/SchedulerService` | 每分钟调用 `evaluate()` 检查所有组 |
| `features/scheduler/TriggerEvaluator` | 触发器工厂，根据类型创建实例 |
| `repositories/ArticleRepository` | 查询未处理文章数量 |
| `services/llm/DashScopeService` | LLM 触发器调用 |

## 添加新触发器步骤

1. 在 `triggers/` 目录创建新类 `NewTrigger.ts`
2. 实现 `Trigger` 接口：`export class NewTrigger implements Trigger`
3. 实现 `evaluate(groupId: string): Promise<TriggerResult>` 方法
4. 在 `TriggerEvaluator.ts` 的 `getTrigger()` 方法中添加新 case
5. 在 `shared/types/scheduler.ts` 中添加新的 triggerType 类型

## 测试

```bash
# 运行调度器测试
npm run test test/scheduler/

# 运行特定触发器测试
npx vitest test/scheduler/trigger-evaluator.test.ts
```
