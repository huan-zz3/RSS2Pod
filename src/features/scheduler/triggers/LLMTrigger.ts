import { Trigger, TriggerResult, TriggerConfig } from '../types.js';
import { ArticleRepository } from '../../../repositories/ArticleRepository.js';
import { DashScopeService } from '../../../services/llm/DashScopeService.js';
import type { Article } from '../../../repositories/ArticleRepository.js';

export class LLMTrigger implements Trigger {
  private config: TriggerConfig;
  private articleRepo: ArticleRepository;
  private llmService: DashScopeService;

  constructor(
    config: TriggerConfig,
    articleRepo: ArticleRepository,
    llmService: DashScopeService,
  ) {
    this.config = config;
    this.articleRepo = articleRepo;
    this.llmService = llmService;
  }

  async evaluate(groupId: string): Promise<TriggerResult> {
    if (!this.config.llmEnabled) {
      return {
        triggered: false,
        triggerType: 'llm',
        reason: 'LLM trigger is disabled',
        timestamp: new Date(),
      };
    }

    const articles = await this.articleRepo.findUnprocessed(groupId, 10);
    
    if (articles.length === 0) {
      return {
        triggered: false,
        triggerType: 'llm',
        reason: 'No unprocessed articles',
        timestamp: new Date(),
      };
    }

    const prompt = this.buildEvaluationPrompt(articles);
    const response = await this.llmService.generateSummary(prompt);

    const shouldTrigger = this.parseLLMResponse(response.content);

    return {
      triggered: shouldTrigger,
      triggerType: 'llm',
      reason: shouldTrigger
        ? `LLM recommends generation: ${response.content}`
        : `LLM does not recommend generation: ${response.content}`,
      timestamp: new Date(),
    };
  }

  private buildEvaluationPrompt(articles: Article[]): string {
    const articleTitles = articles.map(article => `- ${article.title}`).join('\n');
    
    return `Evaluate if these ${articles.length} articles form a coherent topic worth a podcast episode:

${articleTitles}

Answer YES or NO with brief reasoning:`;
  }

  private parseLLMResponse(content: string): boolean {
    return content.toUpperCase().includes('YES');
  }
}
