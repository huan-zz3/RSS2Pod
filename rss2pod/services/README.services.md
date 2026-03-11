# RSS2Pod 服务层文档

## 概述

服务层（Services Layer）是 RSS2Pod 系统的核心业务逻辑封装层，位于数据访问层（Database/Fetcher/LLM/TTS 等）之上，为 API 层和 CLI 层提供统一的服务接口。

### 设计目标

- **业务逻辑封装**：将分散在各模块的业务规则集中管理
- **接口统一**：为 API 和 CLI 提供一致的调用方式
- **解耦**：底层模块可独立替换，不影响上层
- **错误处理**：统一的错误封装和返回格式

### 架构位置

```
┌─────────────────────────────────────────┐
│           API / CLI 层                   │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│           Services 服务层                │
│  ┌─────────────────────────────────┐    │
│  │      BaseService (基类)          │    │
│  └─────────────────────────────────┘    │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ...   │
│  │Fever│ │TTS  │ │LLM  │ │Group│       │
│  │Svc  │ │Svc  │ │Svc  │ │Svc  │       │
│  └─────┘ └─────┘ └─────┘ └─────┘       │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│      底层模块（Fetcher/LLM/TTS/DB）      │
└─────────────────────────────────────────┘
```

---

## 基础服务类

### BaseService

所有服务的基类，提供通用的配置加载和数据库连接管理。

```python
from services import BaseService

class MyService(BaseService):
    def __init__(self, config_path: str = None, db_path: str = None):
        super().__init__(config_path, db_path)
```

**主要属性**：

| 属性 | 类型 | 说明 |
|------|------|------|
| `config_path` | `str` | 配置文件路径 |
| `db_path` | `str` | 数据库文件路径 |
| `config` | `dict` | 懒加载的配置对象 |
| `db` | `DatabaseManager` | 懒加载的数据库连接 |

**主要方法**：

- `close()`: 关闭服务，释放资源

### ServiceResult

所有服务方法的统一返回格式。

```python
from services import ServiceResult

result = ServiceResult(
    success=True,
    data={'key': 'value'},
    metadata={'count': 1}
)
```

**属性说明**：

| 属性 | 类型 | 说明 |
|------|------|------|
| `success` | `bool` | 操作是否成功 |
| `data` | `any` | 返回的业务数据 |
| `error_message` | `str` | 错误信息（失败时） |
| `metadata` | `dict` | 额外元数据（如 count） |

---

## 配置服务 (ConfigService)

提供配置管理的统一接口。

### 功能

- 配置文件的加载和保存
- 嵌套配置值的获取和设置
- 使用系统编辑器交互式编辑
- 配置项重置到默认值
- 脱敏配置输出（隐藏 API Key）

### 主要方法

```python
from services import ConfigService

service = ConfigService()

# 加载配置
config = service.load_config()

# 保存配置
service.save_config(config)

# 获取嵌套值
value = service.get_nested_value(config, 'llm.model')

# 设置嵌套值
service.set_nested_value(config, 'llm.model', 'qwen-plus')

# 使用编辑器编辑
result = service.edit_config_with_editor()

# 设置配置项
result = service.set_config_value('tts.voice', 'FunAudioLLM/CosyVoice2-0.5B:claire')

# 重置到默认值
result = service.reset_config_value('llm.model')

# 获取脱敏配置
safe_config = service.get_safe_config()
```

### 默认配置值

| 配置路径 | 默认值 | 说明 |
|----------|--------|------|
| `llm.model` | `qwen3.5-plus` | LLM 模型 |
| `llm.base_url` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | API 地址 |
| `tts.provider` | `siliconflow` | TTS 提供商 |
| `tts.voice` | `FunAudioLLM/CosyVoice2-0.5B:claire` | 默认音色 |
| `tts.model` | `fnlp/MOSS-TTSD-v0.5` | TTS 模型 |
| `db_path` | `rss2pod.db` | 数据库路径 |
| `orchestrator.check_interval_seconds` | `60` | 检查间隔（秒） |
| `orchestrator.max_concurrent_groups` | `3` | 最大并发组数 |
| `logging.level` | `INFO` | 日志级别 |

