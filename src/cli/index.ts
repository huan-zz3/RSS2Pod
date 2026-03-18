#!/usr/bin/env node

import { Command } from 'commander';
import { join } from 'path';
import { readFileSync, existsSync } from 'fs';
import { loadConfig, saveConfig, createConfigTemplate } from '../shared/config/index.js';
import { DatabaseManager } from '../infrastructure/database/DatabaseManager.js';
import { FeverClient } from '../infrastructure/external/FeverClient.js';
import { PipelineOrchestrator } from '../features/pipeline/PipelineOrchestrator.js';
import { GroupRepository } from '../repositories/GroupRepository.js';
import type { Group } from '../repositories/GroupRepository.js';
import { ArticleRepository } from '../repositories/ArticleRepository.js';
import { TriggerEvaluator } from '../features/scheduler/TriggerEvaluator.js';
import { SchedulerService } from '../features/scheduler/SchedulerService.js';
import { SyncService } from '../features/sync/SyncService.js';
import { getEventBus } from '../features/events/EventBus.js';
import pino from 'pino';

const logger = pino({
  name: 'cli',
  timestamp: () => `,"time":"${new Date(new Date().getTime() + 8 * 3600 * 1000).toISOString().replace('Z', '+08:00')}"`,
});

const pkgPath = join(process.cwd(), 'package.json');
const pkg = existsSync(pkgPath) 
  ? JSON.parse(readFileSync(pkgPath, 'utf-8'))
  : { name: 'rss2pod', version: '3.0.0' };

const program = new Command();

program
  .name(pkg.name)
  .version(pkg.version)
  .description('RSS to Podcast Converter with AI Enhancement');

program
  .command('init')
  .description('Create configuration template')
  .action(() => {
    createConfigTemplate();
    logger.info('Configuration template created. Edit config.json with your API keys.');
  });

program
  .command('db:init')
  .description('Initialize the database')
  .action(() => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    logger.info(`Database initialized at ${config.database.path}`);
    dbManager.close();
  });

program
  .command('db:stats')
  .description('Show database statistics')
  .action(() => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const articles = db.prepare('SELECT COUNT(*) as count FROM articles').get() as { count: number };
    const groups = db.prepare('SELECT COUNT(*) as count FROM groups').get() as { count: number };
    const episodes = db.prepare('SELECT COUNT(*) as count FROM episodes').get() as { count: number };
    const summaries = db.prepare('SELECT COUNT(*) as count FROM source_summaries').get() as { count: number };
    
    console.table({
      articles: articles.count,
      groups: groups.count,
      episodes: episodes.count,
      summaries: summaries.count,
    });
    
    dbManager.close();
  });

program
  .command('status')
  .description('Show system status')
  .action(async () => {
    const config = loadConfig();
    
    const status = {
      version: pkg.version,
      database: config.database.path,
      fever: config.fever.baseUrl,
      llm: `${config.llm.provider}/${config.llm.model}`,
      tts: `${config.tts.provider}/${config.tts.model}`,
    };
    
    console.log('System Status:');
    console.table(status);
    
    const dbManager = new DatabaseManager(config.database.path);
    try {
      dbManager.initialize();
      const db = dbManager.getDb();
      const groups = db.prepare('SELECT COUNT(*) as count FROM groups WHERE enabled = 1').get() as { count: number };
      const articles = db.prepare('SELECT COUNT(*) as count FROM articles').get() as { count: number };
      const episodes = db.prepare('SELECT COUNT(*) as count FROM episodes').get() as { count: number };
      
      console.log('\nStatistics:');
      console.table({
        'Enabled Groups': groups.count,
        Articles: articles.count,
        Episodes: episodes.count,
      });
      
      dbManager.close();
    } catch {
      logger.warn('Database not initialized');
    }
  });

program
  .command('config:show')
  .description('Show current configuration (without secrets)')
  .action(() => {
    const config = loadConfig();
    
    const safeConfig = {
      ...config,
      fever: { ...config.fever, password: '***' },
      llm: { ...config.llm, apiKey: '***' },
      tts: { ...config.tts, apiKey: '***' },
    };
    
    console.log(JSON.stringify(safeConfig, null, 2));
  });

program
  .command('config:set <key> <value>')
  .description('Set configuration value')
  .action((key, value) => {
    const config = loadConfig();
    const keys = key.split('.');
    
    if (keys.length !== 2) {
      logger.error('Invalid key format. Use: section.key (e.g., logging.level)');
      process.exit(1);
    }
    
    const [section, k] = keys;
    const sectionConfig = (config as any)[section];
    
    if (!sectionConfig) {
      logger.error(`Section not found: ${section}`);
      process.exit(1);
    }
    
    if (!(k in sectionConfig)) {
      logger.error(`Key not found: ${key}`);
      process.exit(1);
    }
    
    const oldValue = sectionConfig[k];
    sectionConfig[k] = typeof oldValue === 'number' ? Number(value) : value;
    
    saveConfig(config);
    logger.info(`Configuration updated: ${key} = ${value}`);
  });

