# python-feedgen API 架构文档

## 概述

python-feedgen 是一个用于生成 ATOM 和 RSS 格式 Web Feed 的 Python 库，支持扩展机制（包括播客扩展）。采用双重许可：FreeBSD 和 LGPLv3+。

### 核心功能

- **ATOM 1.0 支持** - 符合 RFC 4287 标准
- **RSS 2.0 支持** - 兼容主流 RSS 阅读器
- **扩展系统** - 可加载自定义扩展
- **内置扩展** - Podcast、Dublin Core、Media RSS、GeoRSS 等

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      python-feedgen 架构                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐         ┌─────────────────┐                │
│  │  FeedGenerator  │ ──────→ │   FeedEntry[]   │                │
│  │   (Feed 级)     │  1:N    │   (Entry 级)    │                │
│  └────────┬────────┘         └─────────────────┘                │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    扩展系统                              │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │ Podcast  │ │  DC      │ │  Media   │ │  Geo     │   │    │
│  │  │ (iTunes) │ │(Dublin)  │ │   RSS    │ │   RSS    │   │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   XML 生成引擎                           │    │
│  │         (lxml - ATOM / RSS 输出)                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 项目结构

```
thirdparty/python-feedgen/
├── feedgen/
│   ├── __init__.py           # 模块入口，包含使用文档
│   ├── __main__.py           # 命令行测试入口
│   ├── feed.py               # FeedGenerator 主类
│   ├── entry.py              # FeedEntry 类
│   ├── util.py               # 工具函数
│   ├── compat.py             # Python 2/3 兼容性处理
│   ├── version.py            # 版本信息
│   │
│   └── ext/                  # 扩展模块目录
│       ├── __init__.py
│       ├── base.py           # 扩展基类 (BaseExtension)
│       ├── podcast.py        # iTunes Podcast 扩展
│       ├── podcast_entry.py  # Podcast Entry 扩展
│       ├── dc.py             # Dublin Core 元素扩展
│       ├── media.py          # Media RSS 扩展
│       ├── geo.py            # GeoRSS 扩展
│       ├── geo_entry.py      # GeoRSS Entry 扩展
│       ├── syndication.py    # Syndication 扩展
│       └── torrent.py        # Torrent RSS 扩展
│
├── tests/                    # 测试套件
│   ├── __init__.py
│   ├── test_feed.py
│   ├── test_entry.py
│   ├── test_main.py
│   └── test_extensions/
│
└── doc/                      # Sphinx 文档
    ├── api.rst
    ├── api.feed.rst
    ├── api.entry.rst
    └── ext/
```

---

## 核心类

### FeedGenerator

Feed 生成器的核心类，用于创建和管理 Feed。

```python
from feedgen.feed import FeedGenerator

fg = FeedGenerator()
fg.id('http://example.com/feed')
fg.title('My Feed')
fg.link(href='http://example.com', rel='alternate')
fg.updated('2024-01-01T00:00:00Z')

# 添加条目
fe = fg.add_entry()
fe.id('http://example.com/item/1')
fe.title('First Item')

# 生成输出
atom_xml = fg.atom_str(pretty=True)
rss_xml = fg.rss_str(pretty=True)
```

### FeedEntry

表示单个 Feed 条目（ATOM entry / RSS item）。

```python
from feedgen.entry import FeedEntry

fe = FeedEntry()
fe.id('http://example.com/item/1')
fe.title('First Item')
fe.link(href='http://example.com/item/1')
fe.updated('2024-01-01T00:00:00Z')
```

---

## REST API 端点

> 注意：python-feedgen 是一个 Python 库，不提供内置的 REST API。以下展示的是 Python API。

---

## Python API 参考

### FeedGenerator 方法

#### 初始化

```python
def __init__(self)
```

创建新的 FeedGenerator 实例。

---

#### 基础 Feed 属性

##### `id(id=None)`
Get/Set ATOM Feed ID（必需）。

```python
fg.id('http://example.com/feed')
```

##### `title(title=None)`
Get/Set Feed 标题（必需）。

```python
fg.title('My Feed')
```

##### `updated(updated=None)`
Get/Set Feed 更新时间（必需）。

```python
from datetime import datetime
fg.updated(datetime.now())
```

##### `lastBuildDate(lastBuildDate=None)`
Get/Set RSS lastBuildDate（与 `updated()` 相同）。

---

#### 作者和贡献者

