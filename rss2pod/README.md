# RSS2Pod

将 RSS 订阅转化为个性化播客的自动化系统。

## 项目概述

RSS2Pod 是一个个人化自动系统，将多源 RSS 信息经过结构化压缩、对话化重构、音频化生成，最终以标准 Podcast Feed 发布。

### 核心特性

- **多源 RSS 采集** - 通过 Fever API 获取已订阅文章
- **本地缓存支持** - SQLite 缓存层，减少 HTTP 请求，提高响应速度
- **智能摘要** - 源级摘要 + 组级聚合的两层摘要机制
- **脚本生成** - 支持单人播报和双人对话模式
- **英语学习增强** - 词汇解释、句子翻译、理解问题
- **TTS 合成** - 支持 SiliconFlow MOSS 等语音服务
- **Podcast Feed** - 生成 iTunes 兼容的标准 RSS Feed
- **灵活触发** - 支持 Cron 定时、数量阈值、LLM 智慧判断
- **Prompt 管理** - 支持全局默认配置和组别单独覆盖
- **服务层架构** - 统一封装业务逻辑，为 API/CLI 提供一致接口

## 目录结构

```
rss2pod/
├── __init__.py                 # 包初始化
├── cli.py                      # 命令行接口
├── config.py                   # 配置管理
├── config.json                 # 配置文件
├── sources.json                # 本地订阅源缓存
├── requirements.txt            # 依赖列表
│
├── database/                   # 数据库层
│   └── models.py              # 核心数据表
│
├── services/                   # 服务层（业务逻辑封装）
│   ├── __init__.py            # 服务层模块导出
│   ├── base_service.py        # 基础服务类 + ServiceResult
│   ├── fever_service.py       # Fever API 服务
│   ├── tts_service.py         # TTS 服务
│   ├── llm_service.py         # LLM 服务
│   ├── prompt_service.py      # Prompt 管理服务
│   ├── group_service.py       # Group 管理服务
│   ├── scheduler_service.py   # 调度器服务
│   ├── stats_service.py       # 统计服务
│   ├── asset_service.py       # 资源服务
│   ├── config_service.py      # 配置服务
│   ├── basic/                 # 基础服务模块
│   │   └── __init__.py
│   └── pipeline/              # 管道服务模块
│       ├── __init__.py
│       ├── group_processor.py # Group 处理器
│       ├── models.py          # 数据模型
│       ├── pipeline_orchestrator.py # 管道编排器
│       └── service.py         # 管道服务
│
├── fetcher/                    # 采集模块
│   ├── __init__.py
│   ├── fever_client.py        # Fever API 客户端（支持缓存）
│   ├── fever_cache.py         # Fever API 本地缓存管理器
│   └── article_manager.py     # 文章存储与管理
│
├── llm/                        # LLM 处理层
│   ├── __init__.py
│   ├── llm_client.py          # LLM 客户端 (DashScope/Mock)
│   ├── prompt_manager.py      # LLM Prompt 配置管理器
│   ├── source_summarizer.py   # 源级摘要生成器
│   ├── group_aggregator.py    # 组级摘要聚合器
│   └── trigger_engine.py      # 触发引擎 (Cron/数量/LLM 判断)
│
├── script/                     # 脚本生成层
│   ├── __init__.py
│   ├── script_engine.py       # 脚本引擎基类
│   ├── llm_script_engine.py   # LLM 脚本生成器
│   ├── english_learning.py    # 英语学习增强模块
│   ├── prompt_templates.py    # Prompt 模板
│   ├── main.py                # 脚本主入口
│   └── speaker_output.py      # 说话人输出
│
├── tts/                        # TTS 与音频层
│   ├── __init__.py
│   ├── tts_interface.py       # TTS 接口定义
│   ├── siliconflow_provider.py # SiliconFlow 提供商
│   ├── moss_adapter.py        # MOSS 模型适配器
│   ├── adapter.py             # TTS 适配器
│   ├── audio_assembler.py     # 音频拼接器
│   ├── audio_manager.py       # 音频管理器
│   └── tts_providers.py       # TTS 提供商集合
│
├── feed/                       # Feed 发布层
│   ├── __init__.py
│   ├── feed_generator.py      # RSS Feed 生成器
│   └── feed_manager.py        # Feed 管理器
│
└── orchestrator/               # 编排层
    ├── __init__.py
    ├── scheduler.py           # 调度器
    ├── state_manager.py       # 状态管理器
    ├── asset_manager.py       # Episode 资源管理器
    └── logging_config.py     # 日志配置
```

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户入口层                                │
│  ┌─────────────┐  ┌─────────────┐                          │
│  │     CLI     │  │  Scheduler  │                          │
│  └──────┬──────┘  └──────┬──────┘                          │
└─────────┼────────────────┼─────────────────────────────────┘
          │                │
          └────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Services 服务层                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │  Fever  │ │  TTS    │ │  LLM    │ │  Group  │          │