program
  .command('config:validate')
  .description('Validate configuration file with Zod schema')
  .action(() => {
    try {
      loadConfig();
      logger.info('Configuration is valid');
    } catch (error) {
      if (error instanceof Error) {
        logger.error(`Configuration validation failed: ${error.message}`);
      } else {
        logger.error('Configuration validation failed');
      }
      process.exit(1);
    }
  });

program
  .command('group:list')
  .description('List all groups')
  .option('-e, --enabled', 'Show only enabled groups')
  .action((options) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    
    const groups = groupRepo.findAll({ enabledOnly: options.enabled });
    
    if (groups.length === 0) {
      logger.info('No groups found');
    } else {
      console.table(groups.map(g => ({
        ID: g.id,
        Name: g.name,
        Enabled: g.enabled ? 'Yes' : 'No',
        Trigger: g.triggerType,
        Sources: g.sourceIds.length,
      })));
    }
    
    dbManager.close();
  });

function resolveGroupId(id: string, db: any): string | null {
  const index = parseInt(id, 10);
  if (!isNaN(index)) {
    const groups = db.prepare('SELECT id FROM groups ORDER BY created_at').all() as Array<{ id: string }>;
    if (index >= 0 && index < groups.length) {
      const group = groups[index];
      if (group) {
        return group.id;
      }
    }
  }
  const group = db.prepare('SELECT id FROM groups WHERE id = ?').get(id) as { id: string } | undefined;
  return group ? group.id : null;
}

program
  .command('group:show <id>')
  .description('Show group details (supports index or ID)')
  .action((id) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    
    const resolvedId = resolveGroupId(id, db);
    if (!resolvedId) {
      logger.error(`Group not found: ${id}`);
      dbManager.close();
      process.exit(1);
    }
    
    const group = groupRepo.findById(resolvedId);
    if (!group) {
      logger.error(`Group not found: ${id}`);
      dbManager.close();
      process.exit(1);
    }
    
    console.log('Group Details:');
    console.log(`  ID: ${group.id} (index: ${id})`);
    console.log(`  Name: ${group.name}`);
    console.log(`  Description: ${group.description || 'None'}`);
    console.log(`  Enabled: ${group.enabled ? 'Yes' : 'No'}`);
    console.log(`  Trigger: ${group.triggerType}`);
    console.log(`  Source IDs: ${group.sourceIds.join(', ')}`);
    console.log(`  Podcast Structure: ${group.podcastStructure.type}`);
    console.log(`  Learning Mode: ${group.learningMode}`);
    console.log(`  Retention Days: ${group.retentionDays}`);
    
    dbManager.close();
  });

program
  .command('group:create <name>')
  .description('Create a new group')
  .option('-d, --description <text>', 'Group description')
  .option('-s, --sources <ids>', 'Comma-separated source IDs')
  .option('-t, --type <type>', 'Podcast type: single or dual', 'single')
  .option('--learning-mode <mode>', 'English learning mode: normal, word_explanation, sentence_translation', 'normal')
  .action((name, options) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    
    const validModes = ['normal', 'word_explanation', 'sentence_translation'] as const;
    if (!validModes.includes(options.learningMode as any)) {
      logger.error(`Invalid learning mode: ${options.learningMode}. Valid: ${validModes.join(', ')}`);
      dbManager.close();
      process.exit(1);
    }
    
    const group = {
      id: `grp-${Date.now()}`,
      name,
      description: options.description,
      sourceIds: options.sources ? options.sources.split(',') : [],
      enabled: true,
      triggerType: 'time' as const,
      triggerConfig: { cron: '0 9 * * *' },
      podcastStructure: { type: options.type as 'single' | 'dual' },
      learningMode: options.learningMode as 'normal' | 'word_explanation' | 'sentence_translation',
      retentionDays: 30,
      lastSyncedMaxId: 0,
    };
    
    groupRepo.create(group);
    logger.info(`Group created: ${name} (${group.id})`);
    
    dbManager.close();
  });

