# RSS2Pod Orchestrator Module

中央调度器模块，负责 RSS2Pod 系统的自动化处理流程调度。

## 功能概述

- **定时触发**：基于 cron 表达式的定时调度
- **触发器检测**：支持时间触发和数量触发
- **管道编排**：完整的"获取→摘要→脚本→TTS→保存"处理流程
- **状态管理**：数据库锁机制，确保同一 Group 互斥执行
- **日志记录**：结构化日志，支持控制台和文件输出

## 模块结构

```
orchestrator/
├── __init__.py          # 模块导出
├── scheduler.py         # 主调度器
├── pipeline.py          # 处理管道编排
├── group_processor.py   # 单 Group 处理器
├── state_manager.py     # 状态管理（数据库锁）
├── logging_config.py    # 日志配置
└── README.md            # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install croniter python-json-logger aiohttp
```

### 2. 配置

在 `config.json` 中添加 orchestrator 配置：

```json
{
  "orchestrator": {
    "check_interval_seconds": 60,
    "max_concurrent_groups": 3,
    "retry_attempts": 3,
    "retry_delay_seconds": 3
  },
  "logging": {
    "level": "INFO",
    "file": "logs/orchestrator.log",
    "rotation": "daily",
    "retention_days": 7
  }
}
```

### 3. 启动调度器

```bash
# 使用 CLI 启动
rss2pod scheduler start

# 或使用 Python 直接运行
python -m rss2pod.orchestrator.scheduler
```

## 核心组件

### Scheduler（调度器）

主调度器，负责：
- 解析 cron 表达式
- 检测需要触发的 Group
- 启动处理管道
- 并发控制

```python
from rss2pod.orchestrator import Scheduler

scheduler = Scheduler(config, db_path="rss2pod.db")
scheduler.start()  # 阻塞启动
```

### PipelineOrchestrator（管道编排器）

处理管道编排，负责：
- 获取文章
- 生成源级摘要
- 生成组级摘要
- 生成播客脚本
- TTS 音频合成
- 保存 Episode

```python
from rss2pod.orchestrator import PipelineOrchestrator

orchestrator = PipelineOrchestrator(group, state, db, logger, config)
result = await orchestrator.run()
```

### StateManager（状态管理器）

状态管理，负责：
- Group 处理状态管理
- 管道运行记录
- 数据库锁机制

```python
from rss2pod.orchestrator import StateManager

state_manager = StateManager(db)
state_manager.acquire_lock("group-1", "scheduler")
# ... 处理 ...
state_manager.release_lock("group-1", "scheduler")
```

### GroupProcessor（Group 处理器）

简化的单 Group 处理接口：

```python
from rss2pod.orchestrator import process_group_sync

result = process_group_sync("group-1")
print(f"成功：{result.success}")
```

### 缓存同步接口

提供 Fever API 缓存同步功能：

```python
from rss2pod.orchestrator.group_processor import sync_fever_cache, get_fever_cache_stats

# 同步 Fever API 数据到本地缓存
result = sync_fever_cache(db_path="rss2pod.db", limit=1500)
print(f"同步：{result.items_synced} 篇，新增：{result.new_items} 篇")

# 获取缓存统计
stats = get_fever_cache_stats(db_path="rss2pod.db")
print(f"总文章：{stats['total_items']}, 未读：{stats['unread_count']}")
```

**CLI 命令：**
```bash
# 同步缓存
rss2pod fever sync-cache

# 查看统计
rss2pod fever cache-stats
```

## 处理流程

```
触发器检测
    ↓
获取文章 (fetch)
    ↓
源级摘要 (summarize)
    ↓
组级摘要 (aggregate)
    ↓
播客脚本 (script)
    ↓
TTS 合成 (tts)
    ↓
保存 Episode (save)
```

## 状态说明

### ProcessingState 状态

| 状态 | 说明 |
|------|------|
| idle | 空闲，可触发 |
| running | 运行中 |
| error | 错误，等待重试 |
| disabled | 禁用 |

### PipelineRun 状态

| 状态 | 说明 |
|------|------|
| running | 运行中 |
| success | 成功完成 |
| failed | 失败 |
| partial | 部分完成 |

## 错误处理

- 每个阶段失败后自动重试（默认 3 次，间隔 3 秒）
- 超过重试次数后标记为 error 状态
- 日志记录详细错误信息

## API 参考

### Scheduler

```python
class Scheduler:
    def start(self) -> None:
        """启动调度器（阻塞）"""
    
    def stop(self) -> None:
        """停止调度器"""
    
    def run_once(group_id: str = None, dry_run: bool = False) -> Dict:
        """单次运行"""
    
    def get_status() -> Dict:
        """获取状态"""
```

### StateManager

```python
class StateManager:
    def get_state(group_id: str) -> ProcessingState:
        """获取状态"""
    
    def acquire_lock(group_id: str, owner: str) -> bool:
        """获取锁"""
    
    def release_lock(group_id: str, owner: str) -> bool:
        """释放锁"""
    
    def mark_error(group_id: str, error: str) -> bool:
        """标记错误"""
```

## 日志格式

```
2024-01-01 12:00:00,000 - rss2pod.orchestrator - INFO - 调度器启动
2024-01-01 12:00:01,000 - rss2pod.orchestrator - DEBUG - 检查触发器
2024-01-01 12:00:02,000 - rss2pod.orchestrator - INFO - [fetch] 开始获取文章
```

## 故障排查

### 常见问题

1. **调度器不触发**
   - 检查 cron 表达式是否正确
   - 检查 Group 是否启用
   - 检查状态是否为 idle

2. **管道执行失败**
   - 查看日志获取详细错误
   - 检查 Fever API 连接
   - 检查 LLM API 配额

3. **并发问题**
   - 检查数据库锁状态
   - 调整 `max_concurrent_groups` 配置

## 开发调试

```bash
# 模拟运行（不实际处理）
rss2pod generate run --dry-run

# 查看调度器状态
rss2pod scheduler status

# 手动触发单个 Group
rss2pod generate run <group_id>
```

## 版本历史

- 1.0.0 - 初始版本
  - 基础调度功能
  - 管道编排
  - 状态管理
  - 日志系统