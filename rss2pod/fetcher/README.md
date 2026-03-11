# RSS2Pod Fetcher Module

RSS 采集模块 - 用于从 Fever API 和 RSS 源获取、管理和拼接文章

## 目录结构

```
rss2pod/fetcher/
├── __init__.py           # 包初始化
├── fever_client.py       # Fever API 客户端（支持缓存）
├── fever_cache.py        # Fever API 本地缓存管理器
├── rss_fetcher.py        # RSS 内容获取与文本提取
├── article_manager.py    # 文章存储与管理
├── example_usage.py      # 使用示例
└── README.md             # 本文档
```

## 功能模块

### 1. Fever API 客户端 (`fever_client.py`)

与 Fever API 兼容的 RSS 阅读器（如 FreshRSS、Miniflux、TT-RSS）交互。

**主要功能：**
- 认证管理（支持 API Key 生成）
- 获取订阅源列表
- 获取文章内容
- 标记已读/收藏
- **本地缓存支持**（读取操作从 SQLite 缓存获取，写入操作同步更新缓存和 API）

**使用示例：**
```python
from fetcher.fever_client import FeverClient, FeverCredentials

# 生成 API Key
api_key = FeverClient.generate_api_key('email@example.com', 'password')

# 创建客户端（不带缓存）
credentials = FeverCredentials(
    api_url='https://your-server.com/fever',
    api_key=api_key
)
client = FeverClient(credentials)

# 创建客户端（带缓存模式）
client = FeverClient(credentials, db_path='rss2pod.db')

# 同步缓存（首次使用或定期更新）
result = client.sync_cache(limit=1500)
print(f"同步完成：{result.items_synced} 篇，新增 {result.new_items} 篇")

# 获取订阅源
feeds = client.get_feeds()

# 获取文章（从缓存）
items = client.get_items(limit=50)

# 获取未读文章（从缓存）
unread = client.get_unread_items(limit=20)

# 标记已读（同时更新缓存和 API）
client.mark_as_read([item['id'] for item in unread[:5]])
```

### 2. Fever API 缓存管理器 (`fever_cache.py`)

管理 Fever API 文章的本地 SQLite 缓存。

**主要功能：**
- 文章数据缓存（id, feed_id, title, author, html, url, is_read, is_saved, created_on_time）
- 增量同步（避免重复插入）
- 状态管理（已读/未读/收藏）
- 统计信息查询

**数据结构：**
```python
FeverCacheItem:
  - id: int                    # Fever API 文章 ID（主键）
  - feed_id: int               # 订阅源 ID
  - title: str                 # 标题
  - author: str                # 作者
  - html: str                  # 原始 HTML 内容
  - url: str                   # 原文链接
  - is_read: bool              # 是否已读
  - is_saved: bool             # 是否已收藏
  - created_on_time: int       # 创建时间戳
  - fetched_at: str            # 本地获取时间（ISO 格式）
```

**使用示例：**
```python
from fetcher.fever_cache import FeverCacheManager, SyncResult

# 创建缓存管理器
manager = FeverCacheManager(db_path='rss2pod.db')

# 从 Fever API 同步到缓存
result = manager.sync_items(client, limit=1500)
print(f"同步：{result.items_synced} 篇，新增：{result.new_items} 篇")

# 获取文章
items = manager.get_items(limit=50)
unread = manager.get_unread_items(limit=20)
by_feed = manager.get_items(feed_id=123, limit=10)

# 获取统计
stats = manager.get_stats()
print(f"总文章：{stats['total_items']}, 未读：{stats['unread_count']}")

# 标记状态（仅更新缓存）
manager.mark_as_read([1, 2, 3])
manager.save_item(456)

# 关闭连接
manager.close()
```

### 3. RSS 获取器 (`rss_fetcher.py`)

从 RSS/Atom 源获取内容并提取纯文本。

**主要功能：**
- 解析 RSS/Atom 源
- 提取文章元数据（标题、链接、作者、时间）
- HTML 内容转纯文本
- 支持自定义 User-Agent

**使用示例：**
```python
from fetcher.rss_fetcher import RSSFetcher, FeedManager

# 单个源
fetcher = RSSFetcher()
articles = fetcher.fetch_feed('https://example.com/feed.xml')

# 多个源管理
manager = FeedManager()
manager.add_feed('博客', 'https://example.com/feed.xml')
manager.add_feed('新闻', 'https://news.example.com/rss')
all_articles = manager.fetch_all()
```