program
  .command('group:edit <id>')
  .description('Edit group configuration (supports index or ID)')
  .option('-n, --name <name>', 'New name')
  .option('-d, --description <text>', 'New description')
  .option('-s, --sources <ids>', 'New source IDs (comma-separated)')
  .option('-t, --trigger-type <type>', 'Trigger type: time, count, llm, mixed')
  .option('-c, --trigger-cron <cron>', 'Cron expression (for time trigger)')
  .option('--threshold <number>', 'Article threshold (for count trigger)')
  .option('--llm-enabled <boolean>', 'Enable LLM trigger (true/false)')
  .option('--learning-mode <mode>', 'English learning mode: normal, word_explanation, sentence_translation')
  .action(async (id, options) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    
    const resolvedId = resolveGroupId(id, db);
    if (!resolvedId) {
      logger.error(`Group not found: ${id}`);
      dbManager.close();
      process.exit(1);
    }
    
    const group = groupRepo.findById(resolvedId);
    
    if (!group) {
      logger.error(`Group not found: ${id}`);
      dbManager.close();
      process.exit(1);
    }
    
    if (options.name) group.name = options.name;
    if (options.description !== undefined) group.description = options.description;
    if (options.sources) group.sourceIds = options.sources.split(',');
    
    if (options.threshold) {
      const threshold = parseInt(options.threshold, 10);
      if (isNaN(threshold) || threshold <= 0) {
        logger.error('Threshold must be a positive number');
        dbManager.close();
        process.exit(1);
      }
    }
    
    if (options.triggerType) {
      const validTriggerTypes = ['time', 'count', 'llm', 'mixed'] as const;
      if (!validTriggerTypes.includes(options.triggerType as any)) {
        logger.error(`Invalid trigger type: ${options.triggerType}. Valid: ${validTriggerTypes.join(', ')}`);
        dbManager.close();
        process.exit(1);
      }
      group.triggerType = options.triggerType as 'time' | 'count' | 'llm' | 'mixed';
    }

    if (options.triggerCron || options.threshold || options.llmEnabled !== undefined) {
      group.triggerConfig = {
        ...group.triggerConfig,
        ...(options.triggerCron ? { cron: options.triggerCron } : {}),
        ...(options.threshold ? { threshold: parseInt(options.threshold, 10) } : {}),
        ...(options.llmEnabled !== undefined ? { llmEnabled: options.llmEnabled === 'true' } : {}),
      };
    }
    
    if (options.learningMode) {
      const validModes = ['normal', 'word_explanation', 'sentence_translation'] as const;
      if (!validModes.includes(options.learningMode as any)) {
        logger.error(`Invalid learning mode: ${options.learningMode}. Valid: ${validModes.join(', ')}`);
        dbManager.close();
        process.exit(1);
      }
      group.learningMode = options.learningMode as 'normal' | 'word_explanation' | 'sentence_translation';
    }
    
    groupRepo.update(group);
    logger.info(`Group updated: ${group.name}`);
    
    dbManager.close();
  });

program
  .command('group:delete <id>')
  .description('Delete a group (supports index or ID)')
  .action(async (id) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    
    const resolvedId = resolveGroupId(id, db);
    if (!resolvedId) {
      logger.error(`Group not found: ${id}`);
      dbManager.close();
      process.exit(1);
    }
    
    const group = groupRepo.findById(resolvedId);
    
    if (!group) {
      logger.error(`Group not found: ${id}`);
      dbManager.close();
      process.exit(1);
    }
    
    const mediaDir = join(process.cwd(), 'data', 'media', resolvedId);
    if (existsSync(mediaDir)) {
      const { rmSync } = await import('fs');
      rmSync(mediaDir, { recursive: true, force: true });
      logger.info(`Media files deleted: ${mediaDir}`);
    }
    
    const feedFile = join(process.cwd(), 'data', 'media', 'feeds', `${resolvedId}.xml`);
    if (existsSync(feedFile)) {
      const { rmSync } = await import('fs');
      rmSync(feedFile, { force: true });
      logger.info(`Feed file deleted: ${feedFile}`);
    }
    
    groupRepo.delete(resolvedId);
    logger.info(`Group deleted: ${group.name}`);
    
    dbManager.close();
  });

program
  .command('group:enable <id>')
  .description('Enable a group (supports index or ID)')
  .action((id) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    
    const resolvedId = resolveGroupId(id, db);
    if (!resolvedId) {
      logger.error(`Group not found: ${id}`);
      dbManager.close();
      process.exit(1);
    }
    
    groupRepo.enable(resolvedId);
    logger.info(`Group enabled: ${id}`);
    
    dbManager.close();
  });

program
  .command('group:disable <id>')
  .description('Disable a group (supports index or ID)')
  .action((id) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    
    const resolvedId = resolveGroupId(id, db);
    if (!resolvedId) {
      logger.error(`Group not found: ${id}`);
      dbManager.close();
      process.exit(1);
    }
    
    groupRepo.disable(resolvedId);
    logger.info(`Group disabled: ${id}`);
    
    dbManager.close();
  });

program
  .command('source:list')
  .description('List all feeds')
  .action(async () => {
    const config = loadConfig();
    const client = new FeverClient(config.fever);
    
    const feeds = await client.getFeeds();
    
    console.log(`Found ${feeds.length} feeds:`);
    console.table(feeds.map(f => ({
      ID: f.id,
      Name: f.title,
      URL: f.url,
    })).slice(0, 50));
    
    if (feeds.length > 50) {
      logger.info(`... and ${feeds.length - 50} more feeds`);
    }
  });

program
  .command('source:show <id>')
  .description('Show feed details')
  .action(async (id) => {
    const config = loadConfig();
    const client = new FeverClient(config.fever);
    
    const feeds = await client.getFeeds();
    const feed = feeds.find(f => f.id.toString() === id);
    
    if (!feed) {
      logger.error(`Feed not found: ${id}`);
      process.exit(1);
    }
    
    console.log('Feed Details:');
    console.log(`  ID: ${feed.id}`);
    console.log(`  Name: ${feed.title}`);
    console.log(`  URL: ${feed.url}`);
    console.log(`  Website: ${feed.siteUrl}`);
  });

