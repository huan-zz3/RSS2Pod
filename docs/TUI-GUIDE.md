# RSS2Pod TUI 使用指南

**生成时间:** 2026-03-13
**版本:** v3.0.0

## 快速开始

### 启动 TUI

```bash
npm run tui
```

### 键盘快捷键

| 键 | 功能 | 上下文 |
|-----|------|--------|
| `↑` / `↓` | 上/下导航 | 所有菜单/列表 |
| `j` / `k` | 上/下导航 | 所有菜单/列表（Vim 风格） |
| `Enter` | 选择/确认 | 所有上下文 |
| `b` | 返回 | 所有子界面 |
| `q` | 退出 | 任何界面 |
| `1-8` | 快速选择类别 | 主菜单 |
| `←` / `→` | 按钮切换 | 确认对话框 |
| `h` / `l` | 按钮切换 | 确认对话框（Vim 风格） |

## 主菜单

启动 TUI 后显示主菜单，包含 8 个类别：

```
RSS2Pod TUI v3.0.0

▶ 1. System Status
  2. Configuration
  3. Group Management
  4. Source Management
  5. Fever API
  6. LLM Debug
  7. TTS Debug
  8. Generation

↑↓ Navigate  Enter Select  q Quit
```

## 各界面功能

### 1. System Status（系统状态）

显示系统配置和统计信息：
- RSS2Pod 版本
- 数据库路径
- Fever API 配置
- LLM 配置
- TTS 配置
- 组数量
- 文章数量
- 节目数量

**快捷键:** `b` 或 `q` 返回

### 2. Configuration（配置管理）

查看和修改配置（开发中）

### 3. Group Management（组管理）

管理播客组：
- 显示所有组列表（表格形式）
- 显示组 ID、名称、启用状态、触发器类型、源数量
- 连接真实数据库数据

**快捷键:**
- `↑↓` / `j/k` - 导航组列表
- `c` - 创建组（开发中）
- `e` - 编辑组（开发中）
- `d` - 删除组（开发中）
- `b` - 返回

### 4. Source Management（订阅源管理）

管理 RSS 订阅源（开发中）

### 5. Fever API

Fever API 工具：
- 测试 Fever API 连接
- 同步订阅源列表
- 缓存文章到本地数据库

**快捷键:** `b` 或 `q` 返回

### 6. LLM Debug

LLM 调试工具：
- 测试 LLM 连接
- 与 LLM 对话测试

**快捷键:** `b` 或 `q` 返回

### 7. TTS Debug

TTS 调试工具：
- 测试 TTS 连接

**快捷键:** `b` 或 `q` 返回

### 8. Generation（生成流程）

流水线执行和监控：
- 运行流水线生成节目
- 查看生成历史
- 查看触发器状态

**快捷键:** `b` 或 `q` 返回

## TUI 组件

TUI 使用 6 个可复用的 UI 组件：

### Select（选择框）
- 键盘导航的列表选择
- 支持 `↑↓` / `j/k` 导航
- 绿色高亮当前选项

### Input（输入框）
- 文本输入
- 光标闪烁效果
- 支持退格删除

### Table（表格）
- 数据表格显示
- 行选择功能
- 列对齐

### ProgressBar（进度条）
- 可视化进度显示
- 百分比显示
- 动态更新

### Loading（加载指示器）
- 动画旋转器
- 加载消息显示

### ConfirmDialog（确认对话框）
- 操作确认
- 按钮选择（Cancel/Confirm）
- 防止误操作

## 技术架构

```
src/tui/
├── components/           # 6 个 UI 组件
├── screens/              # 4 个界面组件
├── commands/             # 7 个命令处理器
├── hooks/                # 自定义 React hooks
├── state/                # 状态管理
├── App.tsx               # 根组件
└── index.tsx             # 入口文件
```

## 常见问题

### Q: 看到 "Raw mode is not supported" 警告

**A:** 这是正常的开发提示，不影响 TUI 功能。TUI 仍然可以正常工作。

### Q: 看到 React key 警告

**A:** 这是开发环境的警告，不影响功能。已在最新版本中修复。

### Q: TUI 无法启动

**A:** 确保已安装所有依赖：
```bash
npm install
```

### Q: 键盘无响应

**A:** 确保终端支持 raw mode。尝试：
- 使用现代终端（iTerm2, Windows Terminal, GNOME Terminal）
- 避免在 IDE 内置终端运行

## 开发 TUI

### 添加新界面

1. 在 `src/tui/screens/` 创建新组件
2. 在 `App.tsx` 中添加路由
3. 在主菜单中添加入口

### 示例：创建新界面

```tsx
// src/tui/screens/MyScreen.tsx
import { useInput } from 'ink';
import { Box, Text } from 'ink';

export interface MyScreenProps {
  onBack: () => void;
}

export function MyScreen({ onBack }: MyScreenProps) {
  useInput((input, key) => {
    if (input === 'b' || input === 'q' || key.escape) {
      onBack();
    }
  });

  return (
    <Box flexDirection="column">
      <Text bold>My Screen</Text>
      <Box marginTop={1}>
        <Text>Content here...</Text>
      </Box>
    </Box>
  );
}
```

## 下一步

TUI 仍在积极开发中。计划中的功能：
- ✅ 完整的组管理（创建、编辑、删除）
- ⏳ 完整的订阅源管理
- ⏳ 流水线进度实时显示
- ⏳ 批量操作支持
- ⏳ 搜索和过滤功能

## 反馈

如有问题或建议，请提交 Issue。