##### `author(author=None, replace=False, **kwargs)`
Get/Set 作者信息。

```python
# 单个作者
fg.author({'name': 'John Doe', 'email': 'john@example.com'})

# 多个作者
fg.author([
    {'name': 'John Doe', 'email': 'john@example.com'},
    {'name': 'Jane Smith', 'email': 'jane@example.com'}
])

# 关键字参数
fg.author(name='John Doe', email='john@example.com')
```

##### `contributor(contributor=None, replace=False, **kwargs)`
Get/Set 贡献者信息（ATOM only）。

```python
fg.contributor({'name': 'Jane Smith', 'email': 'jane@example.com'})
```

---

#### 链接

##### `link(link=None, replace=False, **kwargs)`
Get/Set Feed 链接。

```python
# 自引用链接
fg.link(href='http://example.com/feed.atom', rel='self')

# 备用链接
fg.link(href='http://example.com', rel='alternate')

# 多个链接
fg.link([
    {'href': 'http://example.com', 'rel': 'alternate'},
    {'href': 'http://example.com/feed.atom', 'rel': 'self'}
])
```

**支持的 rel 值:**
- `alternate` - 备用表示
- `enclosure` - 附件资源
- `related` - 相关文档
- `self` - Feed 本身
- `via` - 信息来源

---

#### 分类

##### `category(category=None, replace=False, **kwargs)`
Get/Set Feed 分类。

```python
fg.category({'term': 'technology', 'scheme': 'http://example.com/categories'})
fg.category(term='podcasting', label='Podcasting')
```

---

#### 其他 Feed 属性

##### `subtitle(subtitle=None)`
Get/Set Feed 副标题（ATOM），也会设置 RSS description。

```python
fg.subtitle('This is a cool feed!')
```

##### `description(description=None)`
Get/Set RSS description（与 `subtitle()` 相同）。

```python
fg.description('A description of my feed')
```

##### `logo(logo=None)`
Get/Set Feed Logo。

```python
fg.logo('http://example.com/logo.png')
```

##### `icon(icon=None)`
Get/Set Feed Icon（ATOM only）。

```python
fg.icon('http://example.com/icon.ico')
```

##### `rights(rights=None)`
Get/Set 版权信息。

```python
fg.rights('Copyright 2024 Example Inc.')
```

##### `copyright(copyright=None)`
Get/Set RSS copyright（与 `rights()` 相同）。

```python
fg.copyright('Copyright 2024 Example Inc.')
```

##### `generator(generator=None, version=None, uri=None)`
Get/Set 生成器信息。

```python
fg.generator('My Generator', version='1.0', uri='http://example.com')
```

##### `language(language=None)`
Get/Set Feed 语言（RSS only）。

```python
fg.language('en-us')
```

##### `image(url=None, title=None, link=None, width=None, height=None, description=None)`
Get/Set RSS 图像。

```python
fg.image(
    url='http://example.com/image.png',
    title='My Feed Image',
    link='http://example.com'
)
```

---

#### RSS 专用属性

##### `cloud(domain, port, path, registerProcedure, protocol)`
Set RSS cloud。

```python
fg.cloud(
    domain='rpc.example.com',
    port=80,
    path='/rpc',
    registerProcedure='notify',
    protocol='http-post'
)
```

##### `docs(docs=None)`
Get/Set RSS 文档 URL。

```python
fg.docs('http://www.rssboard.org/rss-specification')
```

##### `managingEditor(managingEditor=None)`
Get/Set RSS 编辑邮箱。

```python
fg.managingEditor('editor@example.com (John Doe)')
```

##### `webMaster(webMaster=None)`
Get/Set RSS 技术邮箱。

```python
fg.webMaster('webmaster@example.com')
```

##### `pubDate(pubDate=None)`
Get/Set RSS 发布日期。

```python
fg.pubDate(datetime.now())
```

##### `rating(rating=None)`
Get/Set PICS 评级（RSS only）。

##### `skipHours(hours=None, replace=False)`
Get/Set 跳过的小时数（0-23）。

```python
fg.skipHours([2, 3, 4, 5])
```

##### `skipDays(days=None, replace=False)`
Get/Set 跳过的天数。

```python
fg.skipDays(['Sunday'])
```

##### `textInput(title, description, name, link)`
Get/Set textInput 元素。

```python
fg.textInput(
    title='Search',
    description='Search my feed',
    name='q',
    link='http://example.com/search'
)
```

