# Infrastructure Knowledge Base

## Overview

底层基础设施：SQLite 数据库层和外部 API 客户端。提供数据持久化和外部服务集成基础。

## Structure

```
infrastructure/
├── database/
│   └── DatabaseManager.ts     # SQLite 初始化、模式、迁移
└── external/
    └── FeverClient.ts         # Fever API 客户端 (TT-RSS)
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 修改数据库模式 | `database/DatabaseManager.ts` (`createTables` 方法) | 9 张表定义 |
| 添加数据库迁移 | `database/DatabaseManager.ts` (`migrate` 方法) | 版本控制和迁移逻辑 |
| 添加外部 API 客户端 | `external/` 目录 | 遵循 FeverClient 模式 |
| 修改 Fever API 调用 | `external/FeverClient.ts` | TT-RSS Fever 插件 API |

## 数据库层详情

**DatabaseManager** (`database/DatabaseManager.ts`)：

**初始化**：
```typescript
export class DatabaseManager {
  private db: Database.Database;
  
  constructor(dbPath: string) {
    this.db = new Database(dbPath);
  }
  
  initialize(): void {
    // 启用 WAL 模式（更好的并发性能）
    this.db.pragma('journal_mode = WAL');
    
    // 启用外键约束
    this.db.pragma('foreign_keys = ON');
    
    // 设置繁忙超时（5 秒）
    this.db.pragma('busy_timeout = 5000');
    
    // 创建表
    this.createTables();
  }
}
```

**数据库模式** (9 张表)：
```sql
-- 文章表
CREATE TABLE articles (
  id TEXT PRIMARY KEY,
  feed_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  content TEXT,
  url TEXT,
  author TEXT,
  published_at INTEGER,
  fetched_at INTEGER NOT NULL
);

