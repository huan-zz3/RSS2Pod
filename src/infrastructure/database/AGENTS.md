# Database Module Knowledge Base

## Overview

SQLite 数据库管理层：使用 better-sqlite3 提供同步数据库访问。负责模式创建、迁移和连接管理。

## Structure

```
database/
└── DatabaseManager.ts     # 数据库管理器 (282 行)
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 修改数据库模式 | `DatabaseManager.ts` (`createTables()` 方法) | 9 张表定义 |
| 添加迁移 | `DatabaseManager.ts` (`migrate()` 方法) | 版本控制和迁移逻辑 |
| 修改数据库配置 | `DatabaseManager.ts` (`initialize()` 方法) | WAL 模式、外键、超时设置 |

## 数据库模式

### 核心表 (9 张)

1. **schema_info** - 模式版本控制
2. **articles** - RSS 文章
3. **groups** - 播客组
4. **episodes** - 生成的节目
5. **source_summaries** - 每源摘要
6. **group_summaries** - 组级摘要
7. **pipeline_runs** - 流水线执行历史
8. **processing_state** - 并发控制
9. **feeds** - 订阅源列表

### 表结构详情

**schema_info**:
```sql
CREATE TABLE schema_info (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
-- 存储 version = "1"
```

**articles**:
```sql
CREATE TABLE articles (
  id TEXT PRIMARY KEY,
  fever_id INTEGER UNIQUE NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_name TEXT,
  published_at INTEGER NOT NULL,
  fetched_at INTEGER NOT NULL,
  is_read INTEGER DEFAULT 0,
  processed_by_group TEXT  -- JSON array
);
```

**groups**:
```sql
CREATE TABLE groups (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  source_ids TEXT NOT NULL,      -- JSON array
  trigger_type TEXT NOT NULL,
  trigger_config TEXT,           -- JSON object
  enabled INTEGER DEFAULT 1,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
```

**episodes**:
```sql
CREATE TABLE episodes (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL,
  title TEXT NOT NULL,
  script TEXT,                   -- JSON object
  audio_path TEXT,
  duration REAL,
  file_size INTEGER,
  pub_date INTEGER NOT NULL,
  guid TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (group_id) REFERENCES groups(id)
);
```

## DatabaseManager API

### 初始化
```typescript
constructor(dbPath: string) {
  this.dbPath = dbPath;
}

initialize(): Database.Database {
  // 创建目录
  const dir = dirname(this.dbPath);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }

  // 创建数据库连接
  this.db = new Database(this.dbPath);
  
  // 配置优化
  this.db.pragma('journal_mode = WAL');  // WAL 模式
  this.db.pragma('foreign_keys = ON');   // 外键约束
  this.db.pragma('busy_timeout = 5000'); // 5 秒超时

  // 创建表
  this.createTables();
  
  // 设置版本
  this.db.prepare(`
    INSERT OR REPLACE INTO schema_info (key, value) 
    VALUES ('version', ?)
  `).run(SCHEMA_VERSION.toString());
  
  return this.db;
}
```

### 获取连接
```typescript
getDb(): Database.Database {
  if (!this.db) {
    throw new Error('Database not initialized');
  }
  return this.db;
}
```

### 关闭连接
```typescript
close(): void {
  if (this.db) {
    this.db.close();
    this.db = null;
  }
}
```

## 代码约定

### WAL 模式
启用 Write-Ahead Logging 以获得更好的并发性能：
```typescript
this.db.pragma('journal_mode = WAL');
```

**优势**:
- 读写不阻塞
- 更好的并发性能
- 崩溃恢复更快

### 外键约束
强制执行引用完整性：
```typescript
this.db.pragma('foreign_keys = ON');
```

### 繁忙超时
处理并发访问：
```typescript
this.db.pragma('busy_timeout = 5000');  // 5000ms
```

### 单例模式
每个进程只有一个 DatabaseManager 实例：
```typescript
// 主程序中
const dbManager = new DatabaseManager(config.database.path);
dbManager.initialize();
const db = dbManager.getDb();

// 传递给 Repository
const groupRepo = new GroupRepository(db);
const articleRepo = new ArticleRepository(db);
```

## 反模式

- ❌ 不要创建多个 DatabaseManager 实例 - 每个进程一个
- ❌ 不要使用原始 SQL 字符串 - 使用 prepared statements
- ❌ 不要跳过外键 - 需要数据完整性
- ❌ 不要直接操作数据库文件 - 始终通过 DatabaseManager
- ❌ 不要忘记关闭连接 - 调用 `close()`

## 独特风格

### 模式版本控制
使用 `schema_info` 表跟踪版本：
```typescript
const SCHEMA_VERSION = 1;

// 初始化时设置
this.db.prepare(`
  INSERT OR REPLACE INTO schema_info (key, value) 
  VALUES ('version', ?)
`).run(SCHEMA_VERSION.toString());

// 迁移时检查
const currentVersion = this.db.prepare(`
  SELECT value FROM schema_info WHERE key = 'version'
`).get() as { value: string };
```

### JSON 字段存储
复杂字段使用 JSON 字符串：
```typescript
// 存储
const sourceIds = JSON.stringify(['1', '2', '3']);
db.prepare(`INSERT INTO groups (source_ids, ...) VALUES (?, ...)`).run(sourceIds);

// 读取
const group = db.prepare(`SELECT * FROM groups WHERE id = ?`).get(groupId);
const sourceIds = JSON.parse(group.source_ids as string);
```

### Prepared Statements
所有查询使用预处理语句：
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
| `tui/commands/` | 短生命周期：打开 → Repository 操作 → 关闭 |

## 数据库迁移

当前版本：1

**迁移模式**:
```typescript
migrate(): void {
  const currentVersion = this.getCurrentVersion();
  const targetVersion = 1;
  
  if (currentVersion < targetVersion) {
    logger.info({ from: currentVersion, to: targetVersion }, 'Running migration');
    
    // 执行迁移
    this.db.exec(`
      ALTER TABLE groups ADD COLUMN host_name TEXT;
      ALTER TABLE groups ADD COLUMN guest_name TEXT;
    `);
    
    this.setVersion(targetVersion);
  }
}
```

## 调试命令

```bash
# 初始化数据库
npm run cli -- db:init

# 查看数据库统计
npm run cli -- db:stats

# 直接查询 SQLite
sqlite3 data/rss2pod.db "SELECT * FROM groups;"
```

## 添加新表步骤

1. 在 `createTables()` 方法中添加 `CREATE TABLE` 语句
2. 在 `../../shared/types/` 中添加 TypeScript 类型
3. 创建对应的 Repository 类
4. 更新 `schema_info.version`（如果需要迁移）
5. 更新本文档

## 测试

```bash
# 测试数据库初始化
npm run cli -- db:init

# 查看表结构
sqlite3 data/rss2pod.db ".schema"

# 运行 Repository 测试
npm run test test/repositories/
```