##### `ttl(ttl=None)`
Get/Set TTL（分钟）。

```python
fg.ttl(60)
```

---

#### 条目管理

##### `add_entry(feedEntry=None, order='prepend')`
添加新条目到 Feed。

```python
# 创建新条目
fe = fg.add_entry()
fe.id('http://example.com/item/1')
fe.title('First Item')

# 添加现有条目
entry = FeedEntry()
fg.add_entry(entry)

# 追加到末尾
fg.add_entry(entry, order='append')
```

##### `add_item(item=None)`
`add_entry()` 的别名。

##### `entry(entry=None, replace=False)`
Get/Set Feed 条目列表。

##### `item(item=None, replace=False)`
`entry()` 的别名。

##### `remove_entry(entry)`
移除条目（支持索引或对象）。

```python
fg.remove_entry(0)  # 移除第一个
fg.remove_entry(entry)  # 移除指定对象
```

##### `remove_item(item)`
`remove_entry()` 的别名。

---

#### 生成输出

##### `atom_str(pretty=False, extensions=True, encoding='UTF-8', xml_declaration=True)`
生成 ATOM 字符串。

```python
atom_xml = fg.atom_str(pretty=True)
```

##### `atom_file(filename, extensions=True, pretty=False, encoding='UTF-8', xml_declaration=True)`
写入 ATOM 文件。

```python
fg.atom_file('feed.atom')
```

##### `rss_str(pretty=False, extensions=True, encoding='UTF-8', xml_declaration=True)`
生成 RSS 字符串。

```python
rss_xml = fg.rss_str(pretty=True)
```

##### `rss_file(filename, extensions=True, pretty=False, encoding='UTF-8', xml_declaration=True)`
写入 RSS 文件。

```python
fg.rss_file('feed.rss')
```

---

#### 扩展管理

##### `load_extension(name, atom=True, rss=True)`
加载内置扩展。

```python
# 加载 Podcast 扩展
fg.load_extension('podcast')

# 加载 Dublin Core 扩展
fg.load_extension('dc')

# 仅用于 RSS
fg.load_extension('media', rss=True, atom=False)
```

**内置扩展列表:**
- `podcast` - iTunes Podcast
- `dc` - Dublin Core
- `media` - Media RSS
- `geo` - GeoRSS
- `syndication` - Syndication
- `torrent` - Torrent RSS

##### `register_extension(namespace, extension_class_feed, extension_class_entry, atom=True, rss=True)`
注册自定义扩展。

```python
from my_extension import MyExtension

fg.register_extension(
    namespace='myext',
    extension_class_feed=MyExtension,
    extension_class_entry=None
)
```

---

### FeedEntry 方法

#### 初始化

```python
def __init__(self)
```

创建新的 FeedEntry 实例。

---

#### 基础条目属性

##### `id(id=None)`
Get/Set ATOM Entry ID（必需）。

```python
fe.id('http://example.com/item/1')
```

##### `title(title=None)`
Get/Set 条目标题（必需）。

```python
fe.title('My First Post')
```

##### `updated(updated=None)`
Get/Set 条目更新时间（必需）。

```python
fe.updated(datetime.now())
```

##### `guid(guid=None, permalink=False)`
Get/Set RSS GUID。

```python
fe.guid('http://example.com/item/1', permalink=True)
```

---

#### 作者和贡献者

##### `author(author=None, replace=False, **kwargs)`
Get/Set 条目作者。

```python
fe.author({'name': 'John Doe', 'email': 'john@example.com'})
```

##### `contributor(contributor=None, replace=False, **kwargs)`
Get/Set 条目贡献者（ATOM only）。

```python
fe.contributor({'name': 'Jane Smith'})
```

---

#### 链接和附件

##### `link(link=None, replace=False, **kwargs)`
Get/Set 条目链接。

```python
fe.link(href='http://example.com/post/1', rel='alternate')
```

##### `enclosure(url=None, length=None, type=None)`
Get/Set RSS enclosure（附件）。

```python
fe.enclosure(
    url='http://example.com/audio.mp3',
    length=12345678,
    type='audio/mpeg'
)
```

---

#### 内容

##### `content(content=None, src=None, type=None)`
Get/Set 条目内容。

```python
# 内联内容
fe.content('<p>Hello World!</p>', type='html')

# 链接内容
fe.content(src='http://example.com/post/1/full')

# CDATA 内容
fe.content('<![CDATA[Raw content]]>', type='CDATA')
```

