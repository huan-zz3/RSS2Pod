# RSS2Pod v3.0 - TypeScript

RSS 转播客转换器，具备 AI 驱动的内容增强功能。

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
- 4 个界面组件（MainMenu, SystemStatus, GroupManagement, Placeholder）
- 7 个命令处理器模块（连接所有后端功能）
- 完整的状态管理和导航系统

## CLI 命令（24 个命令）

### 系统状态
```bash
npm run cli -- status          # 显示系统状态和统计
npm run cli -- db:stats        # 数据库统计
```

### 配置管理
```bash
npm run cli -- init            # 创建配置模板
npm run cli -- config:show     # 显示当前配置
npm run cli -- config:set logging.level debug  # 设置配置项
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
npm run cli -- group:edit <id> -n "新名称"  # 编辑组
npm run cli -- group:edit <id> -t count --threshold 10  # 编辑触发器配置
npm run cli -- group:delete <id>       # 删除组
npm run cli -- group:enable <id>       # 启用组
npm run cli -- group:disable <id>      # 禁用组
```

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
npm run cli -- generate:run <groupId>     # 运行流水线
npm run cli -- generate:history           # 显示生成历史
npm run cli -- trigger:status <groupId>   # 显示触发器状态
```

## 项目结构

```
src/
├── cli/                        # 命令行界面（24 个命令）
├── tui/                        # TUI 交互界面
│   ├── components/             # 可复用 UI 组件 (6 个)
│   ├── screens/                # 界面组件 (4 个)
│   ├── commands/               # 命令处理器 (7 个模块)
│   ├── hooks/                  # 自定义 React hooks
│   └── state/                  # 状态管理
├── api/                        # REST API (Fastify)
├── features/
│   ├── events/                 # 事件总线（事件驱动架构）
│   ├── pipeline/               # 7 阶段流水线编排器
│   └── ...                     # 其他功能（TTS、LLM 等）
├── infrastructure/
│   ├── database/               # SQLite 数据库层
│   └── external/               # 外部 API 客户端（Fever 等）
├── services/
│   ├── llm/                    # LLM 服务（DashScope）
│   ├── tts/                    # TTS 服务（SiliconFlow）
│   └── feed/                   # 播客 Feed 生成器
├── repositories/               # 数据访问层
└── shared/
    ├── config/                 # 配置管理
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
    "model": "Qwen/Qwen2.5-72B-Instruct-128K"
  },
  "tts": {
    "provider": "siliconflow",
    "apiKey": "your-key",
    "model": "FunAudioLLM/CosyVoice2-0.5B",
    "voice": "claire"
  }
}
```

## 流水线阶段

1. **获取** - 从 Fever API 获取文章
2. **源摘要** - 为每个源生成摘要（LLM）
3. **组聚合** - 合并为组级摘要
4. **脚本** - 生成播客脚本（LLM）
5. **音频** - 合成音频（TTS）
6. **节目** - 保存节目
7. **订阅源** - 更新播客 RSS 订阅源

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

## 数据库模式

| 表名 | 说明 |
|------|------|
| `articles` | RSS 文章 |
| `groups` | 播客组 |
| `episodes` | 生成的节目 |
| `source_summaries` | 每源摘要 |
| `group_summaries` | 组级摘要 |
| `pipeline_runs` | 执行历史 |
| `processing_state` | 并发锁 |

## 常用工作流

### TUI 工作流（推荐）

```bash
# 1. 启动 TUI
npm run tui

# 2. 在 TUI 中:
#    - 按 1 查看系统状态（版本、数据库、API 配置）
#    - 按 3 管理组（创建、编辑、删除、启用/禁用）
#    - 按 5 测试 Fever API（连接测试、同步订阅源）
#    - 按 6/7 测试 LLM/TTS
#    - 按 8 运行流水线、查看历史
#    - 按 b 返回主菜单
#    - 按 q 退出 TUI
```

**TUI 优势:**
- ✅ 直观的菜单导航
- ✅ 实时显示数据库数据
- ✅ 无需记忆命令
- ✅ 键盘快捷键快速操作
- ✅ 确认对话框防止误操作

### CLI 工作流

```bash
# 1. 初始设置
npm run cli -- init
npm run cli -- db:init
npm run cli -- fever:test

# 2. 查看订阅源
npm run cli -- source:list

# 3. 创建组
npm run cli -- group:create "科技新闻" -s "1,2,3" -t dual

# 4. 缓存文章
npm run cli -- fever:cache-articles -l 50

# 5. 测试 LLM/TTS
npm run cli -- llm:test
npm run cli -- tts:test

# 6. 运行流水线
npm run cli -- generate:run <groupId>

# 7. 查看历史
npm run cli -- generate:history

# 8. 启动 API 服务器
npm run api
```

## 许可证

MIT
