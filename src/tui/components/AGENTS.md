# TUI Components Module Knowledge Base

## Overview

6 个可复用 UI 组件，使用 React Ink 渲染，提供 TUI 界面的基础构建块。

## Structure

```
components/
├── Select.tsx            # 可选择列表 (j/k 导航)
├── Input.tsx             # 文本输入框
├── Table.tsx             # 数据表格显示
├── ProgressBar.tsx       # 进度条组件
├── Loading.tsx           # 加载动画
├── ConfirmDialog.tsx     # 确认对话框
└── index.ts              # 组件导出
```

## Where to Look

| 任务 | 位置 | 说明 |
|------|------|------|
| 添加新组件 | `components/` 目录创建新 `.tsx` 文件 | 在 `index.ts` 中导出 |
| 修改键盘导航 | `Select.tsx` | j/k/Enter 按键处理 |
| 修改进度显示 | `ProgressBar.tsx` | 进度条样式和标签 |

## 组件详情

### 1. Select (可选择列表)

**文件**: `Select.tsx`

**功能**: 支持键盘导航的选择列表，使用 j/k 或上下箭头键。

**Props**:
```typescript
interface SelectProps {
  items: Array<{ label: string; value: string }>;
  selectedIndex: number;
  onChange: (index: number) => void;
  label?: string;
}
```

**键盘处理**:
- `j` / `↓` - 下一项
- `k` / `↑` - 上一项
- `Enter` - 选择当前项

### 2. Input (文本输入框)

**文件**: `Input.tsx`

**功能**: 支持编辑的文本输入框，带标签和占位符。

**Props**:
```typescript
interface InputProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  placeholder?: string;
  focus?: boolean;
}
```

### 3. Table (数据表格)

**文件**: `Table.tsx`

**功能**: 显示多列数据的表格，支持表头和行样式。

**Props**:
```typescript
interface TableProps {
  columns: string[];
  rows: string[][];
  headerColor?: string;
  rowColor?: string;
}
```

### 4. ProgressBar (进度条)

**文件**: `ProgressBar.tsx`

**功能**: 显示百分比进度条，带标签。

**Props**:
```typescript
interface ProgressBarProps {
  progress: number;  // 0-100
  label?: string;
}
```

### 5. Loading (加载动画)

**文件**: `Loading.tsx`

**功能**: 显示加载动画和消息。

**Props**:
```typescript
interface LoadingProps {
  message?: string;
}
```

### 6. ConfirmDialog (确认对话框)

**文件**: `ConfirmDialog.tsx`

**功能**: 确认对话框，用于破坏性操作前确认。

**Props**:
```typescript
interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  selected: 'cancel' | 'confirm';
  onSelectChange: (selected: 'cancel' | 'confirm') => void;
  onConfirm: () => void;
  onCancel: () => void;
}
```

**注意**: 此组件不自己处理键盘输入，由父组件通过 `useInput` 监听左右箭头键来更新 `selected` 状态。

## 代码约定

- **React Ink 渲染** - 所有组件使用 `@inkjs/ink` 进行终端渲染
- **键盘快捷键** - 一致的按键绑定 (j/k, Enter)
- **无状态组件** - 组件本身不保存状态，状态由父组件管理
- **类型安全** - 所有 Props 有明确的 TypeScript 接口

## 反模式

- ❌ 不要使用 `console.log` - 使用 pino logger
- ❌ 不要在组件中混合业务逻辑 - 保持 UI 纯净
- ❌ 不要硬编码颜色 - 使用 Ink 的颜色系统
- ❌ 不要阻塞事件循环 - 所有操作都是异步的
- ❌ ConfirmDialog 不要自己处理键盘输入 - 由父组件控制

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

### 键盘导航一致性

所有可导航组件使用相同的按键绑定：
- `j` / `↓` - 向下/下一个
- `k` / `↑` - 向上/上一个
- `Enter` - 选择/确认

## 与其他模块的关系

| 模块 | 关系 |
|------|------|
| `tui/screens/` | 屏幕组件使用这些可复用组件 |
| `tui/App.tsx` | 主应用组件组合这些组件 |
| `@inkjs/ink` | React Ink 提供终端渲染能力 |

## 添加新组件步骤

1. 在 `components/` 目录创建新组件 `NewComponent.tsx`
2. 实现 React Ink 组件，接受 Props
3. 在 `index.ts` 中导出新组件
4. 在 `tui/screens/` 中的屏幕组件中使用

## 组件使用示例

**Select 组件**:
```tsx
<Select
  items={groups.map(g => ({ label: g.name, value: g.id }))}
  selectedIndex={selectedIndex}
  onChange={setSelectedIndex}
  label="选择组"
/>
```

**Input 组件**:
```tsx
<Input
  value={groupName}
  onChange={setGroupName}
  label="组名称"
  placeholder="输入组名称"
  focus={true}
/>
```

**Table 组件**:
```tsx
<Table
  columns={['名称', '状态', '文章数']}
  rows={groups.map(g => [g.name, g.enabled ? '启用' : '禁用', String(g.articleCount)])}
  headerColor="cyan"
  rowColor="white"
/>
```

**ProgressBar 组件**:
```tsx
<ProgressBar
  progress={pipelineProgress}
  label="流水线进度"
/>
```

**Loading 组件**:
```tsx
<Loading message="正在加载..." />
```

**ConfirmDialog 组件**:
```tsx
<ConfirmDialog
  title="确认删除"
  message={`确定要删除组 "${group.name}" 吗？`}
  confirmLabel="删除"
  cancelLabel="取消"
  selected={deleteSelection}
  onSelectChange={setDeleteSelection}
  onConfirm={handleDelete}
  onCancel={handleCancel}
/>
```

## 终端兼容性

- **支持现代终端** - iTerm2, Windows Terminal, GNOME Terminal 等
- **颜色支持** - 需要终端支持 ANSI 颜色
- **推荐屏幕尺寸** - 最小 80x24，推荐 120x40+

## 测试

```bash
# 启动 TUI（手动测试组件）
npm run tui

# 运行 TUI 相关测试（如果有）
npm run test test/tui/
```