##### `summary(summary=None, type=None)`
Get/Set 条目摘要（ATOM only）。

```python
fe.summary('A brief summary of the post.')
```

##### `description(description=None, isSummary=False)`
Get/Set RSS description。

```python
fe.description('Full description here')
```

---

#### 其他条目属性

##### `category(category=None, replace=False, **kwargs)`
Get/Set 条目分类。

```python
fe.category({'term': 'python', 'label': 'Python'})
```

##### `published(published=None)`
Get/Set 条目发布日期。

```python
fe.published(datetime.now())
```

##### `pubDate(pubDate=None)`
`published()` 的别名。

##### `rights(rights=None)`
Get/Set 条目版权信息。

```python
fe.rights('Copyright 2024')
```

##### `comments(comments=None)`
Get/Set 评论 URL（RSS only）。

```python
fe.comments('http://example.com/post/1#comments')
```

##### `source(url=None, title=None)`
Get/Set 来源信息。

```python
fe.source('http://example.com', 'Example Blog')
```

---

#### 扩展管理

##### `load_extension(name, atom=True, rss=True)`
加载条目扩展。

```python
fe.load_extension('podcast')
```

##### `register_extension(namespace, extension_class_entry, atom=True, rss=True)`
注册条目扩展。

---

### 扩展 API

#### BaseExtension

所有扩展的基类。

```python
class BaseExtension:
    def extend_ns(self):
        '''返回命名空间映射'''
        return {}
    
    def extend_rss(self, feed):
        '''扩展 RSS feed'''
        return feed
    
    def extend_atom(self, feed):
        '''扩展 ATOM feed'''
        return feed
```

---

#### PodcastExtension (iTunes)

用于创建 iTunes Podcast。

```python
fg.load_extension('podcast')

# Feed 级设置
fg.podcast.itunes_author('John Doe')
fg.podcast.itunes_block(True)  # 隐藏播客
fg.podcast.itunes_category('Technology', 'Podcasting')
fg.podcast.itunes_image('http://example.com/cover.jpg')
fg.podcast.itunes_explicit('no')
fg.podcast.itunes_complete('yes')
fg.podcast.itunes_new_feed_url('http://new.example.com/feed')
fg.podcast.itunes_owner('John Doe', 'john@example.com')
fg.podcast.itunes_subtitle('A tech podcast')
fg.podcast.itunes_summary('Summary of the podcast')
fg.podcast.itunes_type('episodic')  # or 'serial'

# Entry 级设置
fe = fg.add_entry()
fe.load_extension('podcast')
fe.podcast.itunes_author('John Doe')
fe.podcast.itunes_block(False)
fe.podcast.itunes_image('http://example.com/episode.jpg')
fe.podcast.itunes_explicit('no')
fe.podcast.itunes_subtitle('Episode 1')
fe.podcast.itunes_summary('Episode summary')
fe.podcast.itunes_duration('00:30:00')
fe.podcast.itunes_episode(1)
fe.podcast.itunes_season(1)
fe.podcast.itunes_episodeType('full')  # 'full', 'trailer', 'bonus'
```

---

#### DcExtension (Dublin Core)

```python
fg.load_extension('dc')

fg.dc_contributor(['Jane Smith'])
fg.dc_coverage('United States')
fg.dc_creator(['John Doe'])
fg.dc_date(['2024-01-01'])
fg.dc_description(['Description'])
fg.dc_format(['text/html'])
fg.dc_identifier(['http://example.com'])
fg.dc_language(['en'])
fg.dc_publisher(['Example Inc.'])
fg.dc_relation(['http://related.com'])
fg.dc_rights(['Copyright 2024'])
fg.dc_source(['http://source.com'])
fg.dc_subject(['Technology', 'Podcasting'])
fg.dc_title(['My Feed'])
fg.dc_type(['Text'])
```

---

#### MediaExtension (Media RSS)

```python
fg.load_extension('media')

fe = fg.add_entry()
fe.media.content(
    url='http://example.com/video.mp4',
    fileSize=12345678,
    type='video/mp4',
    medium='video',
    duration=300,
    width=1920,
    height=1080
)

fe.media.thumbnail(
    url='http://example.com/thumb.jpg',
    width=320,
    height=180
)
```

---

#### GeoExtension (GeoRSS)

