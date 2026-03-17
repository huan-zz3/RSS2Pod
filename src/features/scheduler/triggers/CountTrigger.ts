import type { Trigger, TriggerResult, TriggerConfig } from '../types.js';
import { ArticleRepository } from '../../../repositories/ArticleRepository.js';

/**
 * 基于文章数量的触发器实现
 * 
 * 当指定组的未处理文章数量达到配置的阈值时触发流水线。
 * 适用于希望累积一定数量文章后批量处理的场景。
 */
export class CountTrigger implements Trigger {
  private config: TriggerConfig;
  private articleRepo: ArticleRepository;

  /**
   * 创建 CountTrigger 实例
   * 
   * @param config - 触发器配置，必须包含 threshold 字段
   * @param articleRepo - 文章仓库，用于查询未处理文章数量
   */
  constructor(config: TriggerConfig, articleRepo: ArticleRepository) {
    this.config = config;
    this.articleRepo = articleRepo;
  }

  /**
   * 评估指定组是否应该触发流水线
   * 
   * 查询该组的未处理文章数量，当数量达到或超过配置的阈值时返回 triggered=true。
   * 
   * @param groupId - 要评估的组 ID
   * @returns Promise<TriggerResult> 包含触发状态、触发类型、原因和时间戳的结果对象
   * 
   * @example
   * ```typescript
   * const trigger = new CountTrigger({ threshold: 10 }, articleRepo);
   * const result = await trigger.evaluate('group-123');
   * if (result.triggered) {
   *   console.log(result.reason); // "Article count (15) reached threshold (10)"
   * }
   * ```
   */
  async evaluate(groupId: string): Promise<TriggerResult> {
    const threshold = this.config.threshold ?? 10;
    const count = this.articleRepo.countUnprocessed(groupId);

    const shouldTrigger = count >= threshold;

    return {
      triggered: shouldTrigger,
      triggerType: 'count',
      reason: shouldTrigger
        ? `Article count (${count}) reached threshold (${threshold})`
        : `Article count (${count}) below threshold (${threshold})`,
      timestamp: new Date(),
    };
  }
}