│  │ Service │ │ Service │ │ Service │ │ Service │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ Prompt  │ │Scheduler│ │  Stats  │ │  Asset  │          │
│  │ Service │ │ Service │ │ Service │ │ Service │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              BaseService (统一基类)                      │ │
│  │         ServiceResult (统一返回格式)                     │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                  PipelineOrchestrator                       │
│                   (7 阶段处理流程)                            │
├─────────────────────────────────────────────────────────────┤
│  Stage 1: Fetch Articles      ─► FeverClient               │
│  Stage 2: Source Summaries    ─► SourceSummarizer         │
│  Stage 3: Group Aggregate     ─► GroupAggregator           │
│  Stage 4: Generate Script     ─► LLMScriptEngine           │
│  Stage 5: Synthesize Audio   ─► MossAdapter + Assembler   │
│  Stage 6: Save Episode       ─► DatabaseManager           │
│  Stage 7: Update Feed        ─► FeedManager               │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Scheduler (调度器)                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ TriggerEngine: Cron 触发 | 数量触发 | LLM 判断触发        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                Database (SQLite)                            │
│  Article | Group | Episode | SourceSummary | ProcessingState│
│  PipelineRun | FeverCache | FeverCacheMeta                  │
└─────────────────────────────────────────────────────────────┘
```

## 组件调用关系

### 完整调用链

```
CLI (cli.py)
    │
    ├── generate run ──────► GroupProcessor.process_sync()
    │                          │
    │                          ▼
    │                    PipelineOrchestrator.run()
    │                          │
    │    ┌─────────────┬───────┴───────┬─────────────┐
    │    ▼             ▼               ▼             ▼
    │ Fetch       SourceSummary    GroupSummary    Script
    │ (FeverClient) (SourceSummarizer) (GroupAggregator) (LLM)
    │    │             │               │             │
    │    ▼             ▼               ▼             ▼
    │ Article   Summary Text     JSON Summary    JSON Script
    │    │             │               │             │
    │    └─────────────┴───────┬───────┴─────────────┘
    │                          ▼
    │                    TTS (分段合成)
    │                          │
    │                          ▼
    │                    AudioAssembler (拼接)
    │                          │
    │                          ▼
    │                    Episode + Feed
    │
    └── scheduler start ──► Scheduler.run()
                               │
                               ▼
                          TriggerEngine
                               │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
               Cron      Count    LLM判断
```

### 关键数据类

| 数据类 | 说明 |
|--------|------|
| `FetchResult` | 获取文章结果，包含文章列表和游标 |
| `SummaryResult` | 源级摘要结果列表 |
| `GroupSummaryResult` | 组级摘要聚合结果 |
| `ScriptResult` | 播客脚本和 TTS 输入格式 |
| `TTSResult` | TTS 合成结果，包含音频路径和时长 |
| `EpisodeResult` | Episode 保存结果 |
| `PipelineResult` | 管道总运行结果 |

### 7 阶段管道详解

| 阶段 | 方法 | 说明 |
|------|------|------|
| 1 | `_fetch_articles()` | 从 Fever API 获取文章，存入本地数据库 |
| 2 | `_generate_source_summaries()` | 为每个 RSS 源生成摘要 |
| 3 | `_generate_group_summary()` | 聚合所有源级摘要为组级摘要 |
| 4 | `_generate_script()` | 生成播客对话脚本 |
| 5 | `_synthesize_audio()` | TTS 音频合成（分段+拼接） |
| 6 | `_save_episode()` | 保存 Episode 到数据库 |
| 7 | `_update_feed()` | 更新 RSS Feed |

## 服务层架构

### 设计目标

服务层（Services Layer）位于数据访问层之上，API/CLI 之下，承担以下职责：

- **业务逻辑封装**：将分散在各模块的业务规则集中管理
- **接口统一**：为 API 和 CLI 提供一致的调用接口
- **错误处理**：统一的错误封装和返回格式
- **配置抽象**：集中管理配置加载和数据库连接

### 统一返回格式

```python
@dataclass
class ServiceResult:
    success: bool                    # 是否成功
    error_message: Optional[str]     # 错误信息
    data: Optional[Any]              # 返回数据
    metadata: Dict[str, Any]         # 元数据（如 count 等）
