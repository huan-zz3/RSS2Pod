# RSS2Pod 命令行工具使用文档

## 📖 概述

RSS2Pod CLI 是一个基于 `typer` 的命令行工具，用于管理和调试 RSS2Pod 播客生成系统。

**版本：** 2.4.0  
**最后更新：** 2026-03-09

---

## 🚀 快速开始

### 环境准备

```bash
cd /home/huanzze/Dev/RSS2Pod/rss2pod
source ~/miniconda3/etc/profile.d/conda.sh
conda activate rss2pod
```

### 基本用法

```bash
# 查看所有帮助
python -m rss2pod.cli --help

# 启用详细输出
python -m rss2pod.cli --verbose <command>
# 或简写
python -m rss2pod.cli -v <command>
```

---

## 📋 命令总览

| 命令组 | 功能 | 主要命令 |
|--------|------|----------|
| `status` | 系统状态检查 | `status` |
| `config` | 配置管理 | `show`, `edit`, `set`, `reset` |
| `source` | 本地订阅源管理（只读） | `list`, `show`, `articles` |
| `group` | Group 管理 | `create`, `list`, `show`, `edit`, `delete` |
| `fever` | Fever API 交互 | `test`, `sync-*`, `cache-*`, `mark-*` |
| `prompt` | LLM Prompt 管理 | `list`, `show`, `edit`, `set`, `reset`, `export`, `import` |
| `llm` | LLM 调试 | `test`, `chat` |
| `tts` | TTS 调试 | `test`, `list-voices`, `listen` |
| `db` | 数据库调试 | `stats`, `list-articles`, `list-groups` |
| `generate` | 生成流程控制 | `run`, `history` |
| `trigger` | 触发器管理 | `status`, `set`, `disable` |
| `scheduler` | 调度器管理 | `start`, `status`, `run` |
| `assets` | Episode 资源管理 | `list`, `show`, `cleanup` |

---

## 🔑 核心原则

### 数据流说明

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

### 服务层架构

CLI 命令通过服务层（Services Layer）调用底层业务逻辑：

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI 命令                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Services 服务层                            │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐   │
│  │Fever│ │TTS  │ │LLM  │ │Group│ │Prompt│ │Sched│ │Stats│   │
│  │Svc  │ │Svc  │ │Svc  │ │Svc  │ │Svc  │ │Svc  │ │Svc  │   │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│      底层模块（Fetcher/LLM/TTS/Database/Orchestrator）       │
└─────────────────────────────────────────────────────────────┘
```

### 重要规则

1. **唯一远端入口**：只有 `fever sync-*` 命令能从远端 Fever API 拉取数据
2. **本地缓存优先**：所有其他查看文章的操作都从本地 SQLite 缓存读取
3. **状态同步**：标记已读/收藏等操作同时更新缓存和远端 API
4. **服务层封装**：CLI 通过服务层调用业务逻辑，便于未来替换实现

---

## 📌 详细命令说明

### 1. `fever` — Fever API 交互 ⭐

**重要**：`fever` 命令组用于与 Fever API 交互。只有 `fever sync-*` 命令能从远端拉取数据。

```bash
# 测试连接
python -m rss2pod.cli fever test

# 同步订阅源列表
python -m rss2pod.cli fever sync-feeds

# 同步文章到缓存
python -m rss2pod.cli fever sync-articles
python -m rss2pod.cli fever sync-articles --limit 500

# 同步全部（订阅源 + 文章）
python -m rss2pod.cli fever sync-all
python -m rss2pod.cli fever sync-all --limit 500
```

#### `fever cache-*` — 查看本地缓存

```bash
# 显示缓存统计
python -m rss2pod.cli fever cache-stats

# 从缓存获取文章列表
python -m rss2pod.cli fever cache-articles
python -m rss2pod.cli fever cache-articles --all      # 所有文章
python -m rss2pod.cli fever cache-articles --unread   # 只看未读
python -m rss2pod.cli fever cache-articles -l 50      # 显示 50 篇

