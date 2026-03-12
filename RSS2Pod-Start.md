> 缺少我感兴趣的英语播客，能否自己结合 rss 做一个？

---

# 一、项目整体定位与设计目标

## 1.1 核心目标

构建一个个人化自动系统，将：

- 多源 RSS 信息
- 结构化压缩
- 对话化重构
- 英语学习增强
- 音频化生成
- 标准 Podcast Feed 发布

整合为一个持续运行的知识处理与播报系统。

该系统强调：

- 个人使用
- 自动化
- 可配置
- 可扩展
- 可替换组件设计

---

## 1.2 非目标

本系统不是：

- 多用户 SaaS 平台
- 高并发 API 服务
- 商业分发系统
- 内容推荐算法平台
- 复杂知识图谱系统

---

# 二、系统总体结构说明

系统由六个逻辑层构成：

1. RSS 采集层
2. 分组聚合层
3. LLM 处理层
4. 脚本生成层
5. TTS 与音频组装层
6. Podcast Feed 发布层

所有模块必须解耦，便于未来替换或重构。

---

# 三、RSS 采集与文章管理模块

## 3.1 RSS 数据来源

系统通过 TT-RSS + Fever API 获取已订阅文章。

采集逻辑需具备：

- 周期性拉取（但不标为已读）
- 转换为纯文本，排除图片（避免输入给 llm 过多 token）
- 基于发布时间排序

---

## 3.2 文章存储要求

每条文章必须存储：

- 标题
- 来源
- 发布时间
- 原始正文
- 归属 RSS 源
- 是否已被某组处理

文章必须长期可保留，用于：

- 原文对照展示
- 后续复用（如重新生成）

---

## 3.3 文章拼接策略

当某 RSS 源在当前生成周期内有多条文章时：

- 允许拼接
- 控制总 token 上限
- 保证语义连续性

拼接目标是：

> 提高单次 LLM 调用效率
> 避免短文章单独调用浪费 token

---

# 四、分组（Group）管理机制

## 4.1 分组概念

每个 Group 是一个“信息处理策略容器”，具备：

- 一组 RSS 源
- 一套 Skills 规则
- 一组触发条件
- 一个独立 Podcast Feed
- 一套清理策略

Group 是系统的核心配置单位。

---

## 4.2 Group 功能要求

每个 Group 必须支持：

- 新增 / 编辑 / 删除
- 绑定多个 RSS 源
- 指定摘要倾向
- 指定播客结构（单人 / 双人）
- 指定英语学习增强模式
- 指定生成触发策略
- 指定音频保留周期

---

## 4.3 独立 Feed 要求

每个 Group 必须生成独立 Podcast Feed。

原因：

- 在 AntennaPod 中可独立订阅
- 可单独控制自动下载
- 可单独暂停某类内容

Feed URL 必须固定且长期稳定。

---

# 五、生成触发机制

触发机制必须支持组合逻辑。

---

## 5.1 时间触发

- 支持标准 cron 表达式
- 支持每日 / 每周 / 指定时间

行为规则：

- 到时间自动检测是否具备生成条件
- 若无新内容，可跳过

---

## 5.2 数量触发

- 当组内未处理文章数量 ≥ 设定阈值
- 立即进入生成流程

---

## 5.3 LLM 判断触发

系统可将当前未处理文章摘要交给 LLM。

LLM 判断：

- 是否具有集中主题
- 是否具有生成价值
- 是否值得制作一期播客

该结果用于触发决策。

---

## 5.4 条件逻辑组合

支持：

- AND 条件
- OR 条件

例如：

- 时间到 AND 文章数量足够
- 文章数量足够 OR LLM 判定集中度高

必须允许灵活配置。

---

# 六、内容处理与摘要生成

## 6.1 源级摘要

同一 RSS 源的文章：

- 拼接
- 统一生成源级摘要
- 摘要偏向由 skills 决定（如宏观分析、技术细节等）

---

## 6.2 组级汇总

所有源级摘要合并后：

- 当作组级总摘要
- 作为播客脚本生成输入

该两层摘要机制目的是：

- 控制 token 使用
- 提升主题集中度
- 提高内容结构质量

---

# 七、播客脚本生成模块

## 7.1 ScriptEngine 抽象设计

必须抽象脚本引擎接口。

可支持：

- Mooncast 适配器（Mooncast 融合方式暂不确定，不得耦合）
- 自定义 Prompt Engine
- 未来替换方案

