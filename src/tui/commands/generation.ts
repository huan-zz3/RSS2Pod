import { DatabaseManager } from '../../infrastructure/database/DatabaseManager.js';
import { PipelineOrchestrator } from '../../features/pipeline/PipelineOrchestrator.js';
import { loadConfig } from '../../shared/config/index.js';

export interface PipelineRun {
  id: string;
  groupId: string;
  status: string;
  articlesCount: number;
  error?: string;
}

export interface PipelineHistory {
  id: string;
  groupId: string;
  status: string;
  articlesCount: number;
  createdAt: Date;
}

export async function runPipeline(groupId: string): Promise<PipelineRun> {
  const config = loadConfig();
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  
  const orchestrator = new PipelineOrchestrator(dbManager, {
    maxConcurrentGroups: config.scheduler.maxConcurrentGroups,
  });
  
  try {
    const run = await orchestrator.runForGroup(groupId);
    dbManager.close();
    
    return {
      id: run.id,
      groupId: run.groupId,
      status: run.status,
      articlesCount: run.articlesCount,
      error: run.error,
    };
  } catch (error) {
    dbManager.close();
    throw error;
  }
}

export async function getPipelineHistory(limit: number = 20): Promise<PipelineHistory[]> {
  const config = loadConfig();
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  
  const db = dbManager.getDb();
  const runs = db.prepare(`
    SELECT * FROM pipeline_runs 
    ORDER BY created_at DESC 
    LIMIT ?
  `).all(limit) as Array<{
    id: string;
    group_id: string;
    status: string;
    articles_count: number;
    created_at: number;
  }>;
  
  dbManager.close();
  
  return runs.map(r => ({
    id: r.id,
    groupId: r.group_id,
    status: r.status,
    articlesCount: r.articles_count,
    createdAt: new Date(r.created_at * 1000),
  }));
}
