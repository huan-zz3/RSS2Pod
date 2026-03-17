/**
 * SchedulerService - RSS2Pod 自动调度核心服务
 */

import { schedule, ScheduledTask } from 'node-cron';
import { TriggerEvaluator } from './TriggerEvaluator.js';
import { SyncService } from '../sync/SyncService.js';
import type { Group } from '../../repositories/GroupRepository.js';
import type { GroupRepository } from '../../repositories/GroupRepository.js';
import type { PipelineOrchestrator } from '../pipeline/PipelineOrchestrator.js';
import type { EventBus } from '../events/EventBus.js';
import type { SchedulerConfig } from './types.js';
import type { SyncConfig } from '../sync/types.js';
import { DatabaseManager } from '../../infrastructure/database/DatabaseManager.js';
import { FeverClient } from '../../infrastructure/external/FeverClient.js';
import { ArticleRepository } from '../../repositories/ArticleRepository.js';
import { loadConfig } from '../../shared/config/index.js';
import pino from 'pino';

const logger = pino({ name: 'scheduler-service' });

export class SchedulerService {
  private scheduledTask: ScheduledTask | null = null;
  private syncService: SyncService;
  private isRunning = false;

  constructor(
    private groupRepo: GroupRepository,
    private pipeline: PipelineOrchestrator,
    private evaluator: TriggerEvaluator,
    private eventBus: EventBus,
    private schedulerConfig: SchedulerConfig,
    private syncConfig: SyncConfig,
    dbManager: DatabaseManager,
  ) {
    this.syncService = new SyncService(
      groupRepo,
      new ArticleRepository(dbManager.getDb()),
      new FeverClient(loadConfig().fever),
      eventBus,
      syncConfig,
    );
  }

  start(): void {
    if (this.isRunning) {
      return;
    }
    
    if (this.syncConfig.enabled) {
      this.syncService.start();
      logger.info(`SyncService started with interval: ${this.syncConfig.interval}s`);
    }
    
    this.scheduledTask = schedule('* * * * *', () => {
      this.checkAllGroups().catch((error) => {
        logger.error('[SchedulerService] Error checking groups:', error);
      });
    });
    
    this.isRunning = true;
    logger.info('SchedulerService started');
  }

  stop(): void {
    if (this.scheduledTask) {
      this.scheduledTask.stop();
      this.scheduledTask = null;
    }
    
    this.syncService.stop();
    
    this.isRunning = false;
    logger.info('SchedulerService stopped');
  }

  private async checkAllGroups(): Promise<void> {
    const groups = this.groupRepo.findAll({ enabledOnly: true });
    
    for (const group of groups) {
      await this.checkGroup(group);
    }
  }

  private async checkGroup(group: Group): Promise<void> {
    try {
      const result = await this.evaluator.evaluate(group);
      
      if (result.triggered) {
        const eventType = result.triggerType === 'mixed' 
          ? 'trigger:llm' as const 
          : `trigger:${result.triggerType}` as const;
        
        const payloadTriggerType = result.triggerType === 'mixed' 
          ? 'llm' as const 
          : result.triggerType;
        
        this.eventBus.emit(eventType, {
          groupId: group.id,
          triggerType: payloadTriggerType,
          triggered: true,
          reason: result.reason,
        }, 'SchedulerService');
        
        const activeRuns = this.pipeline.getActiveRuns();
        if (activeRuns.length >= this.schedulerConfig.maxConcurrentGroups) {
          logger.warn({ groupId: group.id }, 'Max concurrent groups reached, skipping trigger');
          return;
        }
        
        // 检查该组是否已经在运行中
        const isGroupRunning = activeRuns.some(run => run.groupId === group.id);
        if (isGroupRunning) {
          logger.warn({ groupId: group.id }, 'Group is already running, skipping trigger');
          return;
        }
        
        logger.info({ groupId: group.id, triggerType: result.triggerType }, 'Trigger condition met, running pipeline');
        await this.pipeline.runForGroup(group.id);
      }
    } catch (error) {
      logger.error(
        { groupId: group.id, error },
        `[SchedulerService] Error checking group ${group.id}:`,
        error instanceof Error ? error.message : String(error)
      );
    }
  }
  
  getSyncService(): SyncService {
    return this.syncService;
  }
}
