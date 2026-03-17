import type { Group } from '../../repositories/GroupRepository.js';
import type { ArticleRepository } from '../../repositories/ArticleRepository.js';
import type { DashScopeService } from '../../services/llm/DashScopeService.js';
import type { Trigger, TriggerResult } from './types.js';
import { CountTrigger } from './triggers/CountTrigger.js';
import { CronScheduler } from './triggers/CronScheduler.js';
import { LLMTrigger } from './triggers/LLMTrigger.js';
import { MixedTrigger } from './triggers/MixedTrigger.js';

/**
 * 触发器评估器工厂类
 * 根据组的触发器类型创建并返回相应的触发器实例
 * 支持四种触发器类型：time（定时）、count（数量）、llm（LLM 智能）、mixed（混合）
 */
export class TriggerEvaluator {
  private articleRepo: ArticleRepository;
  private llmService: DashScopeService;

  /**
   * 创建触发器评估器实例
   * @param articleRepo - 文章仓库，用于查询未处理文章数量
   * @param llmService - LLM 服务，用于智能触发评估
   */
  constructor(articleRepo: ArticleRepository, llmService: DashScopeService) {
    this.articleRepo = articleRepo;
    this.llmService = llmService;
  }

  /**
   * 根据组配置获取相应的触发器实例
   * @param group - 组对象，包含触发器类型和配置
   * @returns 触发器实例
   * @throws 当触发器类型未知时抛出错误
   */
  getTrigger(group: Group): Trigger {
    switch (group.triggerType) {
      case 'time': {
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
        return new CronScheduler(group.triggerConfig) as Trigger;
      }
      case 'count': {
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
        return new CountTrigger(group.triggerConfig, this.articleRepo) as Trigger;
      }
      case 'llm': {
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
        return new LLMTrigger(group.triggerConfig, this.articleRepo, this.llmService) as Trigger;
      }
      case 'mixed': {
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
        return new MixedTrigger(group.triggerConfig, this.articleRepo, this.llmService) as Trigger;
      }
      default: {
        // eslint-disable-next-line @typescript-eslint/no-unused-expressions
        group.triggerType satisfies never;
        throw new Error(`Unknown trigger type: ${group.triggerType}`);
      }
    }
  }

  /**
   * 评估组是否应该触发流水线
   * @param group - 组对象，包含触发器类型和配置
   * @returns 触发器评估结果
   */
  async evaluate(group: Group): Promise<TriggerResult> {
    const trigger = this.getTrigger(group);
    return trigger.evaluate(group.id);
  }
}