---

## 7.2 播客结构模式

### 单人播报

- 类似新闻播音
- 结构紧凑
- 适合 Daily Brief

---

### 双人对话

- 主持人 + 协主持人
- 自然交替
- 增强沉浸感

必须输出结构化 speaker 列表。

---

# 八、英语学习增强模块

该模块属于 Script 生成阶段。

---

## 8.1 支持模式

1. 正常播报
2. 句后难词解释
3. 句后整句翻译

必须允许 Group 独立配置。

---

## 8.2 设计原则

- 翻译自然
- 不打断逻辑流
- 不显得机械
- 不重复冗余

---

# 九、TTS 抽象层

必须设计统一接口。

支持：

- 不同云 TTS 服务
- 单人 / 双人 voice
- 可调语速

---

## 9.1 双人拼接策略

- 每段文本分别生成音频
- 拼接为单一完整 MP3
- 保证音量统一
- 保证无明显断层

---

# 十、音频管理与清理机制

## 10.1 保留策略

- 星标内容永久保留
- 非星标按 retention\_days 删除

---

## 10.2 清理流程

删除必须严格顺序：

1. 从 Feed 中移除
2. 删除音频文件
3. 更新数据库

防止客户端 404。

---

# 十一、Podcast Feed 规范

每个 Group 一个 Feed。

Feed 必须包含（查阅 PSP-1: The Podcast RSS Standard.md 文档）

---

## 11.1 enclosure 要求

必须支持 HTTP Range 请求。

否则在播客应用中：

- 无法拖动进度条
- 无法断点续播

---

# 十二、原文对照显示

在 Feed 中嵌入 HTML 原文。

限制：

- 仅基础 HTML 标签
- 不允许嵌入 JS
- 不使用复杂样式

保证在 AntennaPod 中可读。

---

# 十三、Web 管理界面

必须提供管理页面，包含：

- Group 管理
- RSS 绑定
- Skills 编辑
- 触发条件配置
- 手动生成按钮
- 星标管理
- 历史期列表
- 查看脚本
- 查看音频
- 查看原文与摘要

界面无需华丽，但必须清晰。

---

# 十四、数据库核心结构

必须包括：

- Article
- SourceSummary
- Group
- Episode

Episode 包含：

- 脚本内容
- 音频路径
- guid
- starred
- expire\_at

其余根据项目需求实时改进

---

# 十五、系统边界与规模假设

- 单用户
- 低并发
- SQLite 足够
- 本地文件存储足够
- 云 LLM 调用
- TTS 服务可替换

---

# 十六、技术栈要求

- 使用 FastAPI + NiceGUI 完成整个项目前后端，python 是唯一核心语言
- 使用 SQLite 存储数据
- 使用 python-feedgen 项目用于生成结构化的 `Podcast Feed`
- 不参考使用 Mooncast 项目
- 参考 podcastfy 项目“文本转多语言音频对话”的实现逻辑，但不要使用其余部分功能
- 参考 feverapi 的文档，我们需要从该 api 获得 rss 文本内容

---

# 十七、服务层架构（新增）

## 17.1 服务层设计目标

为统一封装业务逻辑，向 API 层和 CLI 层提供一致的服务接口，特设计独立的服务层（Services Layer）。

服务层位于数据访问层（Database/Fetcher/LLM/TTS 等）之上，API/CLI 之下，承担以下职责：

- **业务逻辑封装**：将分散在各模块的业务规则集中管理
- **接口统一**：为 API 和 CLI 提供一致的调用接口
- **事务管理**：确保跨模块操作的原子性
- **错误处理**：统一的错误封装和返回格式
- **配置抽象**：集中管理配置加载和数据库连接

---

## 17.2 服务层结构

```
rss2pod/services/
├── __init__.py              # 服务层模块导出
├── base_service.py          # 基础服务类
├── fever_service.py         # Fever API 服务
├── tts_service.py           # TTS 服务
├── llm_service.py           # LLM 服务
├── prompt_service.py        # Prompt 管理服务
├── group_service.py         # Group 管理服务
├── scheduler_service.py     # 调度器服务
└── stats_service.py         # 统计服务
```

---

## 17.3 基础服务类（BaseService）

所有服务的基类，提供通用功能：

