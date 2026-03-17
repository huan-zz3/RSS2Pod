# RSS2Pod v3.0 - TypeScript

RSS 转播客转换器，具备 AI 驱动的内容增强功能。

**Tech Stack:** TypeScript + Node.js + ESM + Fastify + SQLite + LLM (DashScope) + TTS (SiliconFlow) + React Ink (TUI) + node-cron

## 快速开始

### TUI 交互界面（推荐）

```bash
# 启动 TUI 交互界面
npm run tui
```

**TUI 键盘操作:**

| 键 | 功能 |
|-----|------|
| `↑↓` 或 `j/k` | 导航菜单项 |
| `Enter` | 选择项目 |
| `1-8` | 快速选择类别 |
| `←→` 或 `h/l` | 按钮切换（确认对话框） |
| `b` | 返回上一级 |
| `q` | 退出 |

**注意:** 如果在某些终端环境中看到 "Raw mode is not supported" 警告，这是正常的开发提示，TUI 仍然可以正常工作。

### CLI 命令行

```bash
# 安装依赖
npm install

# 创建配置
npm run cli -- init

# 编辑 config.json 填入你的 API 密钥

# 初始化数据库
npm run cli -- db:init

# 测试 Fever API 连接
npm run cli -- fever:test

# 查看系统状态
npm run cli -- status

# 列出所有订阅源
npm run cli -- source:list

# 创建组
npm run cli -- group:create "科技新闻" -s "1,2,3"

# 为组运行流水线
npm run cli -- generate:run <groupId>
```

## TUI 功能

TUI 提供交互式界面，支持：

- **系统状态** - 查看版本、数据库、API 配置和统计信息
- **配置管理** - 查看和修改配置
- **组管理** - 创建、编辑、删除、启用/禁用组（显示真实数据库数据）
- **订阅源管理** - 查看订阅源列表和详情
- **Fever API** - 测试连接、同步订阅源、缓存文章
- **LLM 调试** - 测试连接、与 LLM 对话
- **TTS 调试** - 测试连接
- **生成流程** - 运行流水线、查看历史、触发器状态

**TUI 组件:**
- 6 个可复用 UI 组件（Select, Input, Table, ProgressBar, Loading, ConfirmDialog）
- 11 个界面组件（MainMenu, SystemStatus, GroupManagement, GroupEdit, Generation, FeverAPI, LLMDebug, TTSDebug, Configuration, Sources, Placeholder）
- 7 个命令处理器模块（连接所有后端功能）
- 完整的状态管理和导航系统

## CLI 命令（33 个命令）

**完整命令列表:**

```bash
npm run cli -- -h

# 输出:
Usage: rss2pod [options] [command]

RSS to Podcast Converter with AI Enhancement

Options:
  -V, --version                            output the version number
  -h, --help                               display help for command

Commands:
  init                                     Create configuration template
  db:init                                  Initialize the database
  db:stats                                 Show database statistics
  status                                   Show system status
  config:show                              Show current configuration (without secrets)
  config:set <key> <value>                 Set configuration value
  config:validate                          Validate configuration file with Zod schema
  group:list [options]                     List all groups
  group:show <id>                          Show group details (supports index or ID)
  group:create [options] <name>            Create a new group
  group:edit [options] <id>                Edit group configuration (supports index or ID)
  group:delete <id>                        Delete a group (supports index or ID)
  group:enable <id>                        Enable a group (supports index or ID)
  group:disable <id>                       Disable a group (supports index or ID)
  source:list                              List all feeds
  source:show <id>                         Show feed details
  fever:test                               Test Fever API connection
  fever:sync-feeds                         Sync feed list
  fever:cache-articles [options]           Cache articles to local database
  sync:run [groupId]                       Manually trigger article sync (optionally for specific group)
  sync:status                              Show sync service status and configuration
  llm:test                                 Test LLM connection
  llm:chat <prompt>                        Chat with LLM for testing
  tts:test                                 Test TTS connection
  generate:run <groupId>                   Run generation pipeline for a group (supports index or ID)
  generate:history                         Show generation history
  pipeline:runs [options] <groupId>        View pipeline execution history for a group (supports index or ID)
  episode:list [options] <groupId>         List generated podcast episodes for a group (supports index or ID)
  trigger:status <groupId>                 Show trigger status for a group (supports index or ID)
  article:unprocessed [options] <groupId>  List unprocessed articles for a group (supports index or ID)
  trigger:check <groupId>                  Check if trigger conditions are met for a group (supports index or ID)
  scheduler:start                          Start the scheduler service
  scheduler:stop                           Stop the scheduler service
  scheduler:status                         Display scheduler configuration and enabled groups
  pipeline:stop <runId>                    Stop a running pipeline by run ID
  help [command]                           display help for command
```