```

### 服务模块列表

| 服务 | 说明 |
|------|------|
| `FeverService` | Fever API 连接、同步、标记操作 |
| `TTSService` | TTS 连接测试、音色列表、语音合成 |
| `LLMService` | LLM 连接测试、对话、JSON 生成 |
| `PromptService` | Prompt 配置管理、导入导出 |
| `GroupService` | Group CRUD、启用/禁用 |
| `SchedulerService` | 调度器控制、触发执行 |
| `StatsService` | 系统统计、活动记录 |
| `AssetService` | Episode 资源管理 |
| `ConfigService` | 配置管理 |

## 快速开始

### 1. 安装依赖

```bash
cd rss2pod
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.json`：

```json
{
  "db_path": "rss2pod.db",
  "fever": {
    "url": "https://your-fever-server.com/fever",
    "username": "your_username",
    "password": "your_password"
  },
  "llm": {
    "provider": "dashscope",
    "api_key": "your_dashscope_key",
    "model": "qwen-plus"
  },
  "tts": {
    "active_provider": "siliconflow",
    "providers": {
      "siliconflow": {
        "api_key": "your_siliconflow_key",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "FunAudioLLM/CosyVoice2-0.5B"
      }
    },
    "active_adapter": "cosyvoice",
    "adapters": {
      "cosyvoice": {
        "voice": "claire"
      },
      "moss": {
        "voice_host": "alex"
      }
    }
  }
}
```

### 3. 使用 CLI

```bash
# 查看帮助
python -m rss2pod.cli --help

# 启用详细输出
python -m rss2pod.cli -v <command>

# 同步订阅源和文章到本地缓存
python -m rss2pod.cli fever sync-all

# 创建 Group
python -m rss2pod.cli group create

# 手动触发生成
python -m rss2pod.cli generate run <group_id>

# 启动调度器
python -m rss2pod.cli scheduler start

# 查看系统状态
python -m rss2pod.cli status

