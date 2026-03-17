# TUI Module Knowledge Base

## Overview

交互式终端用户界面：使用 React Ink 渲染，支持键盘导航。提供直观的菜单系统，涵盖所有 RSS2Pod 功能。

## Structure

```
tui/
├── index.tsx              # TUI 入口，Ink 渲染
├── App.tsx                # 主应用组件，状态管理
├── screens/               # 界面组件 (11 个界面)
│   ├── MainMenu.tsx       # 主菜单导航
│   ├── SystemStatus.tsx   # 系统状态显示
│   ├── GroupManagement.tsx # 组管理界面
│   ├── GroupEdit.tsx      # 组编辑界面
│   ├── Generation.tsx     # 流水线执行界面
│   ├── FeverAPI.tsx       # Fever API 管理
│   ├── LLMDebug.tsx       # LLM 调试界面
│   ├── TTSDebug.tsx       # TTS 调试界面
│   ├── Configuration.tsx  # 配置管理
│   ├── Sources.tsx        # 订阅源查看器
│   └── Placeholder.tsx    # 占位界面
├── components/            # 可复用 UI 组件 (6 个组件)
│   ├── Select.tsx         # 可选择列表
│   ├── Input.tsx          # 文本输入框
│   ├── Table.tsx          # 数据表格
│   ├── ProgressBar.tsx    # 进度指示器
│   ├── Loading.tsx        # 加载动画
│   └── ConfirmDialog.tsx  # 确认对话框
├── commands/              # 命令处理器 (7 个模块)
│   ├── groups.ts          # 组管理命令
│   ├── system.ts          # 系统状态命令
│   ├── generation.ts      # 流水线执行
│   ├── fever.ts           # Fever API 命令
│   ├── llm.ts             # LLM 调试命令
│   ├── tts.ts             # TTS 调试命令
│   └── index.ts           # 命令注册表
├── hooks/                 # 自定义 React hooks
│   ├── useNavigation.ts   # 导航状态
│   └── index.ts
└── state/                 # 状态管理
    └── navigation.ts      # 导航状态类型
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 添加新界面 | `screens/` | 在 App.tsx 中导入并添加到导航 |
| 添加 UI 组件 | `components/` | 在 index.ts 中导出 |
| 添加命令处理器 | `commands/` | 在 commands/index.ts 中注册 |
| 修改键盘导航 | `hooks/useNavigation.ts` | 按键绑定逻辑 |
| 修改应用状态 | `App.tsx` | 主状态容器 |
| 修改菜单布局 | `screens/MainMenu.tsx` | 菜单项定义 |

## 界面组件详情

**11 个界面**：

| 界面 | 文件 | 功能 |
|------|------|------|
| 主菜单 | `MainMenu.tsx` | 8 个功能分类导航 |
| 系统状态 | `SystemStatus.tsx` | 版本、数据库、API 配置和统计 |
| 组管理 | `GroupManagement.tsx` | 组列表、启用/禁用、删除 |
| 组编辑 | `GroupEdit.tsx` | 创建/编辑组，配置触发器 |
| 生成流程 | `Generation.tsx` | 运行流水线、查看历史、进度显示 |
| Fever API | `FeverAPI.tsx` | 测试连接、同步订阅源、缓存文章 |
| LLM 调试 | `LLMDebug.tsx` | 测试连接、与 LLM 对话 |
| TTS 调试 | `TTSDebug.tsx` | 测试连接、试听声音 |
| 配置 | `Configuration.tsx` | 查看和修改 config.json |
| 订阅源 | `Sources.tsx` | 查看订阅源列表和详情 |
| 占位 | `Placeholder.tsx` | 未实现功能的占位 |

## 可复用组件详情

**6 个 UI 组件**：

| 组件 | 文件 | 功能 |
|------|------|------|
| Select | `Select.tsx` | 可选择列表，支持 j/k 导航 |
| Input | `Input.tsx` | 文本输入框，支持编辑 |
| Table | `Table.tsx` | 数据表格显示 |
| ProgressBar | `ProgressBar.tsx` | 进度条，显示百分比 |
| Loading | `Loading.tsx` | 加载动画 |
| ConfirmDialog | `ConfirmDialog.tsx` | 确认对话框，防止误操作 |

## 命令处理器详情

**7 个命令模块**：

| 模块 | 文件 | 处理的命令 |
|------|------|-----------|
| groups | `groups.ts` | group:list, group:create, group:edit, group:delete |
| system | `system.ts` | status, db:stats |
| generation | `generation.ts` | generate:run, generate:history, trigger:status |
| fever | `fever.ts` | fever:test, fever:sync-feeds, fever:cache-articles |
| llm | `llm.ts` | llm:test, llm:chat |
| tts | `tts.ts` | tts:test |
| 注册表 | `index.ts` | 所有命令的导出 |

## 代码约定

- **React Ink** - 所有组件使用 @inkjs/ink 进行终端渲染
- **键盘快捷键** - 一致的按键绑定 (j/k, Enter, b, q)
- **状态管理** - 集中在 App.tsx，通过 props 传递
- **命令模式** - 每个命令是返回结果的异步函数

## 反模式

- ❌ 不要使用 console.log - 使用 pino logger
- ❌ 不要混合 CLI 和 TUI 逻辑 - 命令是独立的
- ❌ 不要硬编码颜色 - 使用 Ink 的颜色系统
- ❌ 不要阻塞事件循环 - 所有命令都是异步的

## 独特风格

- **键盘优先导航** - j/k 上下，Enter 选择，b 返回，q 退出
- **加载状态** - 所有异步操作显示 Loading 组件
- **确认对话框** - 破坏性操作需要 ConfirmDialog 确认
- **进度条** - 长时间操作显示 ProgressBar 和百分比

## 键盘快捷键

| 键 | 功能 |
|-----|------|
| `↑↓` 或 `j/k` | 导航菜单项 |
| `Enter` | 选择项目 |
| `1-8` | 快速选择类别 |
| `←→` 或 `h/l` | 按钮切换（确认对话框） |
| `b` | 返回上一级 |
| `q` | 退出 |

## 启动命令

```bash
# 启动 TUI 界面
npm run tui

