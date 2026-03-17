/**
 * Scheduler types for RSS2Pod
 */

/**
 * 触发器配置接口，与 GroupRepository 中的数据库模式匹配
 * 定义组的触发条件，包括定时、数量和 LLM 触发
 */
export interface TriggerConfig {
  cron?: string;
  threshold?: number;
  llmEnabled?: boolean;
  [key: string]: unknown;
}

/**
 * 触发器评估结果接口
 * 所有触发器实现（CronScheduler、CountTrigger、LLMTrigger）都使用此接口返回评估结果
 */
export interface TriggerResult {
  triggered: boolean;
  triggerType: TriggerType;
  reason?: string;
  timestamp: Date;
}

/**
 * 触发器类型联合类型
 * 定义系统支持的触发器类型
 */
export type TriggerType = 'time' | 'count' | 'llm' | 'mixed';

/**
 * 触发器接口，所有触发器实现必须遵循此接口
 * 用于评估指定组是否应该触发流水线
 */
export interface Trigger {
  evaluate(groupId: string): Promise<TriggerResult>;
}

/**
 * 调度器配置接口
 * 定义调度器的全局配置选项
 */
export interface SchedulerConfig {
  checkInterval: number;
  maxConcurrentGroups: number;
}