### 便捷函数

```python
from services.config_service import load_config, save_config, get_nested_value, set_nested_value

config = load_config()
save_config(config)
value = get_nested_value(config, 'llm.model')
set_nested_value(config, 'llm.model', 'qwen-plus')
```

---

## 资源服务 (AssetService)

管理 Episode 生成过程中产生的中间文件。

### 功能

- 列出 Group 下所有 Episode 的资源
- 查看指定 Episode 的资源详情
- 清理中间文件（保留最终音频）

### 资源类型

| 类型 | 命名示例 | 说明 |
|------|----------|------|
| 源级摘要 | `source_summary_feed-1.txt` | 每个 RSS 源的摘要 |
| 组级摘要 | `group_summary.txt` | 合并后的组级摘要 |
| 播客脚本 | `script.json`, `script.moss` | 生成的脚本文件 |
| 分段音频 | `segment_001_host.mp3` | TTS 分段生成 |
| 最终音频 | `final.mp3` | 拼接后的完整音频 |

### 存储位置

```
data/media/{group_id}/
└── episode_{timestamp}/
    ├── source_summary_feed-1.txt
    ├── source_summary_feed-2.txt
    ├── group_summary.txt
    ├── script.json
    ├── script.moss
    ├── segment_001_host.mp3
    ├── segment_002_guest.mp3
    └── final.mp3
```

### 主要方法

```python
from services import AssetService

service = AssetService()

# 列出 Group 下所有 Episode 的资源
result = service.list_episode_assets('group-1')

# 获取指定 Episode 的资源详情
result = service.get_episode_assets('group-1', '20260309120000')

# 清理指定 Episode 的中间文件
result = service.cleanup_episode_assets('group-1', '20260309120000')

# 清理 Group 下所有 Episode 的中间文件
result = service.cleanup_episode_assets('group-1')
```

### 便捷函数

```python
from services.asset_service import list_episode_assets, get_episode_assets, cleanup_episode_assets

episodes = list_episode_assets('group-1')
assets = get_episode_assets('group-1', '20260309120000')
cleanup_episode_assets('group-1')
```

---

## Fever API 服务 (FeverService)

封装 Fever API 的相关操作。

### 功能

- Fever API 连接测试
- 订阅源列表同步
- 文章同步到本地缓存
- 文章已读/收藏标记
- 缓存文章和订阅源查询

### 主要方法

```python
from services import FeverService

service = FeverService()

# 测试连接
result = service.test_connection()

# 同步订阅源列表
result = service.sync_feeds()

# 同步文章（默认 1500 条）
result = service.sync_articles(limit=1500)

# 标记已读
result = service.mark_as_read([1, 2, 3])

# 收藏文章
result = service.mark_as_saved(123)

# 标记未读（仅本地缓存）
result = service.mark_as_unread([4, 5, 6])

# 获取缓存统计
result = service.get_cache_stats()

# 获取文章列表
result = service.get_cache_articles(limit=50, unread=True, feed_id=1)

# 获取订阅源列表
result = service.get_cache_feeds()
```

---

## LLM 服务 (LLMService)

封装大语言模型相关操作。

### 功能

- LLM 连接测试
- 对话生成
- 结构化 JSON 生成

### 主要方法

```python
from services import LLMService

service = LLMService()

# 测试连接
result = service.test_connection()

# 对话
result = service.chat('今天天气怎么样？')

# 带系统消息的对话
result = service.chat(
    message='总结这段文字',
    system_message='你是一个专业的文字编辑'
)

# 生成 JSON
result = service.generate_json(
    prompt='提取文章中的关键信息',
    schema={'title': 'str', 'summary': 'str'}
)
```

---

## TTS 服务 (TTSService)

封装文本转语音相关操作。

### 功能

- TTS 连接测试
- 可用音色列表查询
- 文本转语音合成

### 支持的模型

| 模型 | 特点 |
|------|------|
| `fnlp/MOSS-TTSD-v0.5` | 支持双人模式 |
| `FunAudioLLM/CosyVoice2-0.5B` | 高质量单人音色 |

### 主要方法