# 管理 Prompts
python -m rss2pod.cli prompt list
python -m rss2pod.cli prompt show source_summarizer
```

详细 CLI 使用说明见 [CLI_USAGE.md](CLI_USAGE.md)。

### 4. FastAPI 后端接口（待实现）

> **注意**: `api.py` 文件已删除，完整的 RESTful API 将在后续统一实现。

## 模块说明

### Database (`database/`)

数据持久化层，使用 SQLite 存储：

| 表名 | 说明 |
|------|------|
| `articles` | RSS 文章：标题、内容、来源、状态 |
| `groups` | 播客组：RSS 源、触发配置、播客结构、prompt 覆盖 |
| `episodes` | 播客节目：脚本、音频、星标、过期时间 |
| `source_summaries` | 源级摘要：来源、摘要内容、关键主题 |
| `processing_state` | Group 处理状态：游标、锁、运行时间 |
| `pipeline_run` | 管道运行记录：阶段、文章数、错误信息 |
| `fever_cache` | Fever API 文章缓存 |
| `fever_cache_meta` | 缓存元数据 |

### Services (`services/`)

业务逻辑服务层，封装统一接口供 API 和 CLI 调用：

- **BaseService** - 基础服务类，提供配置加载和数据库连接
- **ServiceResult** - 统一返回格式
- **FeverService** - Fever API 业务逻辑
- **TTSService** - TTS 业务逻辑
- **LLMService** - LLM 业务逻辑
- **PromptService** - Prompt 管理业务逻辑
- **GroupService** - Group 管理业务逻辑
- **SchedulerService** - 调度器业务逻辑
- **StatsService** - 统计服务
- **AssetService** - 资源服务
- **ConfigService** - 配置服务
- **Pipeline 模块** - 管道编排器、Group 处理器、数据模型

### Fetcher (`fetcher/`)

RSS 采集模块：

- **FeverClient** - 与 Fever API 兼容的 RSS 阅读器交互
- **FeverCacheManager** - SQLite 缓存管理器
- **ArticleManager** - 文章存储、去重

### LLM (`llm/`)

大语言模型处理层：

- **LLMClient** - 统一接口，支持 DashScope 和 Mock
- **PromptManager** - LLM Prompt 配置管理器
- **SourceSummarizer** - 源级摘要生成
- **GroupAggregator** - 组级摘要聚合
- **TriggerEngine** - 触发引擎

### Script (`script/`)

播客脚本生成：

- **ScriptEngine** - 抽象基类
- **LLMScriptEngine** - LLM 脚本生成
- **EnglishLearningEnhancer** - 英语学习增强
- **SpeakerOutput** - 说话人输出格式化
- **Main** - 脚本主入口

### TTS (`tts/`)

文本转语音：

- **TTSInterface** - 统一接口定义
- **SiliconFlowProvider** - SiliconFlow API 实现
- **MossAdapter** - MOSS 模型适配器
- **Adapter** - TTS 适配器
- **AudioAssembler** - 多段音频拼接
- **AudioManager** - 音频管理器
- **TTSProviders** - TTS 提供商集合

### Feed (`feed/`)

Podcast Feed 发布：

- **FeedGenerator** - iTunes 兼容 RSS Feed
- **FeedManager** - 多 Group Feed 管理

### Orchestrator (`orchestrator/`)

系统编排：

- **Scheduler** - Cron 调度
- **StateManager** - 状态管理
- **AssetManager** - Episode 资源管理
- **LoggingConfig** - 日志配置

## 触发机制

支持三种触发方式：

### 1. Cron 定时触发

```json
{
  "trigger_type": "time",
  "trigger_config": {
    "cron": "0 9 * * *"
  }
}
```

### 2. 数量触发

```json
{
  "trigger_type": "count",
  "trigger_config": {
    "threshold": 10
  }
}
```

### 3. LLM 智慧判断

```json
{
  "trigger_type": "llm_judgment",
  "trigger_config": {
    "importance_threshold": 0.7
  }
}
```

## 开发状态

### ✅ 已完成

#### 核心功能
- [x] 数据库模型设计
- [x] Fever API 客户端（支持缓存）
- [x] LLM 客户端 (DashScope/Mock)
- [x] Prompt 管理器 (全局默认 + 组别覆盖)
- [x] 源级摘要生成器
- [x] 组级摘要聚合器
- [x] 脚本引擎 (单人/双人模式)
- [x] TTS 提供商 (SiliconFlow MOSS + CosyVoice)
- [x] Feed 生成器 (iTunes 兼容)
- [x] 调度器 (Cron)
- [x] 触发引擎 (3 种方式)
- [x] 管道编排器 (7 阶段)
- [x] CLI 命令行接口
- [x] 状态管理 (锁机制)
- [x] 英语学习增强
- [x] 端到端测试
- [x] 分段 TTS（解决时长限制）
- [x] Episode 资源管理器

#### 服务层
- [x] BaseService 基础服务类
- [x] ServiceResult 统一返回格式
- [x] FeverService
- [x] TTSService
- [x] LLMService
- [x] PromptService
- [x] GroupService
- [x] SchedulerService
- [x] StatsService
- [x] AssetService
- [x] ConfigService

#### 超出原始设计的扩展功能
- [x] Fever API 本地缓存系统
- [x] Prompt 配置管理系统
- [x] 管道运行记录追踪
- [x] 处理状态锁机制
- [x] 文章导出功能
- [x] 来源订阅源管理
- [x] 丰富的 CLI 调试命令
- [x] 服务层架构
- [x] Episode 中间文件管理
- [x] 分段 TTS 拼接功能
- [x] Pipeline 服务模块

### ⏳ 部分实现

- [ ] 条件逻辑组合 (AND/OR) - 触发条件组合未实现
- [ ] 音频自动清理 - 按过期时间删除（需要调度器配合）

### 📋 待实现

- [ ] Web 管理界面 (NiceGUI)
- [ ] 完整 RESTful API
- [ ] 全文检索
- [ ] 播放统计

## 测试

```bash
# 运行端到端测试
python tests/test_e2e/test_pipeline_e2e.py

# 运行单元测试
pytest tests/
```

## 数据流说明

```
┌─────────────────────────────────────────────────────────────────┐
│                        远端 Fever API                            │
│                     (RSS 文章数据源)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  fever sync-*   │ ← 唯一能从远端拉取数据的入口
                    └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      本地 SQLite 缓存                            │
│                    (rss2pod.db / fever_cache)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     source articles   fever cache-*       generate run
        (只读)          (只读)               (只读)
```

## 相关文件

| 文件 | 说明 |
|------|------|
| `config.json` | 主配置文件 |
| `sources.json` | 本地订阅源缓存 |
| `rss2pod.db` | SQLite 数据库 |
| `data/media/{group}/` | 音频文件存储目录 |
| `data/feeds/{group}/` | RSS Feed 文件目录 |
| `data/exports/` | 文章导出目录 |

## 许可证

MIT License
