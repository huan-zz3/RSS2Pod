# Infrastructure 知识库

## 概述

底层基础设施：SQLite 数据库层和外部 API 客户端。

## 结构

```
infrastructure/
├── database/
│   └── DatabaseManager.ts     # SQLite 初始化、模式
└── external/
    └── FeverClient.ts         # Fever API 客户端
```

## 查找指南

| 任务 | 位置 |
|------|------|
| 修改数据库模式 | `database/DatabaseManager.ts` (createTables) |
| 添加数据库迁移 | `database/DatabaseManager.ts` (migrate 方法) |
| 添加外部 API 客户端 | `external/` (遵循 FeverClient 模式) |
| 修改 Fever API 调用 | `external/FeverClient.ts` |

## 代码约定

- **数据库单例** - 每个进程一个 DatabaseManager 实例
- **WAL 模式启用** - 更好的并发性
- **外键启用** - 强制执行引用完整性
- **预编译语句** - 所有查询使用预编译语句

## 反模式

- ❌ 不要使用原始 SQL 字符串 - 使用预编译语句
- ❌ 不要跳过外键 - 需要数据完整性
- ❌ 不要创建多个 DatabaseManager 实例

## 独特风格

- **模式版本控制** - schema_info 表跟踪版本
- **繁忙超时** - 5000ms 用于并发访问
