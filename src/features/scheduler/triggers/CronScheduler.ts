import { CronExpressionParser } from 'cron-parser';
import type { Trigger, TriggerConfig, TriggerResult } from '../types.js';

export class CronScheduler implements Trigger {
  private readonly config: TriggerConfig;

  constructor(config: TriggerConfig) {
    this.config = config;
  }

  async evaluate(_groupId: string): Promise<TriggerResult> {
    const now = new Date();
    const cronExpression = this.config.cron;

    if (!cronExpression || typeof cronExpression !== 'string') {
      return {
        triggered: false,
        triggerType: 'time',
        reason: '未配置 Cron 表达式',
        timestamp: now,
      };
    }

    try {
      const interval = CronExpressionParser.parse(cronExpression, {
        currentDate: now,
        tz: 'Asia/Shanghai',
      });
      
      const prev = interval.prev().toDate();
      const timeDiff = now.getTime() - prev.getTime();
      const shouldTrigger = timeDiff < 60000;

      if (shouldTrigger) {
        return {
          triggered: true,
          triggerType: 'time',
          reason: `Cron 计划匹配成功：${now.toISOString()}`,
          timestamp: now,
        };
      }

      const next = interval.next().toDate();
      return {
        triggered: false,
        triggerType: 'time',
        reason: `下次执行时间：${next.toISOString()}`,
        timestamp: now,
      };
    } catch (error) {
      return {
        triggered: false,
        triggerType: 'time',
        reason: `Cron 表达式解析失败：${error instanceof Error ? error.message : String(error)}`,
        timestamp: now,
      };
    }
  }
}
