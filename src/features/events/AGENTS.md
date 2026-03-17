# EventBus Module Knowledge Base

## Overview

事件总线系统：使用 EventEmitter2 实现解耦的异步通信。支持通配符订阅、事件历史追踪和类型安全的事件 payload。

## Structure

```
events/
└── EventBus.ts          # 事件总线核心 (240 行)
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 发射事件 | `EventBus.ts` (`publish()` 方法) | 发布事件到总线 |
| 订阅事件 | `EventBus.ts` (`subscribe()` 方法) | 注册事件处理器 |
| 添加事件类型 | `../../shared/types/events.ts` | 更新 `EventType` 和 `EventPayloadMap` |
| 查看事件历史 | `EventBus.ts` (`getEventHistory()` 方法) | 获取最近 100 个事件 |

## 事件类型

### 流水线事件
```typescript
type EventType =
  | 'pipeline:started'
  | 'pipeline:completed'
  | 'pipeline:failed'
  | 'pipeline:cancelled'
  | 'stage:started'
  | 'stage:completed'
  | 'stage:failed';
```

### 同步事件
```typescript
  | 'sync:started'
  | 'sync:completed'
  | 'sync:failed';
```

### 音频合成事件
```typescript
  | 'pipeline:audio:segment-completed'
  | 'pipeline:audio:merge-completed';
```

## EventBus 核心 API

### 发布事件
```typescript
publish<T extends EventType>(event: AppEvent<EventPayloadMap[T]>): void {
  // 添加到历史
  this.eventHistory.push(event);
  if (this.eventHistory.length > this.maxHistorySize) {
    this.eventHistory.shift();
  }

  // 记录日志
  this.logger.debug({ eventId: event.id, type: event.type }, 'Event published');

  // 发射事件
  this.emitter.emit(event.type, event);
  this.emitter.emit('*', event);  // 通配符事件
}
```

### 订阅事件
```typescript
subscribe<T extends EventType>(
  eventType: T,
  handler: EventHandler<T>,
  options?: { once?: boolean; immediate?: boolean }
): () => void {
  const subscription = { eventType, handler, once: options?.once };
  this.subscriptions.push(subscription);
  
  this.emitter.on(eventType, async (event: AppEvent) => {
    await handler(event);
  });
  
  // 返回取消订阅函数
  return () => this.unsubscribe(subscription);
}
```

### 创建并发布事件
```typescript
emit<T extends EventType>(
  type: T,
  payload: EventPayloadMap[T],
  source: string,
  metadata?: EventMetadata
): void {
  const event = createEvent(type, payload, source, metadata);
  this.publish(event);
}
```

## 事件 Payload 类型

### Pipeline Started
```typescript
{
  runId: string;
  groupId: string;
  stages: PipelineStage[];
  articlesCount: number;
}
```

### Stage Completed
```typescript
{
  runId: string;
  groupId: string;
  stage: PipelineStage;
  payload?: {
    segmentIndex?: number;
    totalSegments?: number;
    // ... 阶段特定数据
  };
}
```

### Audio Segment Completed
```typescript
{
  runId: string;
  groupId: string;
  segmentIndex: number;
  totalSegments: number;
  audioPath: string;
}
```

## 代码约定

### 事件历史追踪
自动保留最近 100 个事件：
```typescript
private readonly maxHistorySize = 100;

publish(event: AppEvent): void {
  this.eventHistory.push(event);
  if (this.eventHistory.length > this.maxHistorySize) {
    this.eventHistory.shift();
  }
  // ...
}
```

### 通配符订阅
支持订阅所有事件：
```typescript
eventBus.subscribe('*', (event) => {
  logger.info({ type: event.type }, 'Any event');
});
```

### 类型安全
使用泛型确保 payload 类型正确：
```typescript
interface EventPayloadMap {
  'pipeline:started': {
    runId: string;
    groupId: string;
    stages: PipelineStage[];
    articlesCount: number;
  };
  'stage:completed': {
    runId: string;
    groupId: string;
    stage: PipelineStage;
    payload?: unknown;
  };
  // ...
}
```

## 反模式

- ❌ 不要跳过事件发射 - TUI 依赖事件更新状态
- ❌ 不要忘记清理订阅 - 调用 unsubscribe 函数
- ❌ 不要在事件处理器中抛出未捕获异常 - 使用 try-catch
- ❌ 不要发射未定义的事件类型 - 先更新 `EventType`
- ❌ 不要阻塞事件循环 - 事件处理器应该是异步的

## 独特风格

### UTC+8 时间戳
所有事件时间戳转换为北京时间：
```typescript
timestamp: () => `,"time":"${new Date(new Date().getTime() + 8 * 3600 * 1000).toISOString().replace('Z', '+08:00')}"`
```

### 事件创建辅助函数
```typescript
export function createEvent<T extends EventType>(
  type: T,
  payload: EventPayloadMap[T],
  source: string,
  metadata?: EventMetadata
): AppEvent<T> {
  return {
    id: `evt-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    type,
    payload,
    timestamp: Date.now(),
    source,
    metadata,
  };
}
```

### 单次订阅
支持 `once` 选项：
```typescript
const unsubscribe = eventBus.subscribe(
  'pipeline:completed',
  (event) => { /* ... */ },
  { once: true }
);
```

## TUI 集成示例

### 订阅流水线进度
```typescript
// Generation.tsx
const unsubscribeSegment = eventBus.subscribe(
  'pipeline:audio:segment-completed',
  (event) => {
    if (event.payload?.groupId === groupId) {
      const { segmentIndex, totalSegments } = event.payload;
      setCurrentSegment(segmentIndex);
      setProgress((segmentIndex + 1) / totalSegments * 100);
    }
  }
);

// 清理订阅
useEffect(() => {
  return () => {
    if (unsubscribeSegment) unsubscribeSegment();
  };
}, []);
```

### 订阅流水线完成
```typescript
const unsubscribeComplete = eventBus.subscribe(
  'pipeline:completed',
  (event) => {
    if (event.payload?.groupId === groupId) {
      setIsRunning(false);
      setMessage('Pipeline completed successfully!');
    }
  }
);
```

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `features/pipeline/` | 发射流水线阶段事件 |
| `features/sync/` | 发射同步事件 |
| `tui/screens/Generation.tsx` | 订阅事件更新进度条 |
| `shared/types/events.ts` | 事件类型定义 |

## 调试

```typescript
// 查看事件历史
const history = eventBus.getEventHistory();
console.log('Recent events:', history);

// 订阅所有事件（调试用）
eventBus.subscribe('*', (event) => {
  console.log('Event:', event.type, event.payload);
});
```

## 添加新事件类型步骤

1. 在 `../../shared/types/events.ts` 中添加新事件类型到 `EventType`
2. 在 `EventPayloadMap` 中定义 payload 类型
3. 在发射位置调用 `eventBus.emit()` 或 `eventBus.publish()`
4. 在需要响应的位置调用 `eventBus.subscribe()`
5. 更新本文档

## 测试

```typescript
import { getEventBus } from './EventBus';

const eventBus = getEventBus();

// 测试事件订阅
const mockHandler = vi.fn();
const unsubscribe = eventBus.subscribe('pipeline:started', mockHandler);

// 发射事件
eventBus.emit('pipeline:started', {
  runId: 'run-123',
  groupId: 'grp-456',
  stages: ['source-summary'],
  articlesCount: 5,
}, 'test');

// 验证
expect(mockHandler).toHaveBeenCalled();

// 清理
unsubscribe();
```