program
  .command('fever:test')
  .description('Test Fever API connection')
  .action(async () => {
    const config = loadConfig();
    
    if (!config.fever.baseUrl) {
      logger.error('Fever API URL not configured');
      process.exit(1);
    }
    
    const client = new FeverClient(config.fever);
    const isConnected = await client.testAuth();
    
    if (isConnected) {
      logger.info('Fever API connection successful');
      
      const feeds = await client.getFeeds();
      logger.info(`Found ${feeds.length} feeds`);
      
      const groups = await client.getGroups();
      logger.info(`Found ${groups.length} groups`);
    } else {
      logger.error('Fever API connection failed');
      process.exit(1);
    }
  });

program
  .command('fever:sync-feeds')
  .description('Sync feed list')
  .action(async () => {
    const config = loadConfig();
    const client = new FeverClient(config.fever);
    
    logger.info('Syncing feeds...');
    const feeds = await client.getFeeds();
    logger.info(`Sync complete: ${feeds.length} feeds`);
    
    console.table(feeds.slice(0, 20).map(f => ({
      ID: f.id,
      Name: f.title,
    })));
  });

program
  .command('fever:cache-articles')
  .description('Cache articles to local database')
  .option('-l, --limit <number>', 'Maximum articles', '100')
  .action(async (options) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const client = new FeverClient(config.fever);
    const articleRepo = new ArticleRepository(dbManager.getDb());
    
    logger.info('Fetching articles...');
    const articles = await client.getItems();
    
    let count = 0;
    for (const item of articles.slice(0, Number(options.limit))) {
      articleRepo.insert({
        id: `art-${item.id}`,
        feverId: item.id,
        title: item.title,
        content: item.html.replace(/<[^>]*>/g, '').trim(),
        sourceId: item.feedId.toString(),
        sourceName: item.feedId.toString(),
        publishedAt: item.createdOn,
        fetchedAt: new Date(),
        isRead: item.isRead,
        isSaved: item.isSaved,
        processedByGroup: [],
      });
      count++;
    }
    
    logger.info(`Cached ${count} articles`);
    
    dbManager.close();
  });

program
  .command('sync:run [groupId]')
  .description('Manually trigger article sync (optionally for specific group) (supports index or ID)')
  .action(async (groupId) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const syncService = new SyncService(
      new GroupRepository(db),
      new ArticleRepository(db),
      new FeverClient(config.fever),
      getEventBus(),
      config.sync,
    );
    
    try {
      if (groupId) {
        const resolvedId = resolveGroupId(groupId, db);
        
        if (!resolvedId) {
          logger.error(`Group not found: ${groupId}`);
          dbManager.close();
          process.exit(1);
        }
        
        const groupRepo = new GroupRepository(db);
        const group = groupRepo.findById(resolvedId);
        if (!group) {
          logger.error(`Group not found: ${groupId}`);
          dbManager.close();
          process.exit(1);
        }
        
        logger.info(`Syncing articles for group: ${group.name}`);
        const result = await syncService.syncGroup(group);
        
        if (result.synced) {
          logger.info(`✅ Sync completed: ${result.articlesSynced} articles in ${result.duration}ms (maxId: ${result.maxId})`);
        } else {
          logger.error(`❌ Sync failed`);
          process.exit(1);
        }
      } else {
        logger.info('Syncing all articles...');
        await syncService.syncAllGroups();
        logger.info('✅ Sync completed');
      }
    } catch (error) {
      logger.error(`❌ Sync failed: ${error instanceof Error ? error.message : String(error)}`);
      process.exit(1);
    } finally {
      dbManager.close();
    }
  });

program
  .command('sync:status')
  .description('Show sync service status and configuration')
  .action(() => {
    const config = loadConfig();
    
    console.log('\n📋 Sync Configuration:');
    console.table({
      'Enabled': config.sync.enabled,
      'Interval (seconds)': config.sync.interval,
      'Max Articles per Sync': config.sync.maxArticlesPerSync,
    });
    
    console.log('\n💡 Tip: Use "scheduler:start" to start automatic sync');
    console.log('   Use "sync:run" to manually trigger sync');
  });

program
  .command('llm:test')
  .description('Test LLM connection')
  .action(async () => {
    const config = loadConfig();
    const { DashScopeService } = await import('../services/llm/DashScopeService.js');
    
    const service = new DashScopeService(config.llm);
    
    logger.info('Testing LLM connection...');
    const result = await service.testConnection();
    
    if (result) {
      logger.info('LLM connection successful');
      
      const response = await service.generateSummary('Test text', { style: 'balanced' });
      logger.info(`Test response length: ${response.content.length} chars`);
    } else {
      logger.error('LLM connection failed');
      process.exit(1);
    }
  });

