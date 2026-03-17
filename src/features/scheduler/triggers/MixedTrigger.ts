import type { Trigger, TriggerResult, TriggerConfig } from '../types.js';
import { ArticleRepository } from '../../../repositories/ArticleRepository.js';
import { DashScopeService } from '../../../services/llm/DashScopeService.js';
import type { Article } from '../../../repositories/ArticleRepository.js';

/**
 * 混合触发器实现
 * 
 * 结合定时、数量和 LLM 智能三种触发条件。
 * 当任意一个条件满足时触发流水线。
 */
export class MixedTrigger implements Trigger {
  private config: TriggerConfig;
  private articleRepo: ArticleRepository;
  private llmService: DashScopeService;

  /**
   * 创建 MixedTrigger 实例
   * 
   * @param config - 触发器配置，可包含 cron、threshold、llmEnabled 等字段
   * @param articleRepo - 文章仓库，用于查询未处理文章数量
   * @param llmService - LLM 服务，用于智能触发评估
   */
  constructor(
    config: TriggerConfig,
    articleRepo: ArticleRepository,
    llmService: DashScopeService,
  ) {
    this.config = config;
    this.articleRepo = articleRepo;
    this.llmService = llmService;
  }

  /**
   * 评估指定组是否应该触发流水线
   * 
   * 按顺序检查三种触发条件：
   * 1. 定时触发：检查当前时间是否匹配 Cron 表达式
   * 2. 数量触发：检查未处理文章数量是否达到阈值
   * 3. LLM 触发：使用 LLM 分析文章重要性
   * 
   * 任意一个条件满足即返回 triggered=true。
   * 
   * @param groupId - 要评估的组 ID
   * @returns Promise<TriggerResult> 包含触发状态、触发类型、原因和时间戳的结果对象
   */
  async evaluate(groupId: string): Promise<TriggerResult> {
    const now = new Date();
    const results: Array<{ type: string; triggered: boolean; reason: string }> = [];

    if (this.config.cron) {
      const timeResult = await this.evaluateTimeTrigger(now);
      results.push(timeResult);
      if (timeResult.triggered) {
        return {
          triggered: true,
          triggerType: 'mixed',
          reason: `Time trigger: ${timeResult.reason}`,
          timestamp: now,
        };
      }
    }

    if (this.config.threshold) {
      const countResult = this.evaluateCountTrigger(groupId);
      results.push(countResult);
      if (countResult.triggered) {
        return {
          triggered: true,
          triggerType: 'mixed',
          reason: `Count trigger: ${countResult.reason}`,
          timestamp: now,
        };
      }
    }

    if (this.config.llmEnabled) {
      const llmResult = await this.evaluateLLMTrigger(groupId);
      results.push(llmResult);
      if (llmResult.triggered) {
        return {
          triggered: true,
          triggerType: 'mixed',
          reason: `LLM trigger: ${llmResult.reason}`,
          timestamp: now,
        };
      }
    }

    const reasons = results.map(r => r.reason).join('; ');
    return {
      triggered: false,
      triggerType: 'mixed',
      reason: `All conditions not met: ${reasons}`,
      timestamp: now,
    };
  }

  /**
   * 评估定时触发条件
   */
  private async evaluateTimeTrigger(now: Date): Promise<{ type: string; triggered: boolean; reason: string }> {
    const cronExpression = this.config.cron;
    if (!cronExpression || typeof cronExpression !== 'string') {
      return { type: 'time', triggered: false, reason: 'No cron expression' };
    }

    const { validate, schedule } = await import('node-cron');
    const isValid = validate(cronExpression);
    if (!isValid) {
      return { type: 'time', triggered: false, reason: 'Invalid cron expression' };
    }

    const task = schedule(cronExpression, () => {}, { timezone: 'Asia/Shanghai' });
    task.stop();
    const nextRun = task.getNextRun();
    task.destroy();

    if (nextRun && Math.abs(now.getTime() - nextRun.getTime()) < 60000) {
      return { type: 'time', triggered: true, reason: `Cron matched at ${now.toISOString()}` };
    }

    return { type: 'time', triggered: false, reason: `Next at ${nextRun?.toISOString() ?? 'unknown'}` };
  }

  /**
   * 评估数量触发条件
   */
  private evaluateCountTrigger(groupId: string): { type: string; triggered: boolean; reason: string } {
    const threshold = this.config.threshold ?? 10;
    const count = this.articleRepo.countUnprocessed(groupId);
    const shouldTrigger = count >= threshold;

    return {
      type: 'count',
      triggered: shouldTrigger,
      reason: shouldTrigger
        ? `Count (${count}) >= threshold (${threshold})`
        : `Count (${count}) < threshold (${threshold})`,
    };
  }

  /**
   * 评估 LLM 触发条件
   */
  private async evaluateLLMTrigger(groupId: string): Promise<{ type: string; triggered: boolean; reason: string }> {
    const articles = await this.articleRepo.findUnprocessed(groupId, 10);

    if (articles.length === 0) {
      return { type: 'llm', triggered: false, reason: 'No unprocessed articles' };
    }

    const prompt = this.buildEvaluationPrompt(articles);
    const response = await this.llmService.generateSummary(prompt);
    const shouldTrigger = this.parseLLMResponse(response.content);

    return {
      type: 'llm',
      triggered: shouldTrigger,
      reason: shouldTrigger
        ? `LLM recommends: ${response.content}`
        : `LLM does not recommend: ${response.content}`,
    };
  }

  /**
   * 构建 LLM 评估提示
   */
  private buildEvaluationPrompt(articles: Article[]): string {
    const articleTitles = articles.map(article => `- ${article.title}`).join('\n');

    return `Evaluate if these ${articles.length} articles form a coherent topic worth a podcast episode:

${articleTitles}

Answer YES or NO with brief reasoning:`;
  }

  /**
   * 解析 LLM 响应
   */
  private parseLLMResponse(content: string): boolean {
    return content.toUpperCase().includes('YES');
  }
}
