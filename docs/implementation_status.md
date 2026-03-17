# 实现状态清单

以下对 src/tui/commands 下各命令模块的实现状态、返回格式以及错误处理现状进行汇总。

- system.ts
  - 实现状态：已实现（getSystemStats）
  - 返回格式：SystemStats
  - 错误处理：try/catch 存在但 catch 为空，需要改进
  - 备注：存在降级数据返回的需求。

- groups.ts
  - 实现状态：已实现（listGroups、getGroup、createGroup、deleteGroup）
  - 返回格式：GroupInfo | GroupInfo[] | string | void
  - 错误处理：目前缺乏统一错误捕获，资源释放在异常路径未保障

- fever.ts
  - 实现状态：已实现（testFeverConnection、listFeeds、listFeverGroups、syncFeeds）
  - 返回格式：boolean | FeedInfo[] | GroupInfo[] | number
  - 错误处理：未见统一处理，存在直接抛错的风险

- generation.ts
  - 实现状态：已实现（runPipeline、getPipelineHistory）
  - 返回格式：PipelineRun | PipelineHistory[]
  - 错误处理：runPipeline 有 try/catch，getPipelineHistory 需完善

- tts.ts
  - 实现状态：已实现（testTTSConnection）
  - 返回格式：boolean
  - 错误处理：缺乏统一捕获与日志

- llm.ts
  - 实现状态：已实现（testLLMConnection、chatWithLLM）
  - 返回格式：boolean | string
  - 错误处理：缺乏统一捕获与日志

- 汇总结论
  - 当前实现覆盖完整，但需要建立统一的错误处理与返回结构，以提升稳定性与可维护性。