# 启动 TUI 并执行特定命令
npm run tui group:edit 0
npm run tui group:list
```

## 与其他入口的关系

| 入口 | 关系 |
|------|------|
| `src/cli/index.ts` | 调用相同的后端服务，TUI 提供图形界面 |
| `src/api/index.ts` | 独立运行，TUI 不通过 API 直接调用服务 |
| `src/index.ts` | 共享核心初始化逻辑 |

## 状态管理

**App.tsx 状态**：
```typescript
interface AppState {
  currentScreen: ScreenType;
  previousScreen: ScreenType | null;
  selectedGroup: Group | null;
  isLoading: boolean;
  error: string | null;
  // ...
}
```

**导航状态** (`state/navigation.ts`)：
```typescript
export type ScreenType =
  | 'main-menu'
  | 'system-status'
  | 'group-management'
  | 'group-edit'
  | 'generation'
  | 'fever-api'
  | 'llm-debug'
  | 'tts-debug'
  | 'configuration'
  | 'sources';
```

## 组件使用示例

**Select 组件**：
```tsx
<Select
  items={groups.map(g => ({ label: g.name, value: g.id }))}
  selectedIndex={selected_index}
  onChange={setSelectedIndex}
  label="选择组"
/>
```

**ConfirmDialog 组件**：
```tsx
<ConfirmDialog
  title="确认删除"
  message={`确定要删除组 "${group.name}" 吗？`}
  confirmLabel="删除"
  cancelLabel="取消"
  onConfirm={handleDelete}
  onCancel={handleCancel}
/>
```

**Loading 组件**：
```tsx
<Loading message="正在加载..." />
```

**ProgressBar 组件**：
```tsx
<ProgressBar
  progress={pipelineProgress}
  label="流水线进度"
/>
```

## 终端兼容性

- **支持现代终端** - iTerm2, Windows Terminal, GNOME Terminal 等
- **Raw mode 警告** - "Raw mode is not supported" 是正常的开发提示，不影响使用
- **推荐屏幕尺寸** - 最小 80x24，推荐 120x40+

## 测试

```bash
# 启动 TUI（手动测试）
npm run tui

# 运行 TUI 相关测试（如果有）
npm run test test/tui/
```

## 添加新界面步骤

1. 在 `screens/` 目录创建新组件 `NewScreen.tsx`
2. 在 `App.tsx` 中导入新组件
3. 在 `App.tsx` 的 render 逻辑中添加条件渲染
4. 在 `screens/MainMenu.tsx` 中添加菜单项
5. 在 `state/navigation.ts` 中添加新的 ScreenType（如需要）