### 系统状态
```bash
npm run cli -- status          # 显示系统状态和统计
npm run cli -- db:stats        # 数据库统计
npm run cli -- sync:status     # 显示同步服务状态和配置
```

### 配置管理
```bash
npm run cli -- init            # 创建配置模板
npm run cli -- config:show     # 显示当前配置
npm run cli -- config:set logging.level debug  # 设置配置项
npm run cli -- config:validate               # 验证配置文件
```

### 数据库
```bash
npm run cli -- db:init         # 初始化数据库
```

### 组管理
```bash
npm run cli -- group:list              # 列出所有组
npm run cli -- group:list -e           # 仅列出已启用的组
npm run cli -- group:show <id>         # 显示组详情
npm run cli -- group:create "名称" -s "1,2"  # 创建新组
npm run cli -- group:create "名称" -s "1,2" --learning-mode word_explanation  # 创建时指定英语学习模式
npm run cli -- group:edit <id> -n "新名称"  # 编辑组
npm run cli -- group:edit <id> -t count --threshold 10  # 编辑触发器配置
npm run cli -- group:edit <id> --learning-mode sentence_translation  # 编辑英语学习模式
npm run cli -- group:delete <id>       # 删除组
npm run cli -- group:enable <id>       # 启用组
npm run cli -- group:disable <id>      # 禁用组
```

**英语学习模式说明**：
- `normal` - 正常播报（默认）
- `word_explanation` - 句后难词解释
- `sentence_translation` - 句后整句翻译

### 订阅源管理
```bash
npm run cli -- source:list             # 列出所有订阅源
npm run cli -- source:show <id>        # 显示订阅源详情
```

### Fever API
```bash
npm run cli -- fever:test              # 测试连接
npm run cli -- fever:sync-feeds        # 同步订阅源列表
npm run cli -- fever:cache-articles -l 100  # 缓存文章
```

### 同步服务
```bash
npm run cli -- sync:run [groupId]      # 手动触发文章同步（可选指定组）
npm run cli -- sync:status             # 显示同步服务状态和配置
```

### LLM 调试
```bash
npm run cli -- llm:test                # 测试 LLM 连接
npm run cli -- llm:chat "你好"          # 与 LLM 对话
```

### TTS 调试
```bash
npm run cli -- tts:test                # 测试 TTS 连接
```

### 生成流程
```bash
npm run cli -- generate:run <groupId>           # 运行流水线
npm run cli -- generate:history                 # 显示生成历史
npm run cli -- trigger:status <groupId>         # 显示触发器状态
npm run cli -- pipeline:runs <groupId>          # 查看流水线历史（按组）
npm run cli -- pipeline:stop <runId>            # 停止正在运行的流水线
npm run cli -- episode:list <groupId>           # 列出播客节目
npm run cli -- article:unprocessed <groupId>    # 查看未处理文章
npm run cli -- trigger:check <groupId>          # 手动检查触发条件
```

### 调度器
```bash
npm run cli -- scheduler:start            # 启动调度器服务
npm run cli -- scheduler:stop             # 停止调度器服务
npm run cli -- scheduler:status           # 显示调度器配置和启用的组
```

## 项目结构

```
src/
├── cli/                        # 命令行界面（33 个命令）
├── tui/                        # TUI 交互界面 (React Ink)
│   ├── components/             # 可复用 UI 组件 (6 个)
│   ├── screens/                # 界面组件 (11 个)
│   ├── commands/               # 命令处理器 (7 个模块)
│   ├── hooks/                  # 自定义 React hooks
│   └── state/                  # 状态管理
├── api/                        # REST API (Fastify)
├── features/
│   ├── events/                 # 事件总线（事件驱动架构）
│   ├── pipeline/               # 6 阶段流水线编排器
│   ├── scheduler/              # 调度器（4 种触发器）
│   └── sync/                   # 独立同步服务（600s 间隔）
├── infrastructure/
│   ├── database/               # SQLite 数据库层（9 张表）
│   └── external/               # 外部 API 客户端（Fever）
├── services/
│   ├── llm/                    # LLM 服务（DashScope）
│   ├── tts/                    # TTS 服务（SiliconFlow）
│   └── feed/                   # 播客 Feed 生成器
├── repositories/               # 数据访问层（SQLite CRUD）
└── shared/
    ├── config/                 # 配置管理（Zod 验证）
    └── types/                  # TypeScript 类型定义
```

