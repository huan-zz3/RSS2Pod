# RSS 采集模块创建记录

**创建时间**: 2026-03-02  
**任务**: 创建 RSS 采集模块

## 完成内容

### 1. 目录结构 ✅

创建了 `rss2pod/fetcher/` 目录，包含以下文件：

```
rss2pod/fetcher/
├── __init__.py            # 包初始化文件
├── fever_client.py        # Fever API 客户端
├── rss_fetcher.py         # RSS 内容获取与文本提取
├── article_manager.py     # 文章存储与管理
├── example_usage.py       # 完整使用示例
├── requirements.txt       # Python 依赖
└── README.md              # 详细文档
```

### 2. fever_client.py - Fever API 客户端 ✅

**功能**:
- `FeverCredentials` - 认证信息数据类
- `FeverClient` - Fever API 客户端类
  - `generate_api_key()` - 生成 API Key（MD5: email:password）
  - `test_auth()` - 测试认证
  - `get_feeds()` - 获取所有订阅源
  - `get_groups()` - 获取订阅源分组
  - `get_items()` - 获取文章列表（支持 since_id, max_id, limit）
  - `get_feed_items()` - 获取指定源的文章
  - `mark_as_read()` - 标记文章为已读
  - `mark_feed_as_read()` - 标记整个源为已读
  - `save_item()` - 收藏文章
  - `get_unread_count()` - 获取未读数量

**参考**: Fever API 标准规范 (https://feedafever.com/api)

### 3. rss_fetcher.py - RSS 内容获取 ✅

**功能**:
- `RSSArticle` - 文章数据类（标题、链接、时间、内容、纯文本等）
- `RSSFetcher` - RSS 获取器
  - `fetch_feed()` - 获取 RSS 源的所有文章
  - `extract_text()` - HTML 转纯文本（使用 BeautifulSoup）
  - `fetch_article_content()` - 获取文章完整页面内容
- `FeedManager` - 源管理器
  - `add_feed()` / `remove_feed()` - 管理订阅源
  - `fetch_all()` - 批量获取所有源
  - `fetch_from_source()` - 从指定源获取

**特性**:
- 支持 RSS 和 Atom 格式
- 自动提取作者、发布时间等元数据
- 智能 HTML 清理（移除 script、style 等标签）
- 自定义 User-Agent
- 超时控制

### 4. article_manager.py - 文章存储与管理 ✅

**功能**:
- `ArticleStatus` - 文章状态枚举（pending, fetched, processing, processed, failed, skipped）
- `Article` - 文章数据类
  - 唯一 ID（基于标题 + 链接 + 源的 MD5）
  - 完整的元数据字段
  - `estimate_tokens()` - Token 数量估算
  - `mark_processed()` / `mark_failed()` - 状态管理
- `ArticleManager` - 文章管理器
  - JSON 文件存储
  - 按源索引
  - 按状态查询
  - 统计信息
  - 清理旧文章
- `ArticleConcatenator` - 文章拼接器
  - `concatenate_articles()` - 拼接多篇文章
  - `concatenate_with_strategy()` - 使用策略拼接
    - chronological（时间正序）
    - reverse_chronological（时间倒序）
    - by_length（按长度）

**拼接策略特性**:
- 控制 token 上限（默认 4000）
- 自动估算每篇文章的 token 数
- 达到上限时自动停止
- 可选包含元数据（标题、时间、作者、链接）
- 文章分隔符

### 5. 配套文件 ✅

- `__init__.py` - 包初始化，导出所有公共类
- `example_usage.py` - 完整使用示例
  - Fever API 客户端示例
  - RSS 获取器示例
  - 源管理器示例
  - 文章管理器示例
  - 文章拼接示例
  - 完整工作流程示例
- `requirements.txt` - Python 依赖
  - requests>=2.28.0
  - feedparser>=6.0.0
  - beautifulsoup4>=4.11.0
- `README.md` - 详细文档（fetcher 模块和 rss2pod 根目录）

## 设计特点

1. **模块化设计** - 三个核心模块职责清晰，可独立使用
2. **数据持久化** - 文章以 JSON 格式存储，支持增量更新
3. **Token 控制** - 智能估算和控制 token 数量，适合 LLM 处理
4. **状态管理** - 完整的文章处理状态跟踪
5. **去重机制** - 基于内容哈希的自动去重
6. **灵活拼接** - 多种策略支持，可配置 token 上限

## 使用示例

```python
from fetcher import (
    FeverClient, FeverCredentials,
    RSSFetcher, FeedManager,
    ArticleManager, Article, ArticleConcatenator
)

# 1. 连接 Fever API
credentials = FeverCredentials(
    api_url='https://your-server.com/fever',
    api_key='your_api_key'
)
client = FeverClient(credentials)

# 2. 获取订阅源
feeds = client.get_feeds()

# 3. 获取并管理文章
manager = ArticleManager(storage_dir="articles")
for feed in feeds:
    items = client.get_feed_items(feed['id'], limit=10)
    for item in items:
        article = Article(
            id=Article.generate_id(item['title'], item['url'], feed['title']),
            title=item['title'],
            source=feed['title'],
            source_url=feed['url'],
            link=item['url'],
            published=datetime.now().isoformat(),
            content=item.get('content', ''),
            text_content=item.get('content', '')
        )
        article.estimate_tokens()
        manager.add_article(article)

# 4. 拼接文章
concatenator = ArticleConcatenator(max_tokens=4000)
for feed in feeds[:5]:
    articles = manager.get_articles_by_source(feed['title'], limit=5)
    combined = concatenator.concatenate_articles(articles, feed['title'])
    # 处理 combined 文本...
```

## 后续扩展建议

1. 支持更多输出格式（Markdown、PDF、EPUB）
2. 添加文章相似度检测（避免重复内容）
3. 支持增量更新（只获取新文章）
4. 添加 Web 界面进行管理
5. 集成 LLM 进行文章摘要和分类
6. 支持定时任务自动采集
7. 添加全文搜索功能

## 文件统计

- 核心模块：3 个 Python 文件
- 总代码量：约 30KB
- 文档：2 个 README 文件
- 示例：1 个完整示例文件
- 依赖：3 个 Python 包

---

**任务完成状态**: ✅ 全部完成
