# TUI 命令处理器返回数据格式对照

以下整理了 src/tui/commands 下各命令模块暴露的返回数据结构、字段及示例数据，便于后续实现统一的返回风格与错误处理。

1) 系统状态（system.ts）
- 导出函数：getSystemStats(): Promise<SystemStats>
- SystemStats 接口字段：
  - version: string
  - database: string
  - fever: string
  - llm: string
  - tts: string
  - groups: number
  - articles: number
  - episodes: number
- 实际返回的数据格式示例：
  {
    version: "3.0.0",
    database: "/path/to/rss2pod.db",
    fever: "https://fever.example",
    llm: "dashscope/Model-1",
    tts: "siliconflow/Voice-1",
    groups: 5,
    articles: 123,
    episodes: 12
  }

2) 组管理（groups.ts）
- 导出函数：
  - listGroups(): Promise<GroupInfo[]>
  - getGroup(id: string): Promise<GroupInfo | null>
  - createGroup(name: string, options: { description?: string; sourceIds?: string[]; triggerType?: string }): Promise<string>
  - deleteGroup(id: string): Promise<void>
- GroupInfo 字段：
  - id: string
  - name: string
  - description?: string
  - enabled: boolean
  - triggerType: string
  - sourceCount: number
- 示例（listGroups）：
  [
    { id: "grp-1", name: "科技新闻", description: "", enabled: true, triggerType: "time", sourceCount: 3 },
    ...
  ]
- 示例（getGroup）返回单条 GroupInfo
  { id: "grp-1", name: "科技新闻", description: "", enabled: true, triggerType: "time", sourceCount: 3 }

3) Fever 相关（fever.ts）
- 导出函数：
  - testFeverConnection(): Promise<boolean>
  - listFeeds(): Promise<FeedInfo[]>
  - listFeverGroups(): Promise<GroupInfo[]>
  - syncFeeds(): Promise<number>
- FeedInfo 字段：
  - id: number
  - title: string
  - url: string
  - siteUrl: string
- Fever GroupInfo 字段（简化版本，用于表示 Fever 的分组信息）
  - id: number
  - title: string
- 示例（listFeeds）
  [ { id: 1, title: "BBC News", url: "https://example.com/rss", siteUrl: "https://bbc.co.uk" }, ... ]

4) 生产流水线（generation.ts）
- 导出函数：
  - runPipeline(groupId: string): Promise<PipelineRun>
  - getPipelineHistory(limit?: number): Promise<PipelineHistory[]>
- PipelineRun 字段：
  - id: string
  - groupId: string
  - status: string
  - articlesCount: number
  - error?: string
- PipelineHistory 字段：
  - id: string
  - groupId: string
  - status: string
  - articlesCount: number
  - createdAt: Date
- 示例（runPipeline）
  { id: "run-1", groupId: "grp-1", status: "success", articlesCount: 12 }
- 示例（getPipelineHistory）
  [ { id: "run-1", groupId: "grp-1", status: "success", articlesCount: 12, createdAt: new Date() }, ... ]

5) TTS 调试（tts.ts）
- 导出函数：testTTSConnection(): Promise<boolean>
- 返回示例：true/false 表示连接测试结果

6) LLM 调试与对话（llm.ts）
- 导出函数：
  - testLLMConnection(): Promise<boolean>
  - chatWithLLM(prompt: string): Promise<string>
- 返回示例：
  - testLLMConnection：true/false
  - chatWithLLM：返回文本对话结果

备注：以上返回类型均在各自模块的 TypeScript 接口中定义，实际返回值应保持字段名与类型的一致性，方便 UI 层展示与错误处理扩展。