## 配置

编辑 `config.json`:

```json
{
  "fever": {
    "baseUrl": "https://your-ttrss/plugins/fever",
    "email": "your-email",
    "password": "your-password"
  },
  "llm": {
    "provider": "dashscope",
    "apiKey": "your-key",
    "model": "qwen3.5-plus",
    "maxTokens": 2000,
    "temperature": 0.7
  },
  "tts": {
    "provider": "siliconflow",
    "apiKey": "your-key",
    "model": "FunAudioLLM/CosyVoice2-0.5B",
    "voice": "claire",
    "baseUrl": "https://api.siliconflow.cn/v1"
  },
  "scheduler": {
    "checkInterval": 60,
    "maxConcurrentGroups": 3
  },
  "sync": {
    "enabled": true,
    "interval": 600,
    "maxArticlesPerSync": 100
  },
  "api": {
    "host": "0.0.0.0",
    "port": 3000,
    "baseUrl": "http://localhost:3000"
  }
}
```

**配置说明**:
- `api.baseUrl` - 控制 Feed 生成的公开 URL（生产环境改为你的域名）
- `sync.interval` - 同步间隔（秒），默认 600 秒（10 分钟）
- `scheduler.checkInterval` - 触发器检查间隔（秒），默认 60 秒

### 组触发器配置

使用 CLI 配置组的触发器：

```bash
# 数量触发：10 篇文章时触发
npm run cli -- group:edit <groupId> -t count --threshold 10

# 时间触发：每天早上 9 点
npm run cli -- group:edit <groupId> -t time --cron "0 9 * * *"

# LLM 触发：启用 LLM 内容评估
npm run cli -- group:edit <groupId> -t llm --llm-enabled true

# 混合触发：数量或时间（任一满足即触发）
npm run cli -- group:edit <groupId> -t mixed --threshold 5 --cron "0 */6 * * *"
```

## 流水线阶段

1. **获取** - 从 Fever API 获取文章
2. **源摘要** - 为每个源生成摘要（LLM）
3. **组聚合** - 合并为组级摘要
4. **脚本** - 生成播客脚本（LLM）
5. **音频** - 合成音频（TTS）
6. **节目** - 保存节目
7. **订阅源** - 更新播客 RSS 订阅源

## 触发器机制

系统支持三种触发方式，可组合使用：

### 时间触发
- 基于 Cron 表达式
- 支持每日/每周/指定时间触发
- 到时间检测是否满足生成条件，无新内容可跳过
- 示例：`0 9 * * *` = 每天早上 9 点

### 数量触发
- 当未处理文章数量达到阈值时触发
- 立即进入生成流程
- 示例：threshold=10 → 10 篇文章触发

### LLM 判断触发
- 将未处理文章摘要交给 LLM 分析
- LLM 判断是否具有集中主题、生成价值
- 根据判断结果决定是否触发

### 混合触发
- 结合上述三种方式
- 任一条件满足即触发

## 开发

```bash
# 构建
npm run build

# 运行（实时重载）
npm run dev

# 类型检查
npm run typecheck

# Lint 检查
npm run lint

# 运行测试
npm run test
```

## 数据库模式（9 张表）

| 表名 | 说明 |
|------|------|
| `articles` | RSS 文章 |
| `groups` | 播客组 |
| `episodes` | 生成的节目 |
| `source_summaries` | 每源摘要 |
| `group_summaries` | 组级摘要 |
| `pipeline_runs` | 执行历史 |
| `processing_state` | 并发锁 |
| `feeds` | 订阅源列表 |
| `schema_info` | 模式版本控制 |

## 常用工作流

### TUI 工作流（推荐）