# 从缓存获取订阅源列表
python -m rss2pod.cli fever cache-feeds
```

#### `fever mark-*` — 标记文章状态

```bash
# 标记文章为已读（同时更新缓存和远端 API）
python -m rss2pod.cli fever mark-read 123,456,789

# 收藏文章
python -m rss2pod.cli fever mark-saved 123

# 标记文章为未读（仅本地缓存）
python -m rss2pod.cli fever mark-unread 123,456
```

---

### 2. `source` — 本地订阅源管理

**说明**：`source` 命令组用于管理本地订阅源配置（只读，不访问远端）。

```bash
# 列出本地已保存的订阅源
python -m rss2pod.cli source list

# 查看订阅源详情
python -m rss2pod.cli source show <ID 或 URL>

# 查看指定订阅源的文章（从本地缓存读取）
python -m rss2pod.cli source articles <订阅源 ID>
python -m rss2pod.cli source articles <订阅源 ID> -l 10        # 显示 10 篇
python -m rss2pod.cli source articles <订阅源 ID> --unread     # 只看未读
```

#### `source articles` — 从缓存查看指定订阅源的文章

**重要**：此命令从本地 SQLite 缓存读取文章，不访问远端 API。请先运行 `fever sync-*` 同步数据。

```bash
# 查看订阅源 ID 为 92 的文章
python -m rss2pod.cli source articles 92

# 查看 20 篇文章
python -m rss2pod.cli source articles 92 -l 20

# 只看未读文章
python -m rss2pod.cli source articles 92 --unread
```

---

### 3. `group` — Group 管理 ⭐

```bash
# 列出所有 Group
python -m rss2pod.cli group list

# 查看 Group 详情
python -m rss2pod.cli group show <组 ID>

# 交互式创建 Group
python -m rss2pod.cli group create

# 编辑 Group
python -m rss2pod.cli group edit <组 ID>

# 删除 Group
python -m rss2pod.cli group delete <组 ID>

# 启用/禁用 Group
python -m rss2pod.cli group enable <组 ID>
python -m rss2pod.cli group disable <组 ID>
```

---

### 4. `config` — 配置管理

```bash
# 显示当前配置（隐藏敏感信息）
python -m rss2pod.cli config show

# 使用编辑器打开 config.json
python -m rss2pod.cli config edit

# 设置单个配置项（点号路径）
python -m rss2pod.cli config set llm.api_key "sk-xxx"
python -m rss2pod.cli config set tts.voice "fnlp/MOSS-TTSD-v0.5:claire"

# 重置配置项到默认值
python -m rss2pod.cli config reset llm.model
```

---

### 5. `generate` — 生成流程控制

```bash
# 触发指定 Group 生成
python -m rss2pod.cli generate run <组 ID>

# 触发所有启用的 Group
python -m rss2pod.cli generate run --all

# 模拟运行（不实际生成）
python -m rss2pod.cli generate run <组 ID> --dry-run

# 强制模式（忽略文章更新检查，使用最新三篇）
python -m rss2pod.cli generate run <组 ID> --force

# 导出文章列表到 JSON
python -m rss2pod.cli generate run <组 ID> --export-articles

# 查看生成历史
python -m rss2pod.cli generate history
python -m rss2pod.cli generate history --group=<组 ID>
python -m rss2pod.cli generate history -l 20
```

---

### 6. `scheduler` — 调度器管理

```bash
# 启动调度器（前台运行，按 Ctrl+C 停止）
python -m rss2pod.cli scheduler start

# 查看调度器状态
python -m rss2pod.cli scheduler status

# 手动触发一次调度
python -m rss2pod.cli scheduler run <组 ID>
python -m rss2pod.cli scheduler run  # 触发所有启用的 Group
```

---

### 7. `status` — 系统状态

```bash
python -m rss2pod.cli status
```

输出包含：
- 数据库统计（文章数、Group 数、Episode 数）
- 启用的 Group 列表
- 调度器状态
- Fever 缓存状态
- LLM 连接状态
- TTS 连接状态

---

### 8. `llm` — LLM 调试

```bash
# 测试 LLM 连接
python -m rss2pod.cli llm test