```python
from services import TTSService

service = TTSService()

# 测试连接
result = service.test_connection()

# 列出可用音色
result = service.list_voices()

# 列出指定模型的音色
result = service.list_voices('fnlp/MOSS-TTSD-v0.5')

# 合成语音
result = service.synthesize(
    text='你好，欢迎收听今天的播客',
    voice='FunAudioLLM/CosyVoice2-0.5B:claire',
    output_path='output.mp3'
)
```

### 分段 TTS 说明

SiliconFlow MOSS 模型存在 2 分 43 秒的音频时长限制。TTSService 自动处理分段：

1. 将长文本按段落分割
2. 每段分别调用 TTS API
3. 使用 `pydub` 拼接为完整音频

---

## Prompt 管理服务 (PromptService)

提供 LLM Prompt 的灵活配置管理。

### 功能

- Prompt 模板列表和详情
- 全局 Prompt 设置
- 组别级别的 Prompt 覆盖
- Prompt 模板渲染
- 导入/导出

### 内置 Prompts

| 名称 | 说明 | 主要变量 |
|------|------|----------|
| `source_summarizer` | 源级摘要生成 | `source_name`, `article_count`, `articles_text` |
| `group_aggregator` | 组级摘要聚合 | `group_name`, `source_summaries_text` |
| `script_generator` | 播客脚本生成 | `group_name`, `structure_text`, `learning_text` 等 |

### 主要方法

```python
from services import PromptService

service = PromptService()

# 列出所有 prompts
result = service.list_prompts()

# 获取 prompt 配置
result = service.get_prompt('source_summarizer')

# 获取 prompt 模板
result = service.get_prompt_template('script_generator')

# 获取 system message
result = service.get_prompt_system('script_generator')

# 设置全局 prompt
result = service.set_global_prompt('script_generator', {
    'system': '你是一个播客脚本生成专家',
    'template': '{{content}}',
    'description': '自定义脚本生成器'
})

# 设置组别覆盖
result = service.set_group_override('group-1', 'script_generator', {
    'template': '请用更活泼的方式生成脚本：{{content}}'
})

# 重置组别覆盖
result = service.reset_group_override('group-1', 'script_generator')

# 渲染模板
result = service.render_template('script_generator', {
    'group_name': '科技前沿',
    'content': '...'
}, group_id='group-1')

# 导出/导入
result = service.export_prompts('prompts.json')
result = service.import_prompts('prompts.json', merge=True)
```

---

## Group 管理服务 (GroupService)

封装 Group 的 CRUD 操作。

### 功能

- Group 列表查询
- Group 详情获取
- Group 创建/更新/删除
- Group 启用/禁用
- 期数列表查询

### 主要方法

```python
from services import GroupService

service = GroupService()

# 列出所有 Group
result = service.list_groups()

# 只列出启用的 Group
result = service.list_groups(enabled_only=True)

# 获取 Group 详情
result = service.get_group('group-1')

# 创建 Group
result = service.create_group({
    'name': '科技前沿',
    'description': '每日科技资讯',
    'rss_sources': ['feed-1', 'feed-2'],
    'summary_preference': 'balanced',
    'podcast_structure': 'dual',
    'english_learning_mode': 'off',
    'trigger_type': 'time',
    'trigger_config': {'cron': '0 8 * * *'}
})

# 更新 Group
result = service.update_group('group-1', {
    'name': '科技前沿（更新）',
    'podcast_structure': 'single'
})

# 删除 Group
result = service.delete_group('group-1')

# 启用 Group
result = service.enable_group('group-1')

# 禁用 Group
result = service.disable_group('group-1')

# 获取期数列表
result = service.get_group_episodes('group-1', limit=50)
```

---

## 调度器服务 (SchedulerService)

封装调度器和管道执行相关操作。

### 功能

- 调度器启动/停止
- 调度器状态查询
- 手动触发执行
- 生成历史查询

### 主要方法