```bash
# 1. 启动 TUI
npm run tui

# 2. 在 TUI 中:
#    - 按 1 查看系统状态（版本、数据库、API 配置）
#    - 按 2 配置管理
#    - 按 3 管理组（创建、编辑、删除、启用/禁用）
#    - 按 4 订阅源管理
#    - 按 5 测试 Fever API（连接测试、同步订阅源、缓存文章）
#    - 按 6 测试 LLM（连接测试、对话）
#    - 按 7 测试 TTS（连接测试）
#    - 按 8 生成流程（运行流水线、查看历史、触发器状态）
#    - 按 b 返回主菜单
#    - 按 q 退出 TUI
```

**TUI 优势:**
- ✅ 直观的菜单导航
- ✅ 实时显示数据库数据
- ✅ 无需记忆命令
- ✅ 键盘快捷键快速操作
- ✅ 确认对话框防止误操作
- ✅ 进度条显示流水线执行状态

### CLI 工作流

```bash
# 1. 初始设置
npm run cli -- init             # 创建配置模板
npm run cli -- db:init          # 初始化数据库
npm run cli -- fever:test       # 测试 Fever API 连接

# 2. 查看订阅源
npm run cli -- source:list

# 3. 创建组（配置触发器）
npm run cli -- group:create "科技新闻" -s "1,2,3"
npm run cli -- group:edit <groupId> -t count --threshold 10  # 数量触发
npm run cli -- group:edit <groupId> -t time --cron "0 9 * * *"  # 时间触发
npm run cli -- group:edit <groupId> -t llm --llm-enabled true  # LLM 触发

# 4. 缓存文章
npm run cli -- fever:cache-articles -l 50

# 5. 测试 LLM/TTS
npm run cli -- llm:test
npm run cli -- tts:test

# 6. 手动检查触发条件
npm run cli -- trigger:check <groupId>

# 7. 启动调度器（自动运行）
npm run cli -- scheduler:start

# 8. 或手动运行流水线
npm run cli -- generate:run <groupId>

# 9. 查看历史
npm run cli -- generate:history
npm run cli -- pipeline:runs <groupId>

# 10. 启动 API 服务器
npm run api
```

## 故障排除

### 流水线卡住或失败

#### 问题：流水线运行时突然停止

**可能原因**：
1. 组没有关联订阅源
2. 没有未处理的文章
3. LLM/TTS API 超时

**解决方案**：

```bash
# 1. 检查组是否有关联的订阅源
npm run cli -- group:show <groupId>

# 2. 如果没有源，添加订阅源
npm run cli -- group:edit <groupId> -s "1,2,3"

# 3. 查看未处理文章数量
npm run cli -- article:unprocessed <groupId>

# 4. 如果流水线卡住，停止它
npm run cli -- pipeline:runs <groupId>  # 查看运行历史
npm run cli -- pipeline:stop <runId>    # 停止正在运行的流水线

# 5. 清理卡住的运行记录（如果 pipeline:stop 无效）
sqlite3 data/rss2pod.db "DELETE FROM pipeline_runs WHERE status='running';"
```

#### 问题：错误消息 "No unprocessed articles found"

**原因**：组内所有文章都已被处理

**解决方案**：
1. 缓存更多文章：`npm run cli -- fever:cache-articles -l 100`
2. 检查组的订阅源是否正确：`npm run cli -- group:show <groupId>`
3. 确认文章属于组的源：检查 `source_ids` 配置

### 调度器问题

#### 问题：调度器没有自动触发流水线

**检查步骤**：
```bash
# 1. 检查调度器状态
npm run cli -- scheduler:status

# 2. 手动检查触发条件
npm run cli -- trigger:check <groupId>

# 3. 查看触发器配置
npm run cli -- group:show <groupId>
```

### API 连接问题

#### 问题：Fever API 连接失败

**解决方案**：
```bash
# 测试连接
npm run cli -- fever:test

# 如果失败，检查：
# 1. config.json 中的 baseUrl, email, password 是否正确
# 2. TT-RSS 服务器是否可访问
# 3. Fever 插件是否已启用
```

#### 问题：LLM/TTS API 失败

**解决方案**：
```bash
# 测试 LLM 连接
npm run cli -- llm:test

# 测试 TTS 连接
npm run cli -- tts:test

# 如果失败，检查：
# 1. config.json 中的 API 密钥是否正确
# 2. 网络连接是否正常
# 3. API 配额是否用完
```

## 许可证

MIT