program
  .command('llm:chat <prompt>')
  .description('Chat with LLM for testing')
  .action(async (prompt) => {
    const config = loadConfig();
    const { DashScopeService } = await import('../services/llm/DashScopeService.js');
    
    const service = new DashScopeService(config.llm);
    
    logger.info('Sending prompt...');
    const response = await service.generateScript(prompt);
    
    console.log('\nLLM Response:');
    console.log(response.content);
  });

program
  .command('tts:test')
  .description('Test TTS connection')
  .action(async () => {
    const config = loadConfig();
    const { SiliconFlowService } = await import('../services/tts/SiliconFlowService.js');
    
    const service = new SiliconFlowService(config.tts);
    
    logger.info('Testing TTS connection...');
    const result = await service.testConnection();
    
    if (result) {
      logger.info('TTS connection successful');
    } else {
      logger.error('TTS connection failed');
      process.exit(1);
    }
  });

program
  .command('generate:run <groupId>')
  .description('Run generation pipeline for a group (supports index or ID)')
  .action(async (groupId) => {
    const config = loadConfig();
    
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const resolvedId = resolveGroupId(groupId, db);
    
    if (!resolvedId) {
      logger.error(`Group not found: ${groupId}`);
      dbManager.close();
      process.exit(1);
    }
    
    const orchestrator = new PipelineOrchestrator(dbManager, {
      maxConcurrentGroups: config.scheduler.maxConcurrentGroups,
    });
    
    logger.info(`Starting pipeline for group: ${resolvedId}`);
    
    try {
      const run = await orchestrator.runForGroup(resolvedId);
      logger.info({ 
        runId: run.id, 
        status: run.status,
        articlesCount: run.articlesCount,
      }, 'Pipeline completed');
    } catch (error) {
      logger.error({ error }, 'Pipeline failed');
      process.exit(1);
    } finally {
      dbManager.close();
    }
  });

program
  .command('generate:history')
  .description('Show generation history')
  .action(() => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const runs = db.prepare(`
      SELECT * FROM pipeline_runs 
      ORDER BY created_at DESC 
      LIMIT 20
    `).all() as Array<{
      id: string;
      group_id: string;
      status: string;
      articles_count: number;
      created_at: number;
    }>;
    
    if (runs.length === 0) {
      logger.info('No generation history');
    } else {
      console.table(runs.map(r => ({
        ID: r.id,
        'Group ID': r.group_id,
        Status: r.status,
        Articles: r.articles_count,
        Time: new Date(r.created_at * 1000).toLocaleString(),
      })));
    }
    
    dbManager.close();
  });

program
  .command('pipeline:runs <groupId>')
  .description('View pipeline execution history for a group (supports index or ID)')
  .option('-l, --limit <number>', 'Maximum runs to show', '20')
  .action((groupId, options) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const resolvedId = resolveGroupId(groupId, db);
    
    if (!resolvedId) {
      logger.error(`Group not found: ${groupId}`);
      dbManager.close();
      process.exit(1);
    }
    
    const runs = db.prepare(`
      SELECT * FROM pipeline_runs 
      WHERE group_id = ?
      ORDER BY created_at DESC 
      LIMIT ?
    `).all(resolvedId, Number(options.limit)) as Array<{
      id: string;
      group_id: string;
      status: string;
      started_at: number | null;
      completed_at: number | null;
      stages: string | null;
      articles_count: number;
      error: string | null;
      created_at: number;
    }>;
    
    if (runs.length === 0) {
      logger.info('No pipeline runs found for this group');
    } else {
      console.table(runs.map(r => ({
        ID: r.id,
        'Group ID': r.group_id,
        Status: r.status,
        Articles: r.articles_count,
        Started: r.started_at ? new Date(r.started_at * 1000).toLocaleString() : 'N/A',
        Completed: r.completed_at ? new Date(r.completed_at * 1000).toLocaleString() : 'N/A',
      })));
    }
    
    dbManager.close();
  });

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

program
  .command('episode:list <groupId>')
  .description('List generated podcast episodes for a group (supports index or ID)')
  .option('-l, --limit <number>', 'Maximum episodes to show', '20')
  .action((groupId, options) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const resolvedId = resolveGroupId(groupId, db);
    
    if (!resolvedId) {
      logger.error(`Group not found: ${groupId}`);
      dbManager.close();
      process.exit(1);
    }
    
    const episodes = db.prepare(`
      SELECT * FROM episodes 
      WHERE group_id = ? 
      ORDER BY pub_date DESC 
      LIMIT ?
    `).all(resolvedId, Number(options.limit)) as Array<{
      id: string;
      group_id: string;
      title: string;
      audio_path: string | null;
      duration_seconds: number | null;
      pub_date: number;
      starred: number;
      created_at: number;
    }>;
    
    if (episodes.length === 0) {
      logger.info('No episodes found for this group');
    } else {
      console.table(episodes.map(e => ({
        ID: e.id,
        Title: e.title,
        Duration: e.duration_seconds ? formatDuration(e.duration_seconds) : 'N/A',
        Published: new Date(e.pub_date * 1000).toLocaleString(),
        Starred: e.starred ? 'Yes' : 'No',
      })));
    }
    
    dbManager.close();
  });