```python
from services import SchedulerService

service = SchedulerService()

# 启动调度器（后台运行）
result = service.start()

# 停止调度器
result = service.stop()

# 获取调度器状态
result = service.get_status()

# 手动触发所有启用的 Group
result = service.run_once()

# 手动触发指定 Group
result = service.run_once('group-1')

# 触发生成（支持强制模式和导出）
result = service.trigger_generation(
    'group-1',
    force=True,
    export_articles=True
)

# 获取生成历史
result = service.get_generation_history(group_id='group-1', limit=50)
```

### 返回数据示例

`get_status()` 返回：
```json
{
  "running": true,
  "states_by_status": {
    "idle": 3,
    "running": 1
  },
  "running_pipelines": 1,
  "runs_today": 5,
  "enabled_groups_count": 4,
  "enabled_groups": [...]
}
```

---

## 统计服务 (StatsService)

提供系统统计信息查询。

### 功能

- 系统整体统计
- 数据库统计
- Fever 缓存统计
- 处理状态统计
- 组别统计
- 最近活动记录

### 主要方法

```python
from services import StatsService

service = StatsService()

# 获取系统整体统计
result = service.get_system_stats()

# 获取数据库统计
result = service.get_database_stats()

# 获取 Fever 缓存统计
result = service.get_fever_cache_stats()

# 获取处理状态统计
result = service.get_processing_stats()

# 获取指定 Group 的统计
result = service.get_group_stats('group-1')

# 获取最近活动记录
result = service.get_recent_activity(days=7)
```

---

## 使用示例

### 基础调用模式

```python
from services import GroupService

service = GroupService()
result = service.list_groups()

if result.success:
    print(f"共找到 {result.metadata['count']} 个 Group")
    for group in result.data:
        print(f"- {group['name']}")
else:
    print(f"错误: {result.error_message}")
```

### 便捷函数调用

目前仅 AssetService 和 ConfigService 提供模块级便捷函数：

```python
# 列出所有 Group 的资源
from services.asset_service import list_episode_assets
episodes = list_episode_assets('group-1')

# 加载配置
from services.config_service import load_config
config = load_config()
```

---

## 配置依赖

各服务对应的 `config.json` 配置项：

| 服务 | 依赖配置 |
|------|----------|
| ConfigService | 全部配置 |
| AssetService | `db_path` |
| FeverService | `fever.*` |
| LLMService | `llm.*` |
| TTSService | `tts.*` |
| PromptService | `llm.*`, `prompts.*` |
| GroupService | `db_path` |
| SchedulerService | `orchestrator.*`, `logging.*` |
| StatsService | `llm.*`, `tts.*`, `orchestrator.*` |

---

## 错误处理

所有服务方法返回 `ServiceResult` 对象，建议按以下模式处理：

```python
result = service.some_method()

if result.success:
    # 处理成功结果
    data = result.data
    # 可选：访问元数据
    count = result.metadata.get('count', 0)
else:
    # 处理错误
    print(f"操作失败: {result.error_message}")
```

---

## Pipeline 服务模块 (services/pipeline/)

Pipeline 服务模块提供完整的播客生成管道编排，是系统的核心执行逻辑。

### 目录结构

```
services/pipeline/
├── __init__.py              # 导出所有类
├── models.py                # 数据类定义
├── pipeline_orchestrator.py  # 管道编排器
├── group_processor.py       # Group 处理器
└── service.py              # 对外统一接口
```

### 数据类 (models.py)

| 类名 | 说明 |
|------|------|
| `FetchResult` | 文章获取结果 |
| `SummaryResult` | 源级摘要结果 |
| `GroupSummaryResult` | 组级摘要结果 |
| `ScriptResult` | 脚本生成结果 |
| `TTSResult` | TTS 合成结果 |
| `EpisodeResult` | Episode 创建结果 |
| `PipelineResult` | 管道执行结果 |
| `PipelineStage` | 管道阶段定义 |

### PipelineOrchestrator

核心管道编排器，协调各个处理阶段。

```python
from services.pipeline import PipelineOrchestrator

orchestrator = PipelineOrchestrator(config_path, db_path)

# 同步执行
result = orchestrator.run_sync(group_id, force=False, export_articles=False)

# 异步执行
result = await orchestrator.run(group_id, force=False, export_articles=False)
```

### PipelineService

对外统一接口类，封装了 PipelineOrchestrator。

