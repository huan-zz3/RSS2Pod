import { loadConfig } from './shared/config/index.js';
import { DatabaseManager } from './infrastructure/database/DatabaseManager.js';
import { getEventBus } from './features/events/EventBus.js';
import { PipelineOrchestrator } from './features/pipeline/PipelineOrchestrator.js';
import { SchedulerService } from './features/scheduler/SchedulerService.js';
import { TriggerEvaluator } from './features/scheduler/TriggerEvaluator.js';
import { GroupRepository } from './repositories/GroupRepository.js';
import { ArticleRepository } from './repositories/ArticleRepository.js';
import { DashScopeService } from './services/llm/DashScopeService.js';
import pino from 'pino';

const logger = pino({
  name: 'rss2pod',
  timestamp: () => `,"time":"${new Date(new Date().getTime() + 8 * 3600 * 1000).toISOString().replace('Z', '+08:00')}"`,
});

async function main() {
  logger.info('Starting RSS2Pod...');
  
  const config = loadConfig();
  
  logger.level = config.logging.level;
  logger.info({ level: config.logging.level }, 'Logging configured');
  
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  
  const eventBus = getEventBus();
  
  eventBus.subscribeAll((event) => {
    logger.debug({ 
      eventId: event.id, 
      type: event.type,
      groupId: event.metadata?.groupId,
    }, 'Event received');
  });
  
  const db = dbManager.getDb();
  const groupRepo = new GroupRepository(db);
  const articleRepo = new ArticleRepository(db);
  const llmService = new DashScopeService(config.llm);
  
  const pipeline = new PipelineOrchestrator(dbManager, {
    maxConcurrentGroups: 3,
  });
  
  const evaluator = new TriggerEvaluator(articleRepo, llmService);
  
  const scheduler = new SchedulerService(
    groupRepo,
    pipeline,
    evaluator,
    eventBus,
    { checkInterval: 60, maxConcurrentGroups: 3 },
    config.sync,
    dbManager,
  );
  scheduler.start();
  
  logger.info(`Database initialized at ${config.database.path}`);
  logger.info('Scheduler started - checking triggers every 60 seconds');
  logger.info('RSS2Pod is ready');
  
  process.on('SIGINT', () => {
    logger.info('Shutting down...');
    scheduler.stop();
    dbManager.close();
    process.exit(0);
  });
  
  process.on('SIGTERM', () => {
    logger.info('Shutting down...');
    scheduler.stop();
    dbManager.close();
    process.exit(0);
  });
}

main().catch((error) => {
  logger.error({ error }, 'Failed to start RSS2Pod');
  process.exit(1);
});