# 对话测试
python -m rss2pod.cli llm chat "你好"

# 详细模式
python -m rss2pod.cli -v llm chat "请总结一下今天的新闻"
```

---

### 9. `tts` — TTS 调试

```bash
# 测试 TTS 连接
python -m rss2pod.cli tts test

# 列出可用音色
python -m rss2pod.cli tts list-voices

# 文本转音频试听
python -m rss2pod.cli tts listen "欢迎收听今天的播客节目"
python -m rss2pod.cli tts listen "Hello, welcome to today's podcast" --voice "xxx"
python -m rss2pod.cli tts listen "你好" -o ./output.mp3
```

---

### 10. `db` — 数据库调试

```bash
# 显示数据库统计
python -m rss2pod.cli db stats

# 列出文章
python -m rss2pod.cli db list-articles
python -m rss2pod.cli db list-articles -l 50

# 列出 Group
python -m rss2pod.cli db list-groups

# 查看文章详情
python -m rss2pod.cli db show-article <article_id>
```

---

### 11. `prompt` — LLM Prompt 管理 ⭐

**说明**：`prompt` 命令组用于管理 LLM Prompt 配置，支持全局默认配置和组别单独覆盖。

```bash
# 列出所有可用的 prompts
python -m rss2pod.cli prompt list

# 查看 prompt 详情
python -m rss2pod.cli prompt show source_summarizer
python -m rss2pod.cli prompt show script_generator --group=group-1  # 查看组别覆盖

# 编辑 prompt（使用编辑器）
python -m rss2pod.cli prompt edit source_summarizer

# 为组别设置 prompt 覆盖
python -m rss2pod.cli prompt set script_generator -g group-1 -c "自定义 template..."
python -m rss2pod.cli prompt set script_generator -g group-1 --system="自定义 system message"

# 重置组别的 prompt 为默认
python -m rss2pod.cli prompt reset script_generator -g group-1

# 导出 prompts 到文件
python -m rss2pod.cli prompt export prompts.json

# 从文件导入 prompts
python -m rss2pod.cli prompt import prompts.json
python -m rss2pod.cli prompt import prompts.json --merge  # 合并导入
python -m rss2pod.cli prompt import prompts.json --replace  # 替换导入
```

#### Prompt 配置说明

系统内置 3 个默认 prompts：

| Prompt 名称 | 说明 | 变量 |
|------------|------|------|
| `source_summarizer` | 源级摘要 - 为来自同一 RSS 源的文章生成综合摘要 | `source_name`, `article_count`, `articles_text` |
| `group_aggregator` | 组级摘要 - 为多个 RSS 源的摘要生成播客大纲 | `group_name`, `source_summaries_text` |
| `script_generator` | 脚本生成 - 根据组级摘要生成播客脚本 | `group_name`, `structure_text`, `learning_text`, `executive_summary`, `full_summary`, `highlights_text`, `structure_requirement`, `learning_requirement` |

#### 组别 Prompt 覆盖

每个 Group 可以自定义 prompt 覆盖，覆盖配置存储在数据库的 `groups.prompt_overrides` 字段中。

```bash
# 查看组别的 prompt 覆盖
python -m rss2pod.cli prompt show source_summarizer --group=group-1

# 为组别设置自定义 prompt
python -m rss2pod.cli prompt set source_summarizer -g group-1 -c "自定义 template 内容..."

# 删除组别的 prompt 覆盖，恢复默认
python -m rss2pod.cli prompt reset source_summarizer -g group-1
```

---

### 12. `assets` — Episode 资源管理 ⭐

**说明**：`assets` 命令组用于管理 Episode 生成过程中产生的中间文件（文稿、分段音频等）。

```bash
# 列出 Group 下所有 Episode 的资源
python -m rss2pod.cli assets list <组 ID>