### 4. 文章管理器 (`article_manager.py`)

文章的存储、检索、状态管理和拼接策略。

**主要功能：**
- JSON 文件存储
- 按源/状态索引
- 文章去重（基于 MD5）
- Token 数量估算
- 文章拼接（控制 token 上限）

**数据结构：**
```python
Article:
  - id: str              # 唯一标识
  - title: str           # 标题
  - source: str          # 归属源
  - source_url: str      # 源 URL
  - link: str            # 原文链接
  - published: str       # 发布时间
  - content: str         # HTML 内容
  - text_content: str    # 纯文本
  - author: str          # 作者
  - status: str          # 处理状态
  - token_count: int     # Token 数量
```

**使用示例：**
```python
from fetcher.article_manager import ArticleManager, Article, ArticleConcatenator

# 创建管理器
manager = ArticleManager(storage_dir="articles")

# 添加文章
article = Article(
    id=Article.generate_id(title, link, source),
    title="文章标题",
    source="源名称",
    # ... 其他字段
)
manager.add_article(article)

# 拼接文章
concatenator = ArticleConcatenator(max_tokens=4000)
combined = concatenator.concatenate_articles(articles, source="源名称")
```

## 文章拼接策略

`ArticleConcatenator` 实现智能拼接，控制 token 上限：

### 策略选项

1. **chronological** - 按时间正序（旧→新）
2. **reverse_chronological** - 按时间倒序（新→旧）
3. **by_length** - 按文章长度

### Token 控制

- 默认上限：4000 tokens
- 自动估算每篇文章的 token 数
- 达到上限时停止添加
- 支持自定义上限

**使用示例：**
```python
concatenator = ArticleConcatenator(max_tokens=4000)

# 基本拼接
combined = concatenator.concatenate_articles(
    articles, 
    source="博客",
    include_metadata=True
)

# 使用策略
combined = concatenator.concatenate_with_strategy(
    articles,
    source="博客",
    strategy='reverse_chronological',
    max_articles=5
)
```

## 完整工作流程

```python
from fetcher.fever_client import FeverClient, FeverCredentials
from fetcher.rss_fetcher import RSSFetcher
from fetcher.article_manager import ArticleManager, ArticleConcatenator

# 1. 连接 Fever API（带缓存）
client = FeverClient(credentials, db_path='rss2pod.db')

# 2. 同步缓存
result = client.sync_cache(limit=1500)

# 3. 获取订阅源
feeds = client.get_feeds()

# 4. 获取文章（从缓存）并保存
manager = ArticleManager()
for feed in feeds:
    items = client.get_feed_items(feed['id'])
    for item in items:
        article = Article(...)
        manager.add_article(article)

# 5. 拼接文章
concatenator = ArticleConcatenator(max_tokens=4000)
for feed in feeds:
    articles = manager.get_articles_by_source(feed['title'])
    combined = concatenator.concatenate_articles(articles, feed['title'])
    # 处理 combined 文本...
```

## CLI 命令

使用 CLI 管理 Fever API 缓存：

```bash
# 同步缓存
rss2pod fever sync-cache

# 指定同步数量
rss2pod fever sync-cache --limit 500

# 查看缓存统计
rss2pod fever cache-stats

# 从缓存获取文章
rss2pod fever list-articles
rss2pod fever list-articles --unread  # 只看未读
rss2pod fever list-articles --all     # 看全部
```

## 依赖

```bash
pip install requests feedparser beautifulsoup4
```

## 注意事项

1. **Fever API Key**: 使用 `email:password` 的 MD5 哈希
2. **Token 估算**: 使用简化的估算方法（中文×1.5 + 英文÷4）
3. **存储**: 文章以 JSON 格式存储在 `articles/` 目录
4. **去重**: 基于标题 + 链接 + 源的 MD5 哈希
5. **缓存模式**: 读取操作优先从 SQLite 缓存获取，写入操作同时更新缓存和 API
6. **缓存同步**: 首次使用或定期运行 `sync_cache()` 更新本地缓存

## 扩展

可以扩展的功能：
- 支持更多输出格式（Markdown、PDF 等）
- 添加文章相似度检测
- 支持增量更新
- 添加 Web 界面
- 集成 LLM 进行文章摘要