import { loadConfig } from './shared/config/index.js';
import { DatabaseManager } from './infrastructure/database/DatabaseManager.js';
import { getEventBus } from './features/events/EventBus.js';
import pino from 'pino';

const logger = pino({ name: 'rss2pod' });

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
  
  logger.info(`Database initialized at ${config.database.path}`);
  logger.info('RSS2Pod is ready');
  
  process.on('SIGINT', () => {
    logger.info('Shutting down...');
    dbManager.close();
    process.exit(0);
  });
}

main().catch((error) => {
  logger.error({ error }, 'Failed to start RSS2Pod');
  process.exit(1);
});