program
  .command('trigger:status <groupId>')
  .description('Show trigger status for a group (supports index or ID)')
  .action((groupId) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    
    const resolvedId = resolveGroupId(groupId, db);
    if (!resolvedId) {
      logger.error(`Group not found: ${groupId}`);
      dbManager.close();
      process.exit(1);
    }
    
    const group = groupRepo.findById(resolvedId);
    
    if (!group) {
      logger.error(`Group not found: ${groupId}`);
      dbManager.close();
      process.exit(1);
    }
    
    console.log('Trigger Status:');
    console.log(`  Type: ${group.triggerType}`);
    console.log(`  Config: ${JSON.stringify(group.triggerConfig)}`);
    
    const articleRepo = new ArticleRepository(db);
    const unprocessed = articleRepo.countUnprocessed(groupId);
    console.log(`  Unprocessed Articles: ${unprocessed}`);
    
    dbManager.close();
  });

program
  .command('article:unprocessed <groupId>')
  .description('List unprocessed articles for a group (supports index or ID)')
  .option('-l, --limit <number>', 'Maximum articles to show', '50')
  .action((groupId, options) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const resolvedId = resolveGroupId(groupId, db);
    
    if (!resolvedId) {
      logger.error(`Group not found: ${groupId}`);
      dbManager.close();
      process.exit(1);
    }
    
    const articleRepo = new ArticleRepository(db);
    const count = articleRepo.countUnprocessed(resolvedId);
    const articles = articleRepo.findUnprocessed(resolvedId, Number(options.limit));
    
    logger.info(`Total unprocessed articles: ${count}`);
    
    if (articles.length === 0) {
      logger.info('No unprocessed articles found');
    } else {
      console.table(articles.map(a => ({
        ID: a.id,
        'Fever ID': a.feverId,
        Title: a.title,
        Source: a.sourceName || 'Unknown',
        Published: new Date(a.publishedAt).toLocaleString(),
      })));
    }
    
    dbManager.close();
  });

program
  .command('article:mark-read <groupId>')
  .description('Mark all cached articles as processed for a group (supports index or ID)')
  .action((groupId) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const resolvedId = resolveGroupId(groupId, db);
    
    if (!resolvedId) {
      logger.error(`Group not found: ${groupId}`);
      dbManager.close();
      process.exit(1);
    }
    
    const group = db.prepare('SELECT * FROM groups WHERE id = ?').get(resolvedId) as Group | undefined;
    if (!group) {
      logger.error(`Group not found: ${groupId}`);
      dbManager.close();
      process.exit(1);
    }
    
    const articleRepo = new ArticleRepository(db);
    const updatedCount = articleRepo.markAllAsProcessed(resolvedId);
    
    if (updatedCount === 0) {
      logger.info('No cached articles found for this group');
      dbManager.close();
      return;
    }
    
    logger.info(`✅ Successfully marked ${updatedCount} articles as processed for group: ${group.name}`);
    logger.info('💡 Tip: Run "sync:run" to fetch latest unread articles from Fever API');
    
    dbManager.close();
  });

program
  .command('trigger:check <groupId>')
  .description('Check if trigger conditions are met for a group (supports index or ID)')
  .action(async (groupId) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    
    const resolvedId = resolveGroupId(groupId, db);
    if (!resolvedId) {
      logger.error(`Group not found: ${groupId}`);
      dbManager.close();
      process.exit(1);
    }
    
    const group = groupRepo.findById(resolvedId);
    
    if (!group) {
      logger.error(`Group not found: ${groupId}`);
      dbManager.close();
      process.exit(1);
    }
    
    const articleRepo = new ArticleRepository(db);
    const { DashScopeService } = await import('../services/llm/DashScopeService.js');
    const llmService = new DashScopeService(config.llm);
    const evaluator = new TriggerEvaluator(articleRepo, llmService);
    
    const result = await evaluator.evaluate(group);
    console.log(JSON.stringify(result, null, 2));
    
    dbManager.close();
  });

program
  .command('scheduler:start')
  .description('Start the scheduler service')
  .action(async () => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    const articleRepo = new ArticleRepository(db);
    const { DashScopeService } = await import('../services/llm/DashScopeService.js');
    const llmService = new DashScopeService(config.llm);
    const evaluator = new TriggerEvaluator(articleRepo, llmService);
    const { EventBus } = await import('../features/events/EventBus.js');
    const eventBus = new EventBus();
    const { PipelineOrchestrator } = await import('../features/pipeline/PipelineOrchestrator.js');
    const orchestrator = new PipelineOrchestrator(dbManager, {
      maxConcurrentGroups: config.scheduler.maxConcurrentGroups,
    });
    
    const scheduler = new SchedulerService(
      groupRepo,
      orchestrator,
      evaluator,
      eventBus,
      config.scheduler,
      config.sync,
      dbManager,
    );
    
    scheduler.start();
    console.log(JSON.stringify({ status: 'started', timestamp: new Date().toISOString() }, null, 2));
    
    process.on('SIGINT', () => {
      scheduler.stop();
      dbManager.close();
      process.exit(0);
    });
  });

