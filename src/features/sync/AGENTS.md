# SyncService Module Knowledge Base

## Overview

独立同步服务：定时从 Fever API 获取文章并保存到本地数据库。与 Scheduler 分离，有独立的定时逻辑（默认 600 秒间隔）。

## Structure

```
sync/
├── SyncService.ts          # 同步服务核心 (182 行)
└── types.ts               # 类型定义 (SyncConfig, SyncResult, SyncStatus)
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 启动/停止同步 | `SyncService.ts` (`start()`, `stop()`) | node-cron 调度 |
| 同步单组 | `SyncService.ts` (`syncGroup()`) | 按 sourceIds 过滤 |
| 同步所有组 | `SyncService.ts` (`syncAllGroups()`) | 遍历 enabled groups |
| 配置定义 | `types.ts` | `SyncConfigSchema` (enabled, interval, maxArticlesPerSync) |

## SyncService 核心逻辑

**定时同步**：
```typescript
export class SyncService {
  private scheduledTask: ScheduledTask | null = null;
  
  start(): void {
    const cronExpression = this.generateCronFromInterval(this.config.interval);
    this.scheduledTask = schedule(cronExpression, () => {
      this.syncAllGroups();
    });
  }
  
  async syncGroup(group: Group): Promise<SyncResult> {
    const articles = await this.feverClient.getItems({ maxId: 2147483647 });
    
    for (const item of articles.slice(0, this.config.maxArticlesPerSync)) {
      if (group.sourceIds.includes(item.feedId.toString())) {
        const existed = this.articleRepo.findByFeverId(item.id);
        this.articleRepo.insert({
          id: `art-${item.id}`,
          feverId: item.id,
          title: item.title,
          content: this.stripHtml(item.html),
          // ...
        });
      }
    }
  }
}
```

## 代码约定

- **组过滤** - 只保存 `group.sourceIds` 匹配的订阅源文章
- **增量同步** - 通过 `findByFeverId()` 检查已存在
- **事件发射** - 完成后发射 `sync:completed` 事件
- **状态跟踪** - `lastSyncTime`, `lastMaxId` 记录同步状态
- **HTML 清理** - `stripHtml()` 方法移除 HTML 标签

## 反模式

- ❌ 不要直接调用 Fever API - 通过 SyncService
- ❌ 不要跳过组过滤 - 只保存相关订阅源
- ❌ 不要忘记发射事件 - TUI 依赖事件更新状态
- ❌ 不要手动管理同步状态 - 使用 `lastSyncTime` Map
- ❌ 不要忽略 `maxArticlesPerSync` 限制 - 避免 API 超限

## 独特风格

- **Cron 转换** - `generateCronFromInterval()` 将秒数转换为 cron 表达式
- **双模式同步** - 支持 `syncGroup()` (单组) 和 `syncAllGroups()` (所有组)
- **结果聚合** - `syncAllGroups()` 聚合所有组的 `articlesSynced` 和 `maxId`
- **错误隔离** - 单个组失败不影响其他组同步

## 配置示例

```json
"sync": {
  "enabled": true,
  "interval": 600,
  "maxArticlesPerSync": 100
}
```

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `enabled` | `true` | 是否启用自动同步 |
| `interval` | `600` | 同步间隔（秒） |
| `maxArticlesPerSync` | `100` | 每次同步最多获取的文章数 |

## Cron 转换规则

```typescript
private generateCronFromInterval(seconds: number): string {
  if (seconds <= 60) return '* * * * *';        // 每分钟
  if (seconds <= 300) return '*/5 * * * *';     // 每 5 分钟
  if (seconds <= 600) return '*/10 * * * *';    // 每 10 分钟
  // ...
}
```

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `infrastructure/external/` | 使用 FeverClient 获取文章 |
| `repositories/` | 使用 ArticleRepository, GroupRepository 保存数据 |
| `features/events/` | 发射 `sync:completed` 事件通知 TUI |
| `features/scheduler/` | 独立运行，不依赖 SchedulerService |

## TUI 集成

**TUI 命令** (`src/tui/commands/fever.ts`):
```typescript
export async function syncArticles(groupId?: string): Promise<SyncResult> {
  const config = loadConfig();
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  
  try {
    const syncService = new SyncService(
      new GroupRepository(dbManager.getDb()),
      new ArticleRepository(dbManager.getDb()),
      new FeverClient(config.fever),
      getEventBus(),
      config.sync,
    );
    
    if (groupId) {
      return await syncService.syncGroup(group);
    } else {
      const groups = groupRepo.findAll({ enabledOnly: true });
      let totalArticles = 0;
      for (const group of groups) {
        const result = await syncService.syncGroup(group);
        totalArticles += result.articlesSynced;
      }
      return { synced: true, articlesSynced: totalArticles, ... };
    }
  } finally {
    dbManager.close();
  }
}
```

## 测试

```bash
# 测试同步功能
npm run cli -- sync:run <groupId>

# 查看同步状态
npm run cli -- sync:status

# 手动触发同步
npm run cli -- scheduler:start
```