```python
from services.pipeline import PipelineService

service = PipelineService(config_path, db_path)

# 同步执行单个 Group
result = service.run_sync(group_id, force=False, export_articles=False)

# 异步执行单个 Group
result = await service.run(group_id, force=False, export_articles=False)

# 执行所有启用的 Group
results = service.run_all_enabled_sync()
```

### GroupProcessor

简化的 Group 处理封装。

```python
from services.pipeline import GroupProcessor, process_group_sync

# 使用便捷函数
result = process_group_sync(group_id, db_path, force=False, export_articles=False)

# 使用类
processor = GroupProcessor(config_path, db_path)
result = processor.process(group_id, force=False)
```

### 便捷函数

Pipeline 模块还提供以下模块级便捷函数：

```python
from services.pipeline import run_pipeline, run_pipeline_sync, get_pipeline_service

# 获取单例 PipelineService 实例
service = get_pipeline_service()

# 异步执行管道
result = await run_pipeline(group_id, db_path, force=False, export_articles=False)

# 同步执行管道
result = run_pipeline_sync(group_id, db_path, force=False, export_articles=False)
```

---

## 原子服务模块 (services/basic/)

原子服务模块提供底层业务逻辑封装。

### 目录结构

```
services/basic/
├── __init__.py         # 导出所有原子服务
├── llm_service.py      # LLM 服务（扩展方法）
├── tts_service.py      # TTS 服务（扩展方法）
├── fever_service.py    # Fever API 服务
├── group_service.py    # Group 管理服务
├── prompt_service.py   # Prompt 管理服务
├── asset_service.py    # 资源管理服务
└── stats_service.py   # 统计服务
```

### LLM 扩展方法

LLMService 扩展了以下 Pipeline 所需的方法：

```python
from services.basic import LLMService

service = LLMService()

# 生成源级摘要
result = service.generate_source_summary(
    source='feed-1',
    articles=[article1, article2],
    prompt_template='...'
)

# 生成组级摘要
result = service.generate_group_summary(
    source_summaries=[summary1, summary2],
    group_name='科技前沿',
    prompt_template='...'
)

# 生成播客脚本
result = service.generate_script(
    group_summary={'executive_summary': '...', ...},
    prompt_template='...',
    podcast_structure='dual',
    english_learning_mode='off'
)
```

### TTS 扩展方法

TTSService 扩展了以下 Pipeline 所需的方法：

```python
from services.basic import TTSService

service = TTSService()

# 分段合成（异步）
result = await service.synthesize_segments(
    segments=[{'text': '第一段', 'voice': '...'}, ...],
    voice='FunAudioLLM/CosyVoice2-0.5B:claire'
)

# 分段合成（同步）
result = service.synthesize_segments_sync(
    segments=[{'text': '第一段', 'voice': '...'}, ...],
    voice='FunAudioLLM/CosyVoice2-0.5B:claire'
)
```

---

## 架构分层

```
┌────────────────────────────────────────────────────────────┐
│                      CLI / API 层                          │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                   Services 服务层                           │
│  ┌─────────────────────┐  ┌─────────────────────────────┐ │
│  │   Basic 原子服务     │  │      Pipeline 服务           │ │
│  │  LLMService        │  │  PipelineService            │ │
│  │  TTSService        │  │  PipelineOrchestrator      │ │
│  │  FeverService      │  │  GroupProcessor            │ │
│  │  GroupService      │  │                             │ │
│  │  AssetService      │  │                             │ │
│  │  StatsService      │  │                             │ │
│  └─────────────────────┘  └─────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                  Orchestrator 调度层                       │
│  Scheduler │ StateManager │ logging_config                │
└────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────┐
│                    底层模块                                 │
│  Database │ Fetcher │ LLM Client │ TTS Provider           │
└────────────────────────────────────────────────────────────┘
```

---

## 相关文档

- [RSS2Pod 项目文档](../README.md)
- [CLI 使用说明](../CLI_USAGE.md)
- [Fever API 文档](../../doc/feverapi/fever-api.cn.md)
- [SiliconFlow TTS 文档](../../doc/siliconflow/)
