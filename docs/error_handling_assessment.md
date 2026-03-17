# 错误处理评估（命令处理器模块）

本文件对 src/tui/commands 下各命令模块的错误处理现状进行评估，给出改进方向。

- system.ts
  - 当前实现：getSystemStats 内部对数据库操作放在 try 块中，但 catch 块为空，且并非所有路径都保证了资源释放。
  - 风险：若数据库操作抛错，错误被吞掉，返回的数据可能不准确，且没有日志记录。
  - 改善建议：在 catch 中记录日志并返回降级数据或错误信息；确保在异常路径也能释放资源。

- groups.ts
  - 当前实现：对数据库操作没有 try/catch，出现异常时将向上传播，且未在 finally 中确保 dbManager.close()。
  - 风险：资源未释放、错误信息缺乏结构化处理。
  - 改善建议：整个操作包裹在 try/finally；使用统一的错误对象封装错误信息。

- fever.ts
  - 当前实现：对 Fever 客户端调用没有 try/catch，错误直接抛出。
  - 风险：不可预期的异常未被捕获，UI 需要统一的错误结构。
  - 改善建议：对 Fever 调用加上 try/catch，返回统一的错误对象，如 { ok: false, error: string }。

- generation.ts
  - 当前实现：runPipeline 有 try/catch，确保数据库连接在失败时关闭；getPipelineHistory 缺少显式捕获与最终释放。
  - 风险：历史查询在异常时未释放资源，且返回值可能不规范。
  - 改善建议：对 getPipelineHistory 增加 try/catch/finally，统一错误返回。

- tts.ts
  - 当前实现：testTTSConnection 未捕获异常。
  - 改善建议：统一返回布尔值并在 catch 中返回 false，同时记录日志。

- llm.ts
  - 当前实现：testLLMConnection、chatWithLLM 未捕获异常。
  - 改善建议：统一捕获异常，返回结构化错误或默认值，记录日志。

- 总体结论
  - 已实现的导出函数功能完整，但错误处理风格不统一，缺乏统一的返回结构与日志记录。
  - 建议统一为每个对外接口提供统一的错误对象/结果结构，并确保资源在异常路径也能正确释放。
