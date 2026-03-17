# Repositories Module Knowledge Base

## Overview

数据访问层：封装 SQLite 数据库操作，提供类型安全的 CRUD 接口。每个 Repository 对应一张数据库表。

## Structure

```
repositories/
├── ArticleRepository.ts     # 文章表访问 (articles)
└── GroupRepository.ts       # 组表访问 (groups)
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 文章 CRUD | `ArticleRepository.ts` | insert, findById, findByFeverId, findUnprocessed |
| 组 CRUD | `GroupRepository.ts` | create, update, delete, findById, findAll |
| 类型定义 | 对应 Repository 文件顶部 | `Article` interface, `Group` interface |

## Repository Pattern

**标准模式**：
```typescript
export class ArticleRepository {
  private db: Database.Database;
  
  constructor(db: Database.Database) {
    this.db = db;
  }
  
  // 插入/更新
  insert(article: Article): void {
    const stmt = this.db.prepare(`INSERT OR REPLACE INTO articles (...) VALUES (?, ?, ...)`);
    stmt.run(article.id, article.feverId, ...);
  }
  
  // 查询
  findById(id: string): Article | undefined {
    const row = this.db.prepare(`SELECT * FROM articles WHERE id = ?`).get(id);
    return row ? this.mapRowToArticle(row) : undefined;
  }
  
  // 批量操作
  insertMany(articles: Article[]): void {
    const transaction = this.db.transaction((items) => {
      for (const article of items) {
        this.insert(article);
      }
    });
    transaction(articles);
  }
}
```

## 代码约定

- **依赖注入** - 构造函数接收 `Database.Database` 实例
- **Prepared Statements** - 所有查询使用 `db.prepare()`
- **类型映射** - 数据库行 → TypeScript 接口（`mapRowToArticle` 等）
- **事务支持** - 批量操作使用 `db.transaction()`
- **时间戳** - Unix 秒数（`Math.floor(date.getTime() / 1000)`）

## 反模式

- ❌ 不要直接操作数据库 - 始终通过 Repository
- ❌ 不要在 Repository 中放业务逻辑 - 仅 CRUD 操作
- ❌ 不要跳过类型映射 - 始终返回 TypeScript 接口
- ❌ 不要使用原始 SQL 字符串 - 使用 prepared statements
- ❌ 不要忘记关闭数据库连接 - 由 DatabaseManager 管理

## 独特风格

- **JSON 字段存储** - `processed_by_group`, `source_ids`, `trigger_config` 使用 `JSON.stringify()`
- **唯一 ID 格式** - `art-{feverId}`, `grp-{timestamp}`
- **去重逻辑** - `findUnprocessed()` 使用 `NOT LIKE` 查询 JSON 字段
- **乐观更新** - `INSERT OR REPLACE` 避免重复检查

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `infrastructure/database/` | 直接使用 DatabaseManager 的数据库实例 |
| `features/` | 通过 Repository 间接访问数据库 |
| `tui/commands/` | 短生命周期：打开 → Repository 操作 → 关闭 |

## 测试

```bash
# 运行 Repository 相关测试
npm run test test/repositories/

# 测试特定 Repository
npx vitest test/repositories/article-repository.test.ts
```

## 添加新 Repository

遵循现有模式：

```typescript
// NewRepository.ts
import Database from 'better-sqlite3';

export interface NewEntity {
  id: string;
  // ... fields
}

export class NewRepository {
  private db: Database.Database;
  
  constructor(db: Database.Database) {
    this.db = db;
  }
  
  create(entity: NewEntity): void {
    const stmt = this.db.prepare(`INSERT INTO new_table (...) VALUES (?, ?, ...)`);
    stmt.run(entity.id, ...);
  }
  
  findById(id: string): NewEntity | undefined {
    const row = this.db.prepare(`SELECT * FROM new_table WHERE id = ?`).get(id);
    return row ? this.mapRowToEntity(row) : undefined;
  }
  
  private mapRowToEntity(row: Record<string, unknown>): NewEntity {
    return {
      id: row.id as string,
      // ... map fields
    };
  }
}
```
