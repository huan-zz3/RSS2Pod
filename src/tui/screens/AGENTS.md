# TUI Screens Module Knowledge Base

## Overview

11 个界面组件，每个都是有限状态机（mode 驱动），使用 React Ink 渲染，提供完整的 RSS2Pod 功能交互界面。

## Structure

```
screens/
├── MainMenu.tsx           # 主菜单导航（8 个功能分类）
├── SystemStatus.tsx       # 系统状态显示
├── GroupManagement.tsx    # 组管理（创建/编辑/删除/启用/禁用）
├── GroupEdit.tsx          # 组编辑界面（触发器配置）
├── Generation.tsx         # 流水线执行界面（进度显示）
├── FeverAPI.tsx           # Fever API 管理
├── LLMDebug.tsx           # LLM 调试界面
├── TTSDebug.tsx           # TTS 调试界面
├── Configuration.tsx      # 配置管理
├── Sources.tsx            # 订阅源查看器
└── Placeholder.tsx        # 占位界面
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 添加新界面 | `screens/` 目录创建新组件 | 在 `App.tsx` 中导入并添加到导航 |
| 修改菜单布局 | `MainMenu.tsx` | 菜单项定义和快捷键绑定 |
| 修改组管理流程 | `GroupManagement.tsx` | mode 状态机管理创建/编辑/删除流程 |
| 修改流水线进度显示 | `Generation.tsx` | EventBus 订阅和进度更新 |

## 界面组件详情

### 11 个界面

| 界面 | 文件 | 功能 | 关键模式 |
|------|------|------|----------|
| 主菜单 | `MainMenu.tsx` | 8 个功能分类导航 | 简单列表选择 |
| 系统状态 | `SystemStatus.tsx` | 版本、数据库、API 配置和统计 | 只读显示 |
| 组管理 | `GroupManagement.tsx` | 组列表、启用/禁用、删除 | `Mode = 'view' | 'creating' | 'deleting' | 'editing'` |
| 组编辑 | `GroupEdit.tsx` | 创建/编辑组，配置触发器 | 表单输入模式 |
| 生成流程 | `Generation.tsx` | 运行流水线、查看历史、进度显示 | EventBus 实时订阅 |
| Fever API | `FeverAPI.tsx` | 测试连接、同步订阅源、缓存文章 | 命令执行模式 |
| LLM 调试 | `LLMDebug.tsx` | 测试连接、与 LLM 对话 | 对话历史模式 |
| TTS 调试 | `TTSDebug.tsx` | 测试连接、试听声音 | 命令执行模式 |
| 配置 | `Configuration.tsx` | 查看和修改 config.json | 表单编辑模式 |
| 订阅源 | `Sources.tsx` | 查看订阅源列表和详情 | 列表选择模式 |
| 占位 | `Placeholder.tsx` | 未实现功能的占位 | 简单提示 |

## 代码约定

### 模式驱动 UI（Mode-Driven UI）

每个屏幕组件都是有限状态机：

```typescript
type Mode = 'view' | 'creating' | 'deleting' | 'editing';
const [mode, setMode] = useState<Mode>('view');

if (mode === 'creating') {
  return <Input .../>;
}
if (mode === 'deleting') {
  return <ConfirmDialog .../>;
}
// 默认 view 模式
return <Table .../>;
```

**约定**：
- 所有逻辑扁平化在单一组件内
- 避免组件嵌套过深
- `mode` 状态决定渲染哪个子组件

### 键盘事件分层处理

```typescript
// 通用导航（j/k/Enter/q/b）→ 封装在可复用组件中
useInput((input, key) => {
  if (key.downArrow || input === 'j') { ... }
});

// 业务操作（c 创建，e 编辑，d 删除）→ 在屏幕组件中处理
useInput((input, key) => {
  if (input === 'c') { setMode('creating'); }
  if (input === 'e') { onEdit?.(group.id); }
});
```

### EventBus 订阅模式

```typescript
// Generation.tsx - 流水线进度监听
const unsubscribeSegment = eventBus.subscribe(
  'pipeline:audio:segment-completed', 
  (event) => {
    if (payload?.groupId === groupId) {
      setCurrentSegment(segmentIndex);
      setProgress(newProgress);
    }
  }
);

// 清理订阅
if (unsubscribeSegment) unsubscribeSegment();
```

**关键约定**：
- TUI 组件直接订阅 EventBus 获取实时进度
- 使用 `groupId` 过滤事件，避免接收其他组的事件
- **手动清理订阅**防止内存泄漏

## 反模式

- ❌ 不要使用 console.log - 使用 pino logger
- ❌ 不要在组件中混合业务逻辑 - 调用 commands 模块
- ❌ 不要阻塞事件循环 - 所有操作都是异步的
- ❌ 不要忘记清理 EventBus 订阅 - 手动调用 unsubscribe
- ❌ 不要硬编码颜色 - 使用 Ink 的颜色系统

## 独特风格

### 控制组件模式

`ConfirmDialog` 组件不自己处理键盘输入，而是由父组件通过 `useInput` 监听左右箭头键来更新 `selected` 状态：

```typescript
// ConfirmDialog.tsx - 仅接收 selected 状态，不处理输入
export interface ConfirmDialogProps {
  selected: 'cancel' | 'confirm';  // 外部控制选中状态
}

// GroupManagement.tsx - 父组件处理输入
useInput((input, key) => {
  if (input === 'a' || key.leftArrow) {
    setDeleteSelection('cancel');
  } else if (input === 'd' || key.rightArrow) {
    setDeleteSelection('confirm');
  }
});
```

### 短生命周期 DB 连接

每个命令独立管理 DB 连接（打开 → 查询 → 关闭）：

```typescript
// commands/groups.ts
export async function listGroups(): Promise<GroupInfo[]> {
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  const groups = groupRepo.findAll();
  dbManager.close();  // 每次调用都打开/关闭
  return groups;
}
```

**优点**：避免连接泄漏
**缺点**：频繁打开/关闭开销

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `tui/components/` | 使用 6 个可复用 UI 组件 |
| `tui/commands/` | 调用命令处理器获取数据 |
| `tui/App.tsx` | 主状态容器，管理屏幕切换 |
| `features/events/EventBus` | 订阅流水线进度事件 |
| `features/` | 通过 commands 间接调用业务逻辑 |

## 添加新界面步骤

1. 在 `screens/` 目录创建新组件 `NewScreen.tsx`
2. 在 `App.tsx` 中导入新组件
3. 在 `App.tsx` 的 render 逻辑中添加条件渲染
4. 在 `screens/MainMenu.tsx` 中添加菜单项
5. 在 `state/navigation.ts` 中添加新的 ScreenType（如需要）

## 测试

```bash
# 启动 TUI（手动测试）
npm run tui

# 运行 TUI 相关测试（如果有）
npm run test test/tui/
```