```python
class BaseService:
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        self.config_path = config_path
        self.db_path = db_path
        self._config = None  # 懒加载配置
        self._db = None      # 懒加载数据库连接
    
    @property
    def config(self): ...    # 懒加载配置
    @property
    def db(self): ...        # 懒加载数据库连接
    def close(self): ...     # 关闭服务，释放资源
```

---

## 17.4 统一返回格式（ServiceResult）

所有服务方法返回统一格式：

```python
@dataclass
class ServiceResult:
    success: bool                    # 是否成功
    error_message: Optional[str]     # 错误信息
    data: Optional[Any]              # 返回数据
    metadata: Dict[str, Any]         # 元数据（如 count 等）
```

---

## 17.5 各服务模块职责

### FeverService
- `test_connection()` - 测试 Fever API 连接
- `sync_feeds()` - 同步订阅源列表
- `sync_articles(limit)` - 同步文章到缓存
- `mark_as_read(item_ids)` - 标记已读
- `mark_as_saved(item_id)` - 收藏文章
- `mark_as_unread(item_ids)` - 标记未读（本地）
- `get_cache_stats()` - 获取缓存统计
- `get_cache_articles(limit, unread, feed_id)` - 获取文章列表
- `get_cache_feeds()` - 获取订阅源列表

### TTSService
- `test_connection()` - 测试 TTS 连接
- `list_voices(model)` - 列出可用音色
- `synthesize(text, voice, output_path)` - 文本转语音

### LLMService
- `test_connection()` - 测试 LLM 连接
- `chat(message, system_message)` - 与 LLM 对话
- `generate_json(prompt, schema)` - 生成结构化 JSON

### PromptService
- `list_prompts()` - 列出所有 prompts
- `get_prompt(name, group_id)` - 获取 prompt 配置
- `get_prompt_template(name, group_id)` - 获取 prompt 模板
- `get_prompt_system(name, group_id)` - 获取 system message
- `set_global_prompt(name, prompt_data)` - 设置全局 prompt
- `set_group_override(group_id, name, prompt_data)` - 设置组别覆盖
- `reset_group_override(group_id, name)` - 重置组别覆盖
- `export_prompts(filepath)` - 导出 prompts
- `import_prompts(filepath, merge)` - 导入 prompts
- `render_template(name, variables, group_id)` - 渲染模板

### GroupService
- `list_groups(enabled_only)` - 列出 Group
- `get_group(group_id)` - 获取 Group 详情
- `create_group(group_data)` - 创建 Group
- `update_group(group_id, group_data)` - 更新 Group
- `delete_group(group_id)` - 删除 Group
- `enable_group(group_id)` - 启用 Group
- `disable_group(group_id)` - 禁用 Group
- `get_group_episodes(group_id, limit)` - 获取期数列表

### SchedulerService
- `start()` - 启动调度器
- `stop()` - 停止调度器
- `get_status()` - 获取调度器状态
- `run_once(group_id)` - 手动触发一次调度
- `trigger_generation(group_id, force, export_articles)` - 触发生成
- `get_generation_history(group_id, limit)` - 获取生成历史

### StatsService
- `get_system_stats()` - 获取系统整体统计
- `get_database_stats()` - 获取数据库统计
- `get_fever_cache_stats()` - 获取 Fever 缓存统计
- `get_processing_stats()` - 获取处理状态统计
- `get_group_stats(group_id)` - 获取 Group 统计
- `get_recent_activity(days)` - 获取最近活动记录

---

## 17.6 服务层调用关系

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

## 17.7 服务层优势

1. **解耦**：API/CLI 不直接依赖底层模块，便于替换实现
2. **复用**：API 和 CLI 共享同一套业务逻辑
3. **测试**：服务层可独立进行单元测试
4. **扩展**：新增功能只需添加新服务，不影响现有代码
5. **维护**：业务逻辑集中管理，便于维护和审计

---

# 十八、实现状态总结

## 18.1 已完成功能

| 模块 | 状态 | 说明 |
|------|------|------|
| RSS 采集层 | ✅ | Fever API 客户端、本地缓存 |
| 数据库层 | ✅ | 7 个核心数据表 |
| LLM 处理层 | ✅ | DashScope 客户端、摘要生成 |
| 脚本生成层 | ✅ | ScriptEngine、单人/双人模式 |
| TTS 层 | ✅ | SiliconFlow 适配 |
| Feed 发布层 | ✅ | python-feedgen 集成 |
| 服务层 | ✅ | 8 个服务模块 |
| Orchestrator | ✅ | 管道编排、状态管理 |
| 触发机制 | 🟡 | 时间/数量触发完成，LLM 触发待完善 |
| 音频清理 | 🟡 | 基础支持，自动清理待完善 |
| Web 界面 | ❌ | NiceGUI 界面未实现 |