```python
fg.load_extension('geo')

fe = fg.add_entry()
fe.georss.point('45.256 -71.92')
fe.georss.line('45.256 -71.92 46.256 -72.92')
fe.georss.polygon('45.256 -71.92 46.256 -72.92 45.256 -71.92')
fe.georss.box('45.256 -71.92 46.256 -72.92')
fe.georss.featureName('My Location')
```

---

## 数据流图

### Feed 生成流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Feed 生成流程                                 │
└─────────────────────────────────────────────────────────────────┘

1. 初始化 FeedGenerator
   ┌─────────────────────────────────────────────────────────────┐
   │  fg = FeedGenerator()                                       │
   │  - 初始化 ATOM 字段（id, title, updated 等）                  │
   │  - 初始化 RSS 字段（title, link, description 等）             │
   │  - 初始化扩展字典                                            │
   └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
2. 设置 Feed 属性
   ┌─────────────────────────────────────────────────────────────┐
   │  fg.id('...')                                               │
   │  fg.title('...')                                            │
   │  fg.link(...)                                               │
   │  ...                                                        │
   └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
3. 加载扩展（可选）
   ┌─────────────────────────────────────────────────────────────┐
   │  fg.load_extension('podcast')                               │
   │  - 导入扩展模块                                              │
   │  - 创建扩展实例                                              │
   │  - 注册到扩展字典                                            │
   └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
4. 添加条目
   ┌─────────────────────────────────────────────────────────────┐
   │  fe = fg.add_entry()                                        │
   │  fe.id('...')                                               │
   │  fe.title('...')                                            │
   │  ...                                                        │
   │  - 创建 FeedEntry 实例                                       │
   │  - 自动继承 Feed 的扩展                                      │
   └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
5. 生成 XML
   ┌─────────────────────────────────────────────────────────────┐
   │  fg.atom_str() / fg.rss_str()                               │
   │  - _create_atom() / _create_rss()                           │
   │  - 构建 XML 树 (lxml)                                         │
   │  - 调用扩展的 extend_*() 方法                                │
   │  - 序列化 XML                                                │
   └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
6. 输出
   ┌─────────────────────────────────────────────────────────────┐
   │  - 返回 XML 字符串                                            │
   │  - 或写入文件                                                │
   └─────────────────────────────────────────────────────────────┘
```

---

## 使用示例

### 基础 ATOM Feed

```python
from feedgen.feed import FeedGenerator
from datetime import datetime

fg = FeedGenerator()
fg.id('http://example.com/feed')
fg.title('My ATOM Feed')
fg.author({'name': 'John Doe', 'email': 'john@example.com'})
fg.link(href='http://example.com', rel='alternate')
fg.link(href='http://example.com/feed.atom', rel='self')
fg.logo('http://example.com/logo.png')
fg.subtitle('A sample ATOM feed')
fg.updated(datetime.now())
fg.language('en')

# 添加条目
fe = fg.add_entry()
fe.id('http://example.com/post/1')
fe.title('First Post')
fe.link(href='http://example.com/post/1')
fe.updated(datetime.now())
fe.published(datetime.now())
fe.summary('Summary of the first post')
fe.content('<p>Hello World!</p>', type='html')

# 生成
atom_xml = fg.atom_str(pretty=True)
fg.atom_file('feed.atom')
```

---

### 基础 RSS Feed

```python
from feedgen.feed import FeedGenerator
from datetime import datetime

fg = FeedGenerator()
fg.title('My RSS Feed')
fg.description('A sample RSS feed')
fg.link(href='http://example.com')
fg.language('en-us')
fg.copyright('Copyright 2024')
fg.managingEditor('editor@example.com')
fg.webMaster('webmaster@example.com')
fg.pubDate(datetime.now())
fg.lastBuildDate(datetime.now())
fg.docs('http://www.rssboard.org/rss-specification')
fg.ttl(60)

# 添加条目
fe = fg.add_entry()
fe.title('First Post')
fe.link(href='http://example.com/post/1')
fe.guid('http://example.com/post/1', permalink=True)
fe.description('Description of the first post')
fe.content('<p>Hello World!</p>', type='html')
fe.pubDate(datetime.now())
fe.author('John Doe')

# 生成
rss_xml = fg.rss_str(pretty=True)
fg.rss_file('feed.rss')
```

---

### Podcast Feed

```python
from feedgen.feed import FeedGenerator
from datetime import datetime