program
  .command('scheduler:stop')
  .description('Stop the scheduler service')
  .action(async () => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    const articleRepo = new ArticleRepository(db);
    const { DashScopeService } = await import('../services/llm/DashScopeService.js');
    const llmService = new DashScopeService(config.llm);
    const evaluator = new TriggerEvaluator(articleRepo, llmService);
    const { EventBus } = await import('../features/events/EventBus.js');
    const eventBus = new EventBus();
    const { PipelineOrchestrator } = await import('../features/pipeline/PipelineOrchestrator.js');
    const orchestrator = new PipelineOrchestrator(dbManager, {
      maxConcurrentGroups: config.scheduler.maxConcurrentGroups,
    });
    
    const scheduler = new SchedulerService(
      groupRepo,
      orchestrator,
      evaluator,
      eventBus,
      config.scheduler,
      config.sync,
      dbManager,
    );
    
    scheduler.stop();
    console.log(JSON.stringify({ status: 'stopped', timestamp: new Date().toISOString() }, null, 2));
    
    dbManager.close();
  });

program
  .command('scheduler:status')
  .description('Display scheduler configuration and enabled groups')
  .action(() => {
    const config = loadConfig();
    
    console.log('Scheduler Configuration:');
    console.log(`  Check Interval: ${config.scheduler.checkInterval} seconds`);
    console.log(`  Max Concurrent Groups: ${config.scheduler.maxConcurrentGroups}`);
    
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groups = db.prepare(`
      SELECT id, name, trigger_type 
      FROM groups 
      WHERE enabled = 1 
      ORDER BY name
    `).all() as Array<{ id: string; name: string; trigger_type: string }>;
    
    console.log(`\nEnabled Groups (${groups.length}):`);
    
    if (groups.length === 0) {
      logger.info('No enabled groups found');
    } else {
      console.table(groups.map(g => ({
        ID: g.id,
        Name: g.name,
        Trigger: g.trigger_type,
      })));
    }
    
    dbManager.close();
  });

  program
  .command('pipeline:stop <runId>')
  .description('Stop a running pipeline by run ID')
  .action(async (runId) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const orchestrator = new PipelineOrchestrator(dbManager, {
      maxConcurrentGroups: config.scheduler.maxConcurrentGroups,
    });
    
    logger.info(`Attempting to stop pipeline: ${runId}`);
    
    try {
      const result = orchestrator.stopPipeline(runId);
      logger.info({ 
        runId: result.runId, 
        groupId: result.groupId,
        status: result.status,
      }, 'Pipeline stopped successfully');
      console.log(JSON.stringify({
        success: true,
        runId: result.runId,
        groupId: result.groupId,
        status: result.status,
      }, null, 2));
    } catch (error) {
      logger.error({ error }, 'Failed to stop pipeline');
      console.error(JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : String(error),
      }, null, 2));
      process.exit(1);
    } finally {
      dbManager.close();
    }
  });

