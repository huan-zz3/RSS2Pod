import { FeverClient } from '../../infrastructure/external/FeverClient.js';
import { DatabaseManager } from '../../infrastructure/database/DatabaseManager.js';
import { GroupRepository } from '../../repositories/GroupRepository.js';
import { ArticleRepository } from '../../repositories/ArticleRepository.js';
import { SyncService } from '../../features/sync/SyncService.js';
import { getEventBus } from '../../features/events/EventBus.js';
import { loadConfig } from '../../shared/config/index.js';
import type { SyncResult } from '../../features/sync/types.js';
import pino from 'pino';

const logger = pino({ name: 'tui-commands-fever' });

export interface FeedInfo {
  id: number;
  title: string;
  url: string;
  siteUrl: string;
}

export interface GroupInfo {
  id: number;
  title: string;
}

export async function testFeverConnection(): Promise<boolean> {
  const config = loadConfig();
  const client = new FeverClient(config.fever);
  return await client.testAuth();
}

export async function listFeeds(): Promise<FeedInfo[]> {
  const config = loadConfig();
  const client = new FeverClient(config.fever);
  const feeds = await client.getFeeds();
  return feeds.map(f => ({
    id: f.id,
    title: f.title,
    url: f.url,
    siteUrl: f.siteUrl,
  }));
}

export async function listFeverGroups(): Promise<GroupInfo[]> {
  const config = loadConfig();
  const client = new FeverClient(config.fever);
  const groups = await client.getGroups();
  return groups.map(g => ({
    id: g.id,
    title: g.title,
  }));
}

export async function syncFeeds(): Promise<number> {
  const config = loadConfig();
  const client = new FeverClient(config.fever);
  const feeds = await client.getFeeds();
  return feeds.length;
}

export async function syncArticles(groupId?: string): Promise<SyncResult> {
  const config = loadConfig();
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  
  try {
    const groupRepo = new GroupRepository(dbManager.getDb());
    const syncService = new SyncService(
      groupRepo,
      new ArticleRepository(dbManager.getDb()),
      new FeverClient(config.fever),
      getEventBus(),
      config.sync,
    );
    
    if (groupId) {
      const group = dbManager.getDb().prepare('SELECT * FROM groups WHERE id = ?').get(groupId) as { id: string; name: string; sourceIds: string[] } | undefined;
      if (!group) {
        throw new Error(`Group not found: ${groupId}`);
      }
      return await syncService.syncGroup(group as any);
    } else {
      const startTime = Date.now();
      const groups = groupRepo.findAll({ enabledOnly: true });
      
      if (groups.length === 0) {
        throw new Error('No enabled groups found. Please create and enable a group first.');
      }
      
      let totalArticles = 0;
      let maxId = 0;
      let errorCount = 0;
      const errors: string[] = [];
      
      for (const group of groups) {
        try {
          const result = await syncService.syncGroup(group);
          totalArticles += result.articlesSynced;
          maxId = Math.max(maxId, result.maxId);
        } catch (error) {
          errorCount++;
          const errorMsg = error instanceof Error ? error.message : String(error);
          errors.push(`${group.name}: ${errorMsg}`);
          logger.error({ error }, `Error syncing group ${group.name}`);
        }
      }
      
      if (errorCount === groups.length) {
        throw new Error(`All groups failed to sync:\n${errors.join('\n')}`);
      }
      
      if (errorCount > 0) {
        logger.warn({ errorCount, totalErrors: errors.length }, 'Some groups failed to sync');
      }
      
      return {
        synced: true,
        articlesSynced: totalArticles,
        maxId,
        duration: Date.now() - startTime,
        timestamp: new Date(),
      };
    }
  } finally {
    dbManager.close();
  }
}

export async function cacheArticles(limit: number = 100): Promise<number> {
  const config = loadConfig();
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  
  try {
    const client = new FeverClient(config.fever);
    const articleRepo = new ArticleRepository(dbManager.getDb());
    
    const articles = await client.getItems({ maxId: 2147483647 });
    let count = 0;
    
    for (const item of articles.slice(0, limit)) {
      const existed = articleRepo.findByFeverId(item.id);
      
      if (!existed) {
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
    }
    
    return count;
  } finally {
    dbManager.close();
  }
}
