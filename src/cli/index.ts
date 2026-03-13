#!/usr/bin/env node

import { Command } from 'commander';
import { join } from 'path';
import { readFileSync, existsSync } from 'fs';
import { loadConfig, createConfigTemplate } from '../shared/config/index.js';
import { DatabaseManager } from '../infrastructure/database/DatabaseManager.js';
import { FeverClient } from '../infrastructure/external/FeverClient.js';
import { PipelineOrchestrator } from '../features/pipeline/PipelineOrchestrator.js';
import { GroupRepository } from '../repositories/GroupRepository.js';
import pino from 'pino';

const logger = pino({ name: 'cli' });

const pkgPath = join(process.cwd(), 'package.json');
const pkg = existsSync(pkgPath) 
  ? JSON.parse(readFileSync(pkgPath, 'utf-8'))
  : { name: 'rss2pod', version: '3.0.0' };

const program = new Command();

program
  .name(pkg.name)
  .version(pkg.version)
  .description('RSS to Podcast converter');

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

program
  .command('group:create <name>')
  .description('Create a new group')
  .option('-d, --description <text>', 'Group description')
  .option('-s, --sources <ids>', 'Comma-separated source IDs')
  .action((name, options) => {
    const config = loadConfig();
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const db = dbManager.getDb();
    const groupRepo = new GroupRepository(db);
    
    const group = {
      id: `grp-${Date.now()}`,
      name,
      description: options.description,
      sourceIds: options.sources ? options.sources.split(',') : [],
      enabled: true,
      triggerType: 'time' as const,
      triggerConfig: { cron: '0 9 * * *' },
      podcastStructure: { type: 'single' as const },
      learningMode: 'normal' as const,
      retentionDays: 30,
    };
    
    groupRepo.create(group);
    logger.info(`Group created: ${name} (${group.id})`);
    
    dbManager.close();
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
    } else {
      logger.error('Fever API connection failed');
      process.exit(1);
    }
  });

program
  .command('pipeline:run <groupId>')
  .description('Run pipeline for a group')
  .action(async (groupId) => {
    const config = loadConfig();
    
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    
    const feverClient = new FeverClient(config.fever);
    const orchestrator = new PipelineOrchestrator(dbManager, feverClient, {
      maxConcurrentGroups: config.scheduler.maxConcurrentGroups,
    });
    
    logger.info(`Starting pipeline for group: ${groupId}`);
    
    try {
      const run = await orchestrator.runForGroup(groupId);
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

program.parse();