## 18.2 待完成工作

1. **Web 管理界面** - NiceGUI 实现
2. **API 端点扩展** - 完整 RESTful API
3. **CLI 重构** - 迁移到服务层调用
4. **LLM 判断触发** - 完善触发机制
5. **音频自动清理** - 按 retention_days 清理

---

# 十九、超出原始设计的实现

> 本章节记录了在 RSS2Pod-Start.md 原始设计之外，项目实际实现过程中新增的功能和模块。

## 19.1 新增服务模块

### AssetService（资源服务）

用于管理 Episode 生成过程中产生的中间文件：

- **功能**：
  - 列出 Group 下所有 Episode 的资源
  - 查看指定 Episode 的资源详情
  - 清理中间文件（保留最终音频）

- **资源类型**：
  - 源级摘要文本（`source_summary_*.txt`）
  - 组级摘要文本（`group_summary_*.txt`）
  - 播客脚本 JSON（`script_*.json`）
  - MOSS 脚本（`script_*.moss`）
  - 分段音频（`segment_001_host.mp3` 等）
  - 最终合成音频（`final_*.mp3`）

- **存储位置**：`data/media/{group_id}/episode_{timestamp}/`

### ConfigService（配置服务）

提供配置管理的统一接口：

- **功能**：
  - 加载/保存配置文件
  - 嵌套配置值获取/设置
  - 使用系统编辑器编辑配置
  - 配置项重置到默认值
  - 脱敏配置输出（隐藏 API Key）

- **默认配置值**：
  - LLM: `qwen3.5-plus`
  - TTS: `FunAudioLLM/CosyVoice2-0.5B:claire`
  - 调度器检查间隔: 60秒
  - 最大并发组数: 3
  - 日志级别: INFO

## 19.2 分段 TTS 功能

### 背景

SiliconFlow MOSS 模型存在 2 分 43 秒的音频时长限制。为解决此问题，实现了分段 TTS 功能：

- **实现方式**：
  - 将长文本按段落分割
  - 每段分别调用 TTS API
  - 使用 `pydub` 拼接为完整音频

- **音频命名规范**：
  - 格式：`segment_{序号}_{角色}.mp3`
  - 示例：`segment_001_host.mp3`, `segment_002_guest.mp3`

- **最终合成**：
  - 所有分段拼接后生成最终音频
  - 文件名：`final_{timestamp}.mp3`

## 19.3 Prompt 管理系统

### 设计目标

支持灵活的 Prompt 配置，满足不同 Group 的个性化需求：

- **全局默认 Prompt**：系统内置的默认 Prompt 模板
- **组别覆盖**：每个 Group 可以覆盖默认 Prompt
- **配置存储**：覆盖配置存储在数据库 `groups.prompt_overrides` 字段

### 内置 Prompts

| Prompt 名称 | 说明 | 主要变量 |
|------------|------|----------|
| `source_summarizer` | 源级摘要生成 | `source_name`, `article_count`, `articles_text` |
| `group_aggregator` | 组级摘要聚合 | `group_name`, `source_summaries_text` |
| `script_generator` | 播客脚本生成 | `group_name`, `structure_text`, `learning_text` 等 |

### CLI 命令

```bash
# 列出所有 prompts
python -m rss2pod.cli prompt list

# 查看 prompt 详情
python -m rss2pod.cli prompt show source_summarizer

# 编辑 prompt
python -m rss2pod.cli prompt edit script_generator

# 为组别设置覆盖
python -m rss2pod.cli prompt set script_generator -g group-1 -c "自定义模板..."

# 导出/导入
python -m rss2pod.cli prompt export prompts.json
python -m rss2pod.cli prompt import prompts.json
```

## 19.4 Pipeline 运行记录

### 功能

记录每次管道执行的详细信息，用于调试和审计：

- **记录内容**：
  - 执行开始/结束时间
  - 各阶段状态（pending/running/completed/failed）
  - 处理的文章数量
  - 错误信息（如有）

- **存储位置**：`pipeline_run` 数据库表