fg = FeedGenerator()
fg.id('http://example.com/podcast')
fg.title('My Podcast')
fg.description('A technology podcast')
fg.link(href='http://example.com')
fg.updated(datetime.now())
fg.language('en-us')
fg.copyright('Copyright 2024')

# 加载 Podcast 扩展
fg.load_extension('podcast')

# 设置 Podcast 元数据
fg.podcast.itunes_author('John Doe')
fg.podcast.itunes_owner('John Doe', 'john@example.com')
fg.podcast.itunes_image('http://example.com/cover.jpg')
fg.podcast.itunes_explicit('no')
fg.podcast.itunes_category('Technology', 'Podcasting')
fg.podcast.itunes_summary('A podcast about technology')
fg.podcast.itunes_type('episodic')

# 添加剧集
fe = fg.add_entry()
fe.id('http://example.com/episode/1')
fe.title('Episode 1: Introduction')
fe.link(href='http://example.com/episode/1')
fe.updated(datetime.now())
fe.pubDate(datetime.now())
fe.description('The first episode')
fe.enclosure(
    url='http://example.com/episode1.mp3',
    length=12345678,
    type='audio/mpeg'
)

# Podcast 扩展设置
fe.podcast.itunes_author('John Doe')
fe.podcast.itunes_image('http://example.com/ep1.jpg')
fe.podcast.itunes_explicit('no')
fe.podcast.itunes_subtitle('Introduction to the show')
fe.podcast.itunes_summary('Full episode summary')
fe.podcast.itunes_duration('00:30:00')
fe.podcast.itunes_season(1)
fe.podcast.itunes_episode(1)
fe.podcast.itunes_episodeType('full')

# 生成 RSS
rss_xml = fg.rss_str(pretty=True)
fg.rss_file('podcast.rss')
```

---

### Dublin Core Feed

```python
from feedgen.feed import FeedGenerator

fg = FeedGenerator()
fg.id('http://example.com/dc-feed')
fg.title('Dublin Core Feed')
fg.link(href='http://example.com')

# 加载 DC 扩展
fg.load_extension('dc')

# 设置 DC 元素
fg.dc_creator(['John Doe'])
fg.dc_contributor(['Jane Smith'])
fg.dc_title(['My DC Feed'])
fg.dc_description(['A feed with Dublin Core metadata'])
fg.dc_subject(['Technology', 'Science'])
fg.dc_publisher(['Example Inc.'])
fg.dc_date(['2024-01-01'])
fg.dc_type(['Text'])
fg.dc_format(['text/html'])
fg.dc_identifier(['http://example.com/feed'])
fg.dc_language(['en'])
fg.dc_rights(['Copyright 2024'])

# 生成
atom_xml = fg.atom_str(pretty=True)
```

---

### Media RSS Feed

```python
from feedgen.feed import FeedGenerator

fg = FeedGenerator()
fg.id('http://example.com/media')
fg.title('Media RSS Feed')
fg.link(href='http://example.com')

# 加载 Media 扩展
fg.load_extension('media')

# 添加带媒体的条目
fe = fg.add_entry()
fe.id('http://example.com/video/1')
fe.title('My Video')
fe.link(href='http://example.com/video/1')

# 设置媒体内容
fe.media.content(
    url='http://example.com/video.mp4',
    fileSize=12345678,
    type='video/mp4',
    medium='video',
    isDefault='true',
    expression='full',
    bitrate=1024,
    framerate=30,
    duration=300,
    width=1920,
    height=1080
)

# 设置缩略图
fe.media.thumbnail(
    url='http://example.com/thumb.jpg',
    width=320,
    height=180,
    time='00:01:30'
)

# 生成
atom_xml = fg.atom_str(pretty=True)
```

---

### GeoRSS Feed

```python
from feedgen.feed import FeedGenerator

fg = FeedGenerator()
fg.id('http://example.com/geo')
fg.title('GeoRSS Feed')
fg.link(href='http://example.com')

# 加载 GeoRSS 扩展
fg.load_extension('geo')

# 添加带地理位置的条目
fe = fg.add_entry()
fe.id('http://example.com/location/1')
fe.title('My Location')
fe.link(href='http://example.com/location/1')

# 设置地理位置
fe.georss.point('45.256 -71.92')
fe.georss.featureName('Mountain View')

# 生成
atom_xml = fg.atom_str(pretty=True)
```

---

### 自定义扩展

```python
from feedgen.feed import FeedGenerator
from feedgen.ext.base import BaseExtension, BaseEntryExtension
from feedgen.util import xml_elem


