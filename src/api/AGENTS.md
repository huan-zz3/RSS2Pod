# API Module Knowledge Base

## Overview

REST API 服务器：使用 Fastify 框架，提供播客 Feed 和组管理的 HTTP 端点。支持 CORS 和静态文件服务。

## Structure

```
api/
└── index.ts              # API 入口 (203 行，Fastify 服务器)
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 添加新端点 | `index.ts` | 在 `createApiServer()` 中添加路由 |
| 修改现有端点 | `index.ts` | 搜索 `fastify.get()` 或 `fastify.post()` |
| 修改服务器配置 | `index.ts` | `createApiServer()` 函数 |

## API 端点

### GET `/api/health`
健康检查端点，返回服务器状态和时间戳。

**响应**:
```json
{
  "status": "ok",
  "timestamp": "2026-03-17T09:00:00.000Z"
}
```

### GET `/api/groups`
列出所有组。

**响应**:
```json
{
  "groups": [
    {
      "id": "grp-123",
      "name": "科技新闻",
      "description": "科技类新闻聚合",
      "enabled": true,
      "triggerType": "count",
      "sourceCount": 3
    }
  ]
}
```

### GET `/api/groups/:id`
获取单个组详情。

**响应**:
```json
{
  "group": {
    "id": "grp-123",
    "name": "科技新闻",
    "description": "科技类新闻聚合",
    "sourceIds": ["1", "2", "3"],
    "triggerType": "count",
    "triggerConfig": { "threshold": 10 },
    "enabled": true
  }
}
```

### GET `/api/feeds/:groupId`
获取播客 RSS Feed XML。

**响应**: `application/rss+xml` 格式的 RSS 2.0 Feed

**关键逻辑**:
- 从数据库查询最近 10 个 episodes
- 使用 `config.api.baseUrl` 构造 enclosure URL
- 动态生成 RSS XML

### POST `/api/groups/:id/generate`
手动触发流水线生成。

**请求**: 组 ID（URL 参数）

**响应**:
```json
{
  "status": "started",
  "groupId": "grp-123",
  "message": "Pipeline execution started"
}
```

**限制**: 仅当组启用时成功

### GET `/api/stats`
获取系统统计信息。

**响应**:
```json
{
  "articles": 150,
  "groups": 5,
  "episodes": 23
}
```

## 代码约定

### 配置使用
所有 API 配置来自 `config.json`：
```typescript
const config = loadConfig();
const host = options.host || config.api.host;
const port = options.port || config.api.port;
const baseUrl = config.api.baseUrl;  // Feed URL 构造
```

### 静态文件服务
媒体文件通过 `@fastify/static` 提供：
```typescript
await fastify.register(fastifyStatic, {
  root: mediaPath,
  prefix: '/api/media/',
  decorateReply: false,
});
```

**访问路径**: `http://host:port/api/media/{relativePath}`

### CORS 配置
允许所有来源（开发环境）：
```typescript
await fastify.register(cors, {
  origin: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
});
```

## 反模式

- ❌ 不要在 API 层放置业务逻辑 - 调用服务层
- ❌ 不要硬编码 API 密钥 - 使用 `config.json`
- ❌ 不要跳过错误处理 - 使用 `setErrorHandler`
- ❌ 不要直接调用流水线阶段 - 通过 `PipelineOrchestrator`
- ❌ 不要忽略类型安全 - 所有响应有 TypeScript 类型

## 独特风格

### 自动启动逻辑
API 服务器支持直接执行：
```typescript
// 文件末尾
if (import.meta.url === `file://${process.argv[1]}`) {
  createApiServer().then(async (server) => {
    await server.start();
  });
}
```

**效果**: `tsx src/api/index.ts` 直接启动服务器

### Feed URL 构造
使用 `config.api.baseUrl` 而非硬编码：
```typescript
const baseUrl = config.api.baseUrl;
const feedUrl = `${baseUrl}/api/feeds/${groupId}`;
const enclosureUrl = `${baseUrl}/api/media/${audioPath}`;
```

**优势**: 支持生产环境自定义域名

## 启动方式

```bash
# 启动 API 服务器
npm run api

# 访问健康检查
curl http://localhost:3000/api/health

# 获取播客 Feed
curl http://localhost:3000/api/feeds/grp-123
```

## 配置示例

**config.json**:
```json
{
  "api": {
    "host": "0.0.0.0",
    "port": 3000,
    "baseUrl": "http://localhost:3000"
  }
}
```

**生产环境**:
```json
{
  "api": {
    "host": "0.0.0.0",
    "port": 3000,
    "baseUrl": "https://podcast.example.com"
  }
}
```

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `services/feed/` | 使用 `PodcastFeedGenerator` 生成 RSS |
| `repositories/` | 通过 `GroupRepository` 访问数据 |
| `infrastructure/database/` | 使用 `DatabaseManager` 初始化数据库 |
| `shared/config/` | 从 `config.json` 读取配置 |

## 错误处理

全局错误处理器：
```typescript
fastify.setErrorHandler((error, _request, reply) => {
  logger.error({ error }, 'API error');
  reply.code(500).send({ error: 'Internal server error' });
});
```

## 添加新端点步骤

1. 在 `index.ts` 的 `createApiServer()` 函数中添加路由
2. 使用 `fastify.get()` 或 `fastify.post()`
3. 添加适当的错误处理
4. 返回 JSON 响应或 XML（Feed）
5. 更新本文档

## 测试

```bash
# 启动 API 服务器
npm run api

# 测试健康检查
curl http://localhost:3000/api/health

# 测试组列表
curl http://localhost:3000/api/groups

# 测试 Feed 生成
curl http://localhost:3000/api/feeds/grp-123
```