# 查看指定 Episode 的资源详情
python -m rss2pod.cli assets show <组 ID> <时间戳>

# 清理中间文件（保留最终音频）
python -m rss2pod.cli assets cleanup <组 ID> <时间戳>
python -m rss2pod.cli assets cleanup <组 ID> --all      # 清理所有 Episode
python -m rss2pod.cli assets cleanup <组 ID> --all --force  # 强制清理，不确认
```

#### `assets list` — 列出 Episode 资源

列出指定 Group 下所有 Episode 的中间文件资源：

```bash
# 列出 group-1 的所有 Episode 资源
python -m rss2pod.cli assets list group-1
```

输出包含：
- 资源目录路径
- 文稿文件（源级摘要、组级摘要、播客脚本 JSON/MOSS）
- 分段音频（segment_001_host.mp3 等）
- 最终音频文件

#### `assets show` — 查看 Episode 资源详情

```bash
# 查看指定 Episode 的资源详情
python -m rss2pod.cli assets show group-1 20260309135338
```

#### `assets cleanup` — 清理中间文件

**重要**：此命令仅删除中间文件（分段音频、文稿），保留最终合成的音频文件。

```bash
# 清理指定 Episode 的中间文件
python -m rss2pod.cli assets cleanup group-1 20260309135338

# 清理 Group 所有 Episode 的中间文件
python -m rss2pod.cli assets cleanup group-1 --all

# 强制清理（不确认）
python -m rss2pod.cli assets cleanup group-1 --all --force
```

---

### 13. `trigger` — 触发器管理
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

## 💡 常用场景

### 初次设置流程
```bash
# 1. 同步订阅源和文章到本地缓存
python -m rss2pod.cli fever sync-all

# 2. 创建 Group
python -m rss2pod.cli group create

# 3. 查看系统状态
python -m rss2pod.cli status
```

### 查看文章
```bash
# 查看所有缓存文章
python -m rss2pod.cli fever cache-articles --unread

# 查看指定订阅源的文章
python -m rss2pod.cli source articles 92
python -m rss2pod.cli source articles 92 --unread
```

### 手动生成
```bash
# 模拟运行（推荐首次使用）
python -m rss2pod.cli generate run group-1 --dry-run

# 实际生成
python -m rss2pod.cli generate run group-1

# 强制模式（忽略文章更新检查）
python -m rss2pod.cli generate run group-1 --force

# 生成所有启用的 Group
python -m rss2pod.cli generate run --all
```

### 修改配置
```bash
# 编辑配置文件
python -m rss2pod.cli config edit

# 设置 TTS 音色
python -m rss2pod.cli config set tts.voice "fnlp/MOSS-TTSD-v0.5:alex"

# 重置配置
python -m rss2pod.cli config reset tts.voice
```

### Prompt 调试
```bash
# 查看所有 prompts
python -m rss2pod.cli prompt list

# 查看某个 prompt 详情
python -m rss2pod.cli prompt show source_summarizer

# 编辑 prompt
python -m rss2pod.cli prompt edit script_generator

# 为特定 Group 设置 prompt 覆盖
python -m rss2pod.cli prompt set script_generator -g group-1 -c "自定义模板..."
```

### 调度器运行
```bash
# 前台启动调度器（Ctrl+C 停止）
python -m rss2pod.cli scheduler start

# 后台运行（使用 nohup）
nohup python -m rss2pod.cli scheduler start > scheduler.log 2>&1 &