class MyExtension(BaseExtension):
    '''自定义 Feed 扩展'''
    
    def extend_ns(self):
        return {'my': 'http://example.com/my_ns'}
    
    def extend_rss(self, rss_feed):
        channel = rss_feed[0]
        custom = xml_elem('{http://example.com/my_ns}custom', channel)
        custom.text = 'Custom RSS data'
        return rss_feed
    
    def extend_atom(self, atom_feed):
        custom = xml_elem('{http://example.com/my_ns}custom', atom_feed)
        custom.text = 'Custom ATOM data'
        return atom_feed


class MyEntryExtension(BaseEntryExtension):
    '''自定义 Entry 扩展'''
    
    def __init__(self):
        self.__custom_data = None
    
    def extend_ns(self):
        return {'my': 'http://example.com/my_ns'}
    
    def extend_atom(self, entry):
        if self.__custom_data:
            custom = xml_elem('{http://example.com/my_ns}entry_custom', entry)
            custom.text = self.__custom_data
        return entry
    
    def extend_rss(self, item):
        if self.__custom_data:
            custom = xml_elem('{http://example.com/my_ns}entry_custom', item)
            custom.text = self.__custom_data
        return item
    
    def custom_data(self, data=None):
        if data is not None:
            self.__custom_data = data
        return self.__custom_data


# 使用自定义扩展
fg = FeedGenerator()
fg.id('http://example.com/custom')
fg.title('Custom Extension Feed')
fg.link(href='http://example.com')

# 注册扩展
fg.register_extension(
    namespace='myext',
    extension_class_feed=MyExtension,
    extension_class_entry=MyEntryExtension
)

# 设置扩展数据
fg.myext  # Feed 扩展实例

fe = fg.add_entry()
fe.id('http://example.com/item/1')
fe.title('Item with custom extension')
fe.myext.custom_data('My custom entry data')

# 生成
atom_xml = fg.atom_str(pretty=True)
```

---

## 依赖

### 运行时依赖

| 包 | 版本 | 用途 |
|-----|------|------|
| `lxml` | >=4.2.5 | XML 生成和解析 |
| `python-dateutil` | >=2.8.0 | 日期时间处理 |

### 安装

```bash
# 使用 pip
pip install feedgen

# 使用系统包管理器 (Fedora/RHEL)
dnf install python3-feedgen
```

---

## 配置

### 不需要配置文件，所有配置通过 API 方法完成。

---

## 错误处理

### 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `ValueError: Required fields not set` | 缺少必需字段 | 确保设置 id、title、updated |
| `ValueError: Invalid datetime format` | 日期格式无效 | 使用 datetime 对象或 ISO 8601 字符串 |
| `ValueError: Datetime object has no timezone info` | 缺少时区信息 | 使用带时区的 datetime |
| `ImportError: Extension already loaded` | 扩展重复加载 | 检查扩展加载逻辑 |
| `ValueError: Invalid hour` | skipHours 值无效 | 使用 0-23 之间的值 |
| `ValueError: Invalid day` | skipDays 值无效 | 使用有效的星期名称 |

### 错误响应示例

```python
try:
    fg.updated('invalid-date')
except ValueError as e:
    print(f"Error: {e}")
```

---

## 版本历史

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| 1.0.0 | 2023-12 | 移除 Python 2 支持 |
| 0.9.0 | 2021-06 | Podcast 扩展改进 |
| 0.7.0 | 2018-05 | GeoRSS 支持 |
| 0.6.0 | 2017-10 | Media RSS 支持 |
| 0.5.0 | 2016-03 | Dublin Core 支持 |

---

## 相关资源

- **GitHub**: https://github.com/lkiesow/python-feedgen
- **PyPI**: https://pypi.org/project/feedgen/
- **文档**: https://lkiesow.github.io/python-feedgen/
- **规范**:
  - [ATOM RFC 4287](https://tools.ietf.org/html/rfc4287)
  - [RSS 2.0](http://www.rssboard.org/rss-specification)
  - [iTunes Podcast Spec](https://podcasters.apple.com/support/1691-apple-podcasts-specifications)
  - [Dublin Core](http://dublincore.org/documents/dces/)
  - [Media RSS](https://www.rssboard.org/media-rss)
  - [GeoRSS](http://www.georss.org/)

---

*文档最后更新：2024 年*