### 用途

- 查看历史生成记录
- 分析失败原因
- 优化管道性能

## 19.5 状态锁机制

### 功能

防止同一 Group 并发执行管道，确保处理一致性：

- **实现方式**：
  - 使用 SQLite 事务和行锁
  - `processing_state` 表记录当前处理状态
  - 执行前检查锁状态，如已锁定则跳过

- **锁字段**：
  - `is_running`: 是否正在运行
  - `lock_time`: 加锁时间
  - `lock_token`: 锁标识（用于识别持有者）

## 19.6 EpisodeAssetManager

### 功能

管理单个 Episode 的所有资源文件：

- **资源组织**：
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

- **管理操作**：
  - `list_assets()`: 列出所有资源
  - `cleanup()`: 清理中间文件（保留 final.mp3）
  - `get_info()`: 获取 Episode 元信息

## 19.7 服务层架构扩展

### 第九个服务模块

原设计包含 8 个服务模块，实际实现共 9 个：

| 服务模块 | 说明 |
|----------|------|
| FeverService | Fever API 服务 |
| TTSService | TTS 服务 |
| LLMService | LLM 服务 |
| PromptService | Prompt 管理服务 |
| GroupService | Group 管理服务 |
| SchedulerService | 调度器服务 |
| StatsService | 统计服务 |
| AssetService | 资源服务（新增） |
| ConfigService | 配置服务（新增） |

### 便捷函数

每个服务模块除了类接口外，还提供了模块级便捷函数：

```python
from services.fever_service import sync_articles
from services.tts_service import synthesize
from services.llm_service import chat
from services.group_service import list_groups
```

## 19.8 CLI 功能增强

### 新增命令组

| 命令组 | 功能 |
|--------|------|
| `assets` | Episode 资源管理 |
| `trigger` | 触发器管理 |
| `source` | 本地订阅源管理（只读） |

### assets 命令

```bash
# 列出资源
python -m rss2pod.cli assets list <group_id>

# 查看详情
python -m rss2pod.cli assets show <group_id> <timestamp>

# 清理中间文件
python -m rss2pod.cli assets cleanup <group_id> <timestamp>
python -m rss2pod.cli assets cleanup <group_id> --all
```

## 19.9 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v1.0.0 | - | 初始版本 |
| v2.0.0 | 2026-03-08 | 重构 fever 命令组 |
| v2.1.0 | 2026-03-08 | 重构 fever/source 命令 |
| v2.2.0 | 2026-03-08 | 新增 Prompt 管理系统 |
| v2.3.0 | 2026-03-08 | 新增服务层架构 |
| v2.4.0 | 2026-03-09 | 新增分段 TTS 和资源管理 |

## 19.10 待实现功能（补充）

除第十八章列出的待完成工作外，还有以下待实现：

1. **音频自动清理** - 按 `expire_at` 字段自动删除过期 Episode
2. **条件逻辑组合** - 支持 AND/OR 触发条件组合
3. **LLM 判断触发完善** - 主题集中度判断逻辑
4. **全文检索** - 文章全文搜索功能
5. **播放统计** - 记录 Feed 下载/播放次数

---

## 二十、REST API 实现

### 20.1 FastAPI 后端

项目实现了基于 FastAPI 的 REST API 接口：

- **API 端点** (`rss2pod/web/api.py`)：
  - `GET /groups` - 获取 Group 列表
  - `GET /groups/{group_id}` - 获取 Group 详情
  - `POST /groups/{group_id}/trigger` - 触发生成
  - `GET /groups/{group_id}/episodes` - 获取 Episode 列表
  - `GET /groups/{group_id}/feed-url` - 获取 RSS Feed URL
  - `GET /health` - 健康检查

- **RSS 接口** (`rss2pod/web/rss.py`)：
  - `GET /rss/{group_id}.xml` - 获取 Podcast RSS Feed

- **Web 应用** (`rss2pod/web/app.py`)：
  - FastAPI 应用入口
  - 静态文件挂载

### 20.2 Web 前端

项目包含简单的前端界面：

- **静态资源** (`rss2pod/web/static/`)：
  - `index.html` - 主页面
  - `app.js` - 前端 JavaScript
  - `style.css` - 样式文件

### 20.3 服务层扩展

除第十七章描述的 8 个服务外，实际实现了更多服务模块：

