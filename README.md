# RSS2Pod v3.0 - TypeScript

RSS 转播客转换器，具备 AI 驱动的内容增强功能。

## 快速开始

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

# 为组运行流水线
npm run cli -- pipeline:run <groupId>
```

## CLI 命令

```bash
# 配置
npm run cli -- init                    # 创建配置模板
npm run cli -- config:show             # 显示当前配置

# 数据库
npm run cli -- db:init                 # 初始化数据库

# 组管理
npm run cli -- group:list              # 列出所有组
npm run cli -- group:list -e           # 仅列出已启用的组
npm run cli -- group:create "My Group" # 创建新组

# Fever API
npm run cli -- fever:test              # 测试连接

# 流水线
npm run cli -- pipeline:run <groupId>  # 为组运行流水线
```

## 项目结构

```
src/
├── cli/                        # 命令行界面
├── features/
│   ├── events/                 # 事件总线（事件驱动架构）
│   ├── pipeline/               # 7 阶段流水线编排器
│   └── ...                     # 其他功能（TTS、LLM 等）
├── infrastructure/
│   ├── database/               # SQLite 数据库层
│   └── external/               # 外部 API 客户端（Fever 等）
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
    "model": "qwen3.5-plus"
  },
  "tts": {
    "provider": "siliconflow",
    "apiKey": "your-key",
    "model": "FunAudioLLM/CosyVoice2-0.5B"
  }
}
```

## 流水线阶段

1. **获取** - 从 Fever API 获取文章
2. **源摘要** - 为每个源生成摘要
3. **组聚合** - 合并为组级摘要
4. **脚本** - 生成播客脚本
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
```

## 数据库模式

- `articles` - RSS 文章
- `groups` - 播客组
- `episodes` - 生成的节目
- `source_summaries` - 每源摘要
- `group_summaries` - 组级摘要
- `pipeline_runs` - 执行历史
- `processing_state` - 并发锁

## 许可证

MIT
