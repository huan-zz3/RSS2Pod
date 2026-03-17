# External API Module Knowledge Base

## Overview

外部 API 客户端层：封装与外部服务的通信。当前包含 Fever API 客户端（TT-RSS），遵循统一的客户端模式。

## Structure

```
external/
└── FeverClient.ts         # Fever API 客户端 (317 行，TT-RSS)
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 添加新 API 客户端 | `external/` 目录创建新类 | 遵循 FeverClient 模式 |
| 修改 Fever API 调用 | `FeverClient.ts` | 各个 API 方法 |
| 修改认证逻辑 | `FeverClient.ts` (`generateApiKey()` 方法) | MD5 密钥生成 |

## Fever API 客户端

### 认证
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
    return createHash('md5')
      .update(`${email}:${password}`)
      .digest('hex');
  }
}
```

### 主要方法

#### 获取订阅源列表
```typescript
async getFeeds(): Promise<Feed[]> {
  const response = await this.get<{ feeds: Feed[] }>({ feeds: 1 });
  return response.feeds.map(feed => ({
    id: feed.id,
    title: feed.title,
    url: feed.url,
    siteUrl: feed.site_url,
  }));
}
```

#### 获取文章
```typescript
async getItems(options?: {
  maxId?: number;
  since?: number;
  limit?: number;
}): Promise<FeverItem[]> {
  const params: Record<string, string | number> = { items: 1 };
  if (options?.since) params.since = options.since;
  if (options?.limit) params.count = options.limit;
  if (options?.maxId) params.max_id = options.maxId;
  
  const response = await this.get<{ items: FeverItem[] }>(params);
  return response.items;
}
```

#### 标记文章为已读
```typescript
async markAsRead(articleIds: number[]): Promise<void> {
  await this.post({ mark: 'items', as: 'read', id: articleIds.join(',') });
}
```

#### 获取未读文章 ID
```typescript
async getUnreadItemIds(): Promise<string> {
  const response = await this.get<{ unread_item_ids: string }>({ unread: 1 });
  return response.unread_item_ids;
}
```

### 错误处理
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

### Axios 实例
每个客户端创建独立的 Axios 实例：
```typescript
this.client = axios.create({
  baseURL: this.baseUrl,
  params: { api_key: this.apiKey },
  timeout: 10000,  // 10 秒超时
});
```

### Zod Schema 验证
所有 API 响应使用 Zod 验证：
```typescript
const FeverAuthSchema = z.object({
  auth: z.number(),
  api_version: z.number(),
});

const ItemSchema = z.object({
  id: z.number(),
  title: z.string(),
  html: z.string(),
  url: z.string(),
  feed_id: z.number(),
  is_read: z.number(),
  is_saved: z.number(),
  created_on: z.number().optional(),
});
```

### 错误传播
记录日志后重新抛出，让上层处理：
```typescript
catch (error) {
  logger.error({ error }, 'Fever API request failed');
  throw error;
}
```

## 反模式

- ❌ 不要硬编码 API 密钥 - 使用 `config.json`
- ❌ 不要跳过 Zod 验证 - 需要类型安全
- ❌ 不要直接调用 Fever API - 通过 FeverClient
- ❌ 不要忽略错误处理 - 记录日志后重新抛出
- ❌ 不要在客户端中保存状态 - 无状态设计

## 独特风格

### MD5 认证密钥
Fever API 使用 MD5(email:password)：
```typescript
private generateApiKey(email: string, password: string): string {
  return createHash('md5')
    .update(`${email}:${password}`)
    .digest('hex');
}
```

### 统一参数格式
所有 API 调用使用统一的参数对象：
```typescript
// GET 请求
await this.get({ items: 1, since: 1234567890 });

// POST 请求
await this.post({ mark: 'items', as: 'read', id: '1,2,3' });
```

### HTML 清理
提供 `stripHtml()` 方法清理文章内容：
```typescript
private stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, '');
}
```

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `features/sync/` | 使用 FeverClient 获取文章 |
| `shared/config/` | 从 `config.json` 读取 Fever 配置 |
| `infrastructure/database/` | 获取的文章保存到数据库 |

## 配置示例

**config.json**:
```json
{
  "fever": {
    "baseUrl": "https://your-ttrss/plugins/fever",
    "email": "your-email",
    "password": "your-password"
  }
}
```

## 调试命令

```bash
# 测试 Fever API 连接
npm run cli -- fever:test

# 同步订阅源列表
npm run cli -- fever:sync-feeds

# 缓存文章
npm run cli -- fever:cache-articles -l 100
```

## 添加新 API 客户端步骤

遵循 FeverClient 模式：

1. 在 `external/` 目录创建新类 `NewApiClient.ts`
2. 定义配置接口和 Zod Schema
3. 创建 Axios 实例
4. 实现 API 方法
5. 添加错误处理和日志记录
6. 在 `features/` 中使用新客户端
7. 更新本文档

**示例**:
```typescript
// external/NewApiClient.ts
import axios, { AxiosInstance } from 'axios';
import { z } from 'zod';
import pino from 'pino';

const logger = pino({ name: 'new-api-client' });

const NewApiResponseSchema = z.object({
  success: z.boolean(),
  data: z.unknown(),
});

export interface NewApiConfig {
  baseUrl: string;
  apiKey: string;
}

export class NewApiClient {
  private baseUrl: string;
  private client: AxiosInstance;
  
  constructor(config: NewApiConfig) {
    this.baseUrl = config.baseUrl;
    this.client = axios.create({
      baseURL: this.baseUrl,
      headers: { 'Authorization': `Bearer ${config.apiKey}` },
      timeout: 10000,
    });
  }
  
  async getData(): Promise<unknown> {
    try {
      const response = await this.client.get('/endpoint');
      return NewApiResponseSchema.parse(response.data).data;
    } catch (error) {
      logger.error({ error }, 'New API request failed');
      throw error;
    }
  }
}
```

## 测试

```bash
# 测试 Fever API 连接
npm run cli -- fever:test

# 查看 Fever 配置
npm run cli -- config:show | grep -A 3 '"fever"'
```