-- 组表
CREATE TABLE groups (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  source_ids TEXT NOT NULL,  -- JSON array
  trigger_type TEXT NOT NULL,
  trigger_config TEXT,       -- JSON object
  enabled INTEGER DEFAULT 1,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

-- 节目表
CREATE TABLE episodes (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  audio_path TEXT,
  duration INTEGER,
  file_size INTEGER,
  published_at INTEGER,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (group_id) REFERENCES groups(id)
);

-- 源摘要表
CREATE TABLE source_summaries (
  id TEXT PRIMARY KEY,
  source_id INTEGER NOT NULL,
  group_id TEXT NOT NULL,
  summary TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (group_id) REFERENCES groups(id)
);

-- 组摘要表
CREATE TABLE group_summaries (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL,
  summary TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (group_id) REFERENCES groups(id)
);

-- 流水线执行历史表
CREATE TABLE pipeline_runs (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL,
  status TEXT NOT NULL,
  stages TEXT NOT NULL,      -- JSON object
  started_at INTEGER NOT NULL,
  completed_at INTEGER,
  error TEXT,
  FOREIGN KEY (group_id) REFERENCES groups(id)
);

-- 处理状态表（并发控制）
CREATE TABLE processing_state (
  id TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);

-- 订阅源表
CREATE TABLE feeds (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  site_url TEXT,
  last_updated INTEGER
);

-- 模式版本表
CREATE TABLE schema_info (
  version INTEGER NOT NULL
);
```

**数据库迁移**：
```typescript
migrate(): void {
  const currentVersion = this.getCurrentVersion();
  const targetVersion = 1;  // 当前目标版本
  
  if (currentVersion < targetVersion) {
    logger.info({ from: currentVersion, to: targetVersion }, 'Running migration');
    
    // 执行迁移逻辑
    this.db.exec(`
      ALTER TABLE groups ADD COLUMN host_name TEXT;
      ALTER TABLE groups ADD COLUMN guest_name TEXT;
    `);
    
    this.setVersion(targetVersion);
  }
}
```

## 外部 API 客户端详情

**FeverClient** (`external/FeverClient.ts`, 313 行)：

**认证**：
```typescript
export class FeverClient {
  private baseUrl: string;
  private apiKey: string;
  private client: AxiosInstance;
  
  constructor(config: FeverConfig) {
    this.baseUrl = config.baseUrl;
    this.apiKey = this.generateApiKey(config.email, config.password);
    
    this.client = axios.create({
      baseURL: this.baseUrl,
      params: { api_key: this.apiKey },
    });
  }
  
  private generateApiKey(email: string, password: string): string {
    return crypto.createHash('md5')
      .update(`${email}:${password}`)
      .digest('hex');
  }
}
```

**主要方法**：
```typescript
// 获取订阅源列表
async getFeeds(): Promise<Feed[]> {
  const response = await this.get<{ feeds: Feed[] }>({ feeds: 1 });
  return response.feeds.map(feed => ({
    id: feed.id,
    title: feed.title,
    url: feed.url,
    siteUrl: feed.site_url,
  }));
}

// 获取文章
async getArticles(options?: {
  since?: number;
  limit?: number;
}): Promise<Article[]> {
  const params: Record<string, string | number> = { items: 1 };
  if (options?.since) params.since = options.since;
  if (options?.limit) params.count = options.limit;
  
  const response = await this.get<{ items: Article[] }>(params);
  return response.items;
}

// 标记文章为已读
async markAsRead(articleIds: number[]): Promise<void> {
  await this.post({ mark: 'items', as: 'read', id: articleIds.join(',') });
}
```

**错误处理**：
```typescript
async get<T>(params: Record<string, string | number>): Promise<T> {
  try {
    const response = await this.client.get('/', { params });
    return response.data as T;
  } catch (error) {
    logger.error({ error }, 'Fever API GET request failed');
    throw error;  // 记录日志后重新抛出
  }
}
```

## 代码约定

- **数据库单例** - 每个进程只有一个 DatabaseManager 实例
- **WAL 模式** - 启用 WAL 以获得更好的并发性能
- **外键启用** - 强制执行引用完整性
- **预处理语句** - 所有查询使用 prepared statements

## 反模式

- ❌ 不要使用原始 SQL 字符串 - 使用 prepared statements
- ❌ 不要跳过外键 - 需要数据完整性
- ❌ 不要创建多个 DatabaseManager 实例
- ❌ 不要直接操作数据库文件 - 始终通过 DatabaseManager

## 独特风格

- **模式版本控制** - schema_info 表跟踪版本
- **繁忙超时** - 5000ms 用于并发访问
- **JSON 字段存储** - 复杂字段（source_ids, trigger_config）使用 JSON 字符串存储

## Prepared Statements 使用

```typescript
// 插入
db.prepare(`
  INSERT INTO groups (id, name, source_ids, trigger_type, created_at, updated_at)
  VALUES (?, ?, ?, ?, ?, ?)
`).run(id, name, JSON.stringify(sourceIds), triggerType, Date.now(), Date.now());

// 查询
const group = db.prepare(`
  SELECT * FROM groups WHERE id = ?
`).get(groupId) as GroupRow | undefined;

// 更新
db.prepare(`
  UPDATE groups SET name = ?, updated_at = ? WHERE id = ?
`).run(name, Date.now(), groupId);

// 删除
db.prepare(`
  DELETE FROM groups WHERE id = ?
`).run(groupId);
```

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `repositories/` | 直接使用 DatabaseManager 的数据库实例 |
| `features/` | 通过 repositories 间接访问数据库 |
| `services/` | FeverClient 被 features 调用 |

## 测试

```bash
# 测试 Fever API 连接
npm run cli -- fever:test

# 测试数据库初始化
npm run cli -- db:init

# 查看数据库统计
npm run cli -- db:stats
```

## 添加新的外部 API 客户端

遵循 FeverClient 模式：

```typescript
// external/NewApiClient.ts
export class NewApiClient {
  private baseUrl: string;
  private client: AxiosInstance;
  
  constructor(config: NewApiConfig) {
    this.baseUrl = config.baseUrl;
    this.client = axios.create({
      baseURL: this.baseUrl,
      headers: { 'Authorization': `Bearer ${config.apiKey}` },
    });
  }
  
  async getData(): Promise<Data[]> {
    const response = await this.client.get<DataResponse>('/endpoint');
    return response.data.items;
  }
}
```