| 服务模块 | 说明 |
|----------|------|
| `FeedService` | Feed 生成和发布服务 |
| `StateService` | 状态管理服务 |
| `LoggingService` | 日志服务 |
| `DatabaseService` | 数据库操作服务 |

---

## 二十一、Pipeline 服务模块

### 21.1 Pipeline 模块结构

`services/pipeline/` 目录包含完整的管道服务：

- **service.py** - `PipelineService` 管道服务类
- **pipeline_orchestrator.py** - `PipelineOrchestrator` 管道编排器
- **group_processor.py** - `GroupProcessor` Group 处理器
- **models.py** - 数据模型定义

### 21.2 便捷函数

提供了模块级便捷函数：

```python
from services.pipeline.service import run_pipeline, run_pipeline_sync
from services.pipeline.group_processor import GroupProcessor
```

---

## 二十二、触发器命令

### 22.1 CLI 触发器管理

新增 `trigger` 命令组用于管理触发器：

```bash
# 查看触发器状态
python -m rss2pod.cli trigger status <组 ID>

# 设置触发类型
python -m rss2pod.cli trigger set <组 ID> --type=time
python -m rss2pod.cli trigger set <组 ID> --type=count
python -m rss2pod.cli trigger set <组 ID> --type=llm_judgment

# 设置 Cron 表达式
python -m rss2pod.cli trigger set <组 ID> --cron="0 9 * * *"

# 设置数量阈值
python -m rss2pod.cli trigger set <组 ID> --threshold=10

# 禁用触发器
python -m rss2pod.cli trigger disable <组 ID>
```

---

## 二十三、版本演进

### 23.1 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v1.0.0 | - | 初始版本 |
| v2.0.0 | 2026-03-08 | 重构 fever 命令组 |
| v2.1.0 | 2026-03-08 | 重构 fever/source 命令 |
| v2.2.0 | 2026-03-08 | 新增 Prompt 管理系统 |
| v2.3.0 | 2026-03-08 | 新增服务层架构 |
| v2.4.0 | 2026-03-09 | 新增分段 TTS 和资源管理 |
| v2.5.0 | 2026-03-12 | 新增 REST API 和 Web 界面 |

### 23.2 完成状态总结

截至 v2.5.0，项目的完整功能矩阵：

| 功能模块 | 状态 | 说明 |
|----------|------|------|
| RSS 采集层 | ✅ | Fever API 客户端、本地缓存 |
| 数据库层 | ✅ | 9 个核心数据表 |
| LLM 处理层 | ✅ | DashScope 客户端、摘要生成 |
| 脚本生成层 | ✅ | ScriptEngine、单人/双人模式 |
| TTS 层 | ✅ | SiliconFlow 适配、分段合成 |
| Feed 发布层 | ✅ | python-feedgen 集成、REST API |
| 服务层 | ✅ | 12 个服务模块 |
| Orchestrator | ✅ | 管道编排、状态管理 |
| REST API | ✅ | FastAPI 端点实现 |
| Web 界面 | ✅ | HTML/JS/CSS 静态页面 |
| 触发机制 | 🟡 | 时间/数量触发完成，LLM 触发待完善 |
| 音频清理 | 🟡 | 基础支持，自动清理待完善 |

---

## 二十四、项目当前进度总结

### 24.1 已完成功能

项目已完成的功能远超出原始设计，主要包括：

1. **核心管道** - 7 阶段完整处理流程
2. **服务层架构** - 12 个服务模块的统一封装
3. **REST API** - FastAPI 实现的完整 API 端点
4. **Web 界面** - 简单的前端管理界面
5. **CLI 工具** - 完整的命令行管理工具
6. **资源管理** - Episode 中间文件管理
7. **分段 TTS** - 解决长音频时长限制
8. **Prompt 管理** - 全局/组别覆盖配置

### 24.2 待完成功能

1. **音频自动清理** - 按过期时间自动删除
2. **条件逻辑组合** - AND/OR 触发条件
3. **LLM 判断触发完善** - 主题集中度判断
4. **全文检索** - 文章搜索功能
5. **播放统计** - 下载/播放计数
6. **Web 界面完善** - 完整的管理界面（当前仅基础）

### 24.3 下一步建议

1. 完善音频自动清理功能
2. 实现触发条件 AND/OR 组合
3. 开发完整的 Web 管理界面（NiceGUI）
4. 添加全文检索功能
