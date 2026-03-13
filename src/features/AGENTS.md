# Features 模块知识库

## 概述

核心业务逻辑：Event Bus（事件驱动架构）和 7 阶段流水线编排器。

## 查找指南

| 任务 | 位置 |
|------|------|
| 修改流水线阶段 | `pipeline/PipelineOrchestrator.ts` |
| 添加事件类型 | `events/EventBus.ts`, `../shared/types/events.ts` |
| 更改阶段执行 | `pipeline/PipelineOrchestrator.ts` (executeStage 方法) |

## 代码约定

- **流水线阶段顺序执行** - 每个阶段必须完成后才能进入下一阶段
- **事件发射** - 在阶段开始/完成时发出事件
- **错误传播** - 错误向上冒泡，运行标记为失败
- **并发控制** - 强制执行 maxConcurrentGroups

## 反模式

- ❌ 不要直接调用流水线阶段 - 使用 `runForGroup()`
- ❌ 不要跳过事件发射 - UI 依赖事件
- ❌ 不要在未更新 PipelineStage 类型的情况下修改阶段顺序

## 独特风格

- **LLM/TTS 集成** 在流水线阶段中（不是外部调用的独立服务）
- **脚本段解析** 处理双语说话人
- **音频分段** 自动分割长文本
