# RSS2Pod LLM Module

LLM 处理与摘要模块，为 RSS2Pod 提供智能内容处理能力。

## 目录结构

```
llm/
├── __init__.py           # 模块导出
├── llm_client.py         # LLM 客户端抽象（支持 DashScope/通义千问）
├── source_summarizer.py  # 源级摘要生成
├── group_aggregator.py   # 组级汇总
├── trigger_engine.py     # 触发引擎
└── README.md             # 本文档
```

## 功能模块

### 1. LLM Client (`llm_client.py`)

提供 LLM 客户端抽象，支持多种后端：

- **DashScopeClient**: 通义千问（DashScope API）
- **MockLLMClient**: 用于测试的模拟客户端

```python
from llm import create_llm_client

# 创建 DashScope 客户端
client = create_llm_client("dashscope")

# 创建模拟客户端（测试用）
mock_client = create_llm_client("mock")

# 生成文本
response = client.generate("请总结这篇文章...")

# 生成结构化 JSON
result = client.generate_json("分析这些文章", schema={"type": "object"})
```

**环境变量**: 使用 DashScope 需要设置 `DASHSCOPE_API_KEY`

### 2. Source Summarizer (`source_summarizer.py`)

为同一 RSS 源的文章生成综合摘要：

```python
from llm import SourceSummarizer, Article, create_llm_client

# 创建摘要器
llm_client = create_llm_client("dashscope")
summarizer = SourceSummarizer(llm_client, source_name="Tech News")

# 添加文章
summarizer.add_article(Article(
    title="AI 新突破",
    content="人工智能领域今日宣布...",
    link="https://example.com/article1"
))

# 生成摘要
summary = summarizer.generate_summary()
print(summary["summary"])
print(summary["key_topics"])
```

**返回格式**:
```json
{
    "source_name": "Tech News",
    "article_count": 5,
    "summary": "综合摘要内容...",
    "key_topics": ["AI", "机器学习"],
    "highlights": ["重要亮点"],
    "generated_at": "2026-03-02T10:00:00"
}
```

### 3. Group Aggregator (`group_aggregator.py`)

合并多个源的摘要，生成群组级汇总：

```python
from llm import GroupAggregator, SourceSummary, create_llm_client

# 创建聚合器
aggregator = GroupAggregator(create_llm_client("dashscope"), "Tech & Science")

# 添加源摘要
aggregator.add_source_summary(SourceSummary(
    source_name="Tech News",
    summary="AI 技术突破...",
    article_count=5,
    key_topics=["AI", "科技"],
    highlights=["新模型发布"],
    generated_at="2026-03-02T10:00:00"
))

# 生成聚合结果
result = aggregator.aggregate()
print(result["executive_summary"])
print(result["cross_source_themes"])
```

**返回格式**:
```json
{
    "group_name": "Tech & Science",
    "source_count": 2,
    "total_articles": 8,
    "executive_summary": "执行摘要...",
    "full_summary": "完整摘要...",
    "cross_source_themes": ["AI", "创新"],
    "top_highlights": ["最重要亮点"],
    "sources_breakdown": [...],
    "generated_at": "2026-03-02T10:00:00"
}
```

### 4. Trigger Engine (`trigger_engine.py`)

触发引擎，支持三种触发方式：

#### 时间触发 (Cron)
```python
from llm import TriggerEngine, create_cron_trigger

engine = TriggerEngine()

# 每天早上 9 点触发
engine.add_trigger(create_cron_trigger(
    name="Daily Morning",
    cron_expression="0 9 * * *",
    cooldown_minutes=60
))
```

#### 数量触发 (Count)
```python
from llm import create_count_trigger

# 当文章数量达到 5 篇时触发
engine.add_trigger(create_count_trigger(
    name="Article Batch",
    threshold=5,
    cooldown_minutes=120
))
```

#### LLM 判断触发 (LLM Judgment)
```python
from llm import create_llm_trigger

# 由 LLM 判断内容重要性
engine.add_trigger(create_llm_trigger(
    name="Important News",
    importance_threshold=0.7,
    cooldown_minutes=180
))
```

#### 评估触发
```python
# 评估是否应该触发
articles = [...]  # 文章列表
results = engine.evaluate(articles)

# 快速检查
should_trigger = engine.should_trigger(articles)

# 获取统计
stats = engine.get_trigger_stats()
```

## 完整示例

```python
from llm import (
    create_llm_client,
    SourceSummarizer, Article,
    GroupAggregator, SourceSummary,
    TriggerEngine, create_count_trigger
)

# 1. 初始化 LLM 客户端
llm_client = create_llm_client("dashscope")

# 2. 为每个源生成摘要
sources = {
    "Tech News": [
        {"title": "AI 突破", "content": "...", "link": "..."},
        {"title": "机器学习", "content": "...", "link": "..."}
    ],
    "Science Daily": [
        {"title": "量子计算", "content": "...", "link": "..."}
    ]
}

source_summaries = []
for source_name, articles in sources.items():
    summarizer = SourceSummarizer(llm_client, source_name)
    for article_data in articles:
        summarizer.add_article(Article(
            title=article_data["title"],
            content=article_data["content"],
            link=article_data["link"]
        ))
    summary = summarizer.generate_summary()
    source_summaries.append(SourceSummary.from_dict(summary))

# 3. 聚合所有源
aggregator = GroupAggregator(llm_client, "Daily Digest")
for summary in source_summaries:
    aggregator.add_source_summary(summary)

group_result = aggregator.aggregate()

# 4. 检查触发条件
engine = TriggerEngine(llm_client)
engine.add_trigger(create_count_trigger("Batch", threshold=3))

all_articles = [a for articles in sources.values() for a in articles]
if engine.should_trigger(all_articles):
    print("触发推送！")
    print(group_result["executive_summary"])
```

## 依赖

- Python 3.8+
- DashScope SDK (可选，用于生产环境): `pip install dashscope`

## 配置

使用 DashScope 需要设置环境变量：

```bash
export DASHSCOPE_API_KEY="your-api-key"
```

## 测试

运行各模块的内置测试：

```bash
cd rss2pod/llm
python3 llm_client.py
python3 source_summarizer.py
python3 group_aggregator.py
python3 trigger_engine.py
```

## 注意事项

1. **API 密钥安全**: 不要将 API 密钥提交到版本控制
2. **错误处理**: 生产环境应添加重试和降级逻辑
3. **速率限制**: 注意 LLM API 的调用频率限制
4. **缓存**: 考虑对摘要结果进行缓存以降低成本