program
  .command('feed:regenerate [groupId]')
  .description('Regenerate RSS feed XML with current baseUrl (supports index or ID)')
  .action(async (groupId) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    const { PodcastFeedGenerator } = await import('../services/feed/PodcastFeedGenerator.js');
    const feedGenerator = new PodcastFeedGenerator();
    
    try {
      if (groupId) {
        // Regenerate for specific group
        const resolvedId = resolveGroupId(groupId, db);
        
        if (!resolvedId) {
          logger.error(`Group not found: ${groupId}`);
          dbManager.close();
          process.exit(1);
        }
        
        const group = groupRepo.findById(resolvedId);
        if (!group) {
          logger.error(`Group not found: ${groupId}`);
          dbManager.close();
          process.exit(1);
        }
        
        // Get episodes for this group
        const episodes = db.prepare(`
          SELECT * FROM episodes 
          WHERE group_id = ? 
          ORDER BY pub_date DESC 
          LIMIT 10
        `).all(resolvedId) as Array<{
          id: string;
          title: string;
          script: string;
          audio_path: string;
          duration_seconds: number;
          guid: string;
          pub_date: string;
        }>;
        
        if (episodes.length === 0) {
          logger.warn(`No episodes found for group: ${group.name}`);
          dbManager.close();
          return;
        }
        
        // Build feed items
        const feedItems = episodes
          .filter(ep => ep.audio_path)
          .map(ep => {
            const scriptContent = ep.script ? JSON.parse(ep.script) : null;
            const relativePath = ep.audio_path.replace(/^.*[/\\]data[/\\]media[/\\]/, '');
            
            return {
              title: ep.title || `${group.name} - ${new Date(ep.pub_date).toLocaleDateString()}`,
              description: scriptContent?.summary || 'Generated episode',
              enclosure: {
                url: `${config.api.baseUrl}/api/media/${relativePath}`,
                length: 0,
                type: 'audio/mpeg',
              },
              pubDate: ep.pub_date,
              guid: ep.guid,
            };
          });
        
        if (feedItems.length === 0) {
          logger.warn(`No episodes with audio found for group: ${group.name}`);
          dbManager.close();
          return;
        }
        
        // Generate feed
        const feedConfig = {
          groupId: resolvedId,
          title: group.name,
          description: group.description || 'Generated podcast feed',
          imageUrl: undefined,
          siteUrl: config.api.baseUrl,
          author: 'RSS2Pod',
          itunesAuthor: 'RSS2Pod',
          itunesExplicit: 'no' as const,
          itunesOwnerName: 'RSS2Pod',
          itunesOwnerEmail: 'noreply@localhost',
          itunesCategory: 'Technology',
          language: 'en',
        };
        
        feedGenerator.generateFeed(feedItems, feedConfig);
        logger.info({ 
          groupId: resolvedId, 
          groupName: group.name,
          episodeCount: feedItems.length,
          baseUrl: config.api.baseUrl,
        }, 'Feed regenerated successfully');
        
        console.log(JSON.stringify({
          success: true,
          groupId: resolvedId,
          groupName: group.name,
          episodes: feedItems.length,
          baseUrl: config.api.baseUrl,
          feedPath: `data/media/feeds/${resolvedId}.xml`,
        }, null, 2));
        
      } else {
        // Regenerate for all groups
        const groups = groupRepo.findAll();
        
        if (groups.length === 0) {
          logger.info('No groups found');
          dbManager.close();
          return;
        }
        
        let successCount = 0;
        let skipCount = 0;
        
        for (const group of groups) {
          try {
            // Get episodes for this group
            const episodes = db.prepare(`
              SELECT * FROM episodes 
              WHERE group_id = ? 
              ORDER BY pub_date DESC 
              LIMIT 10
            `).all(group.id) as Array<{
              id: string;
              title: string;
              script: string;
              audio_path: string;
              duration_seconds: number;
              guid: string;
              pub_date: string;
            }>;
            
            if (episodes.length === 0) {
              logger.warn({ groupId: group.id }, 'No episodes found, skipping');
              skipCount++;
              continue;
            }
            
            // Build feed items
            const feedItems = episodes
              .filter(ep => ep.audio_path)
              .map(ep => {
                const scriptContent = ep.script ? JSON.parse(ep.script) : null;
                const relativePath = ep.audio_path.replace(/^.*[/\\]data[/\\]media[/\\]/, '');
                
                return {
                  title: ep.title || `${group.name} - ${new Date(ep.pub_date).toLocaleDateString()}`,
                  description: scriptContent?.summary || 'Generated episode',
                  enclosure: {
                    url: `${config.api.baseUrl}/api/media/${relativePath}`,
                    length: 0,
                    type: 'audio/mpeg',
                  },
                  pubDate: ep.pub_date,
                  guid: ep.guid,
                };
              });
            
            if (feedItems.length === 0) {
              logger.warn({ groupId: group.id }, 'No episodes with audio found, skipping');
              skipCount++;
              continue;
            }
            
            // Generate feed
            const feedConfig = {
              groupId: group.id,
              title: group.name,
              description: group.description || 'Generated podcast feed',
              imageUrl: undefined,
              siteUrl: config.api.baseUrl,
              author: 'RSS2Pod',
              itunesAuthor: 'RSS2Pod',
              itunesExplicit: 'no' as const,
              itunesOwnerName: 'RSS2Pod',
              itunesOwnerEmail: 'noreply@localhost',
              itunesCategory: 'Technology',
              language: 'en',
            };
            
            feedGenerator.generateFeed(feedItems, feedConfig);
            logger.info({ 
              groupId: group.id, 
              groupName: group.name,
              episodeCount: feedItems.length,
            }, 'Feed regenerated');
            
            successCount++;
            
          } catch (error) {
            logger.error({ 
              groupId: group.id, 
              error: error instanceof Error ? error.message : String(error)
            }, 'Failed to regenerate feed');
          }
        }
        
        logger.info({ 
          total: groups.length, 
          success: successCount, 
          skipped: skipCount,
          baseUrl: config.api.baseUrl,
        }, 'All feeds regenerated');
        
        console.log(JSON.stringify({
          success: true,
          totalGroups: groups.length,
          regenerated: successCount,
          skipped: skipCount,
          baseUrl: config.api.baseUrl,
        }, null, 2));
      }
    } catch (error) {
      logger.error({ error }, 'Failed to regenerate feeds');
      console.error(JSON.stringify({
        success: false,
        error: error instanceof Error ? error.message : String(error),
      }, null, 2));
      process.exit(1);
    } finally {
      dbManager.close();
    }
  });

program.parse();
