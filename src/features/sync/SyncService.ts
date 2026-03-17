import { schedule, ScheduledTask } from 'node-cron';
import { GroupRepository } from '../../repositories/GroupRepository.js';
import type { Group } from '../../repositories/GroupRepository.js';
import { ArticleRepository } from '../../repositories/ArticleRepository.js';
import { FeverClient } from '../../infrastructure/external/FeverClient.js';
import { EventBus } from '../events/EventBus.js';
import type { SyncConfig, SyncResult, SyncStatus } from './types.js';
import pino from 'pino';

const logger = pino({ name: 'sync-service' });

export class SyncService {
  private scheduledTask: ScheduledTask | null = null;
  private isRunning = false;
  private lastSyncTime: Map<string, Date> = new Map();

  constructor(
    private groupRepo: GroupRepository,
    private articleRepo: ArticleRepository,
    private feverClient: FeverClient,
    private eventBus: EventBus,
    private config: SyncConfig,
  ) {}

  start(): void {
    if (this.isRunning || !this.config.enabled) {
      return;
    }

    const cronExpression = this.generateCronFromInterval(this.config.interval);
    
    this.scheduledTask = schedule(cronExpression, () => {
      this.syncAllGroups().catch((error) => {
        logger.error('Error syncing groups:', error);
      });
    });

    this.isRunning = true;
    logger.info(`SyncService started with interval: ${this.config.interval}s (cron: ${cronExpression})`);
  }

  stop(): void {
    if (this.scheduledTask) {
      this.scheduledTask.stop();
      this.scheduledTask = null;
    }
    this.isRunning = false;
    logger.info('SyncService stopped');
  }

  async syncAllGroups(): Promise<void> {
    const groups = this.groupRepo.findAll({ enabledOnly: true });
    
    logger.info(`Syncing ${groups.length} groups...`);
    
    const results: SyncResult[] = [];
    
    for (const group of groups) {
      try {
        const result = await this.syncGroup(group);
        results.push(result);
      } catch (error) {
        logger.error({ error }, `Error syncing group ${group.id}`);
      }
    }

    const totalArticles = results.reduce((sum, r) => sum + r.articlesSynced, 0);
    const globalMaxId = Math.max(...results.map(r => r.maxId), 0);

    this.eventBus.emit('sync:completed', {
      articlesSynced: totalArticles,
      maxId: globalMaxId,
    }, 'SyncService');
  }

  async syncGroup(group: Group): Promise<SyncResult> {
    const startTime = Date.now();
    
    logger.info(`Syncing group ${group.id}...`);

    const lastSyncedMaxId = group.lastSyncedMaxId ?? 0;
    
    const articles = await this.feverClient.getItems({ 
      maxId: 2147483647,
      sinceId: lastSyncedMaxId > 0 ? lastSyncedMaxId : undefined,
    });

    let newCount = 0;
    let updatedCount = 0;
    let maxId = lastSyncedMaxId;

    for (const item of articles.slice(0, this.config.maxArticlesPerSync)) {
      if (group.sourceIds.includes(item.feedId.toString())) {
        const existed = this.articleRepo.findByFeverId(item.id);
        
        if (!existed) {
          this.articleRepo.insert({
            id: `art-${item.id}`,
            feverId: item.id,
            title: item.title,
            content: this.stripHtml(item.html),
            sourceId: item.feedId.toString(),
            sourceName: item.feedId.toString(),
            publishedAt: item.createdOn,
            fetchedAt: new Date(),
            isRead: item.isRead,
            isSaved: item.isSaved,
            processedByGroup: [],
          });
          newCount++;
        }

        maxId = Math.max(maxId, item.id);
      }
    }

    const duration = Date.now() - startTime;
    this.lastSyncTime.set(group.id, new Date());
    
    if (maxId > lastSyncedMaxId) {
      this.groupRepo.updateLastSyncedMaxId(group.id, maxId);
    }

    const result: SyncResult = {
      synced: true,
      articlesSynced: newCount + updatedCount,
      maxId,
      duration,
      timestamp: new Date(),
    };

    logger.info({ result }, `Group ${group.id} sync completed`);

    logger.info(`Group ${group.id}: ${newCount} new, ${updatedCount} updated (${duration}ms)`);

    return result;
  }

  async sync(groupId?: string): Promise<SyncResult> {
    if (groupId) {
      const group = this.groupRepo.findById(groupId);
      if (!group) {
        logger.error({ groupId }, 'Group not found');
        return {
          synced: false,
          articlesSynced: 0,
          maxId: 0,
          timestamp: new Date(),
        };
      }
      return this.syncGroup(group);
    } else {
      await this.syncAllGroups();
      return {
        synced: true,
        articlesSynced: 0,
        maxId: 0,
        timestamp: new Date(),
      };
    }
  }

  getLastSyncTime(groupId: string): Date | undefined {
    return this.lastSyncTime.get(groupId);
  }

  getSyncStatus(): SyncStatus {
    return {
      isRunning: this.isRunning,
      lastSyncTime: this.lastSyncTime,
      intervalSeconds: this.config.interval,
    };
  }

  private generateCronFromInterval(seconds: number): string {
    if (seconds <= 60) return '* * * * *';
    if (seconds <= 300) return '*/5 * * * *';
    if (seconds <= 600) return '*/10 * * * *';
    if (seconds <= 1800) return '*/30 * * * *';
    return `0 */${Math.floor(seconds / 3600)} * * *`;
  }

  private stripHtml(html: string): string {
    return html.replace(/<[^>]*>/g, '').trim();
  }
}