# 查看调度器状态
python -m rss2pod.cli scheduler status
```

---

## ⚠️ 注意事项

1. **配置文件安全** — `config.json` 包含 API 密钥，不要提交到 Git
2. **删除操作** — 删除 Group 不会删除关联的文章和期数
3. **触发器** — 禁用 Group 会停止自动触发，但仍可手动触发
4. **生成流程** — 首次运行建议先用 `--dry-run` 模拟
5. **调度器模式** — `scheduler start` 是前台运行，需要保持终端开启或使用 nohup/screen
6. **缓存同步** — 查看文章前请先运行 `fever sync-all` 同步数据
7. **锁机制** — 同一 Group 不能同时运行多个管道，系统会自动加锁
8. **服务层调用** — CLI 命令通过服务层（Services）调用业务逻辑，便于未来替换实现

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `config.json` | 主配置文件 |
| `sources.json` | 本地订阅源缓存 |
| `rss2pod.db` | SQLite 数据库（含 fever_cache 表） |
| `cli.py` | CLI 工具源码 |
| `services/` | 服务层模块（业务逻辑封装） |
| `orchestrator/asset_manager.py` | Episode 资源管理器 |
| `data/media/{group}/` | 音频文件存储目录 |
| `data/media/{group}/episode_xxx/` | Episode 中间文件目录 |
| `data/feeds/{group}/` | RSS Feed 文件目录 |
| `data/exports/` | 文章导出目录 |

---

## 📝 版本历史

### v2.3.0 (2026-03-08)
- 新增服务层架构（Services Layer），封装业务逻辑供 API/CLI 调用
- 新增 `BaseService` 基础服务类和 `ServiceResult` 统一返回格式
- 新增 `FeverService`、`TTSService`、`LLMService`、`PromptService`
- 新增 `GroupService`、`SchedulerService`、`StatsService`
- CLI 命令通过服务层调用底层模块

### v2.2.0 (2026-03-08)
- 新增 `prompt` 命令组，用于管理 LLM Prompt 配置
- 新增 `prompt list`、`prompt show`、`prompt edit`、`prompt set`、`prompt reset`、`prompt export`、`prompt import` 命令
- 新增 `source_summarizer`、`group_aggregator`、`script_generator` 三个内置 prompts
- 支持组别 prompt 覆盖配置（存储在 `groups.prompt_overrides` 字段）
- 新增 `llm.prompt_manager` 模块

### v2.4.0 (2026-03-09)
- 新增分段 TTS 功能，解决 SiliconFlow TTS 2 分 43 秒时长限制问题
- 新增 `EpisodeAssetManager` 模块，管理 Episode 中间文件保存
- 新增 `assets` 命令组：`assets list`, `assets show`, `assets cleanup`
- 中间文件保存到 `media/group-x/episode_xxx/` 目录
- 分段音频命名：`segment_001_host.mp3`（带角色信息）
- 支持清理中间文件时保留最终音频

### v2.1.0 (2026-03-08)
- 重构 `fever` 命令组为平铺命令结构
- 命令格式：`fever sync-feeds`, `fever sync-articles`, `fever sync-all`
- 命令格式：`fever cache-stats`, `fever cache-articles`, `fever cache-feeds`
- 命令格式：`fever mark-read`, `fever mark-saved`, `fever mark-unread`

### v2.0.0 (2026-03-08)
- 重构 `fever` 命令组，添加 `sync`、`cache`、`mark` 子命令组
- 重构 `source` 命令组，移除 `sync`、`add`、`remove` 命令
- `source articles` 改为从本地缓存读取
- `fever sync` 默认同步全部（订阅源 + 文章）
- `fever cache` 默认显示统计信息

---

## 🔧 故障排查

### Fever API 连接失败
```bash
# 测试连接
python -m rss2pod.cli fever test

# 检查配置
python -m rss2pod.cli config show

# 查看详细错误
python -m rss2pod.cli -v fever test
```

### 没有新文章
```bash
# 检查缓存状态
python -m rss2pod.cli fever cache-stats

# 强制同步
python -m rss2pod.cli fever sync-all --limit 1000

# 强制模式生成（忽略游标）
python -m rss2pod.cli generate run <group_id> --force
```

### 生成失败
```bash
# 查看 Group 状态
python -m rss2pod.cli group show <group_id>

# 查看处理状态
python -m rss2pod.cli status

# 查看数据库统计
python -m rss2pod.cli db stats
```

---

**文档维护：** 更新 CLI 功能时请同步更新此文档