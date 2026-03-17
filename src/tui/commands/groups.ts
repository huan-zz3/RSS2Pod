import { DatabaseManager } from '../../infrastructure/database/DatabaseManager.js';
import { GroupRepository } from '../../repositories/GroupRepository.js';
import { loadConfig } from '../../shared/config/index.js';

export interface GroupInfo {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
  triggerType: string;
  triggerConfig?: {
    cron?: string;
    threshold?: number;
    llmEnabled?: boolean;
  };
  sourceCount: number;
  sourceIds?: string[];
  learningMode?: 'normal' | 'word_explanation' | 'sentence_translation';
}

export async function listGroups(): Promise<GroupInfo[]> {
  const config = loadConfig();
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  
  const db = dbManager.getDb();
  const groupRepo = new GroupRepository(db);
  const groups = groupRepo.findAll();
  
  dbManager.close();
  
  return groups.map(g => ({
    id: g.id,
    name: g.name,
    description: g.description,
    enabled: g.enabled,
    triggerType: g.triggerType,
    sourceCount: g.sourceIds.length,
  }));
}

export async function getGroup(id: string): Promise<GroupInfo | null> {
  const config = loadConfig();
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  
  const db = dbManager.getDb();
  const groupRepo = new GroupRepository(db);
  const group = groupRepo.findById(id);
  
  dbManager.close();
  
  if (!group) return null;
  
  return {
    id: group.id,
    name: group.name,
    description: group.description,
    enabled: group.enabled,
    triggerType: group.triggerType,
    triggerConfig: group.triggerConfig,
    sourceCount: group.sourceIds.length,
    sourceIds: group.sourceIds,
    learningMode: group.learningMode,
  };
}

export async function createGroup(
  name: string,
  options: {
    description?: string;
    sourceIds?: string[];
    triggerType?: string;
  }
): Promise<string> {
  const config = loadConfig();
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  
  const db = dbManager.getDb();
  const groupRepo = new GroupRepository(db);
  
  const group = {
    id: `grp-${Date.now()}`,
    name,
    description: options.description,
    sourceIds: options.sourceIds || [],
    enabled: true,
    triggerType: (options.triggerType || 'time') as 'time' | 'count' | 'llm' | 'mixed',
    triggerConfig: { cron: '0 9 * * *' },
    podcastStructure: { type: 'single' as const },
    learningMode: 'normal' as const,
    retentionDays: 30,
    lastSyncedMaxId: 0,
  };
  
  groupRepo.create(group);
  dbManager.close();
  
  return group.id;
}

export async function deleteGroup(id: string): Promise<void> {
  const config = loadConfig();
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  
  const db = dbManager.getDb();
  const groupRepo = new GroupRepository(db);
  groupRepo.delete(id);
  
  dbManager.close();
}

export async function updateGroup(
  id: string,
  updates: {
    name?: string;
    description?: string;
    sourceIds?: string[];
    enabled?: boolean;
    triggerType?: string;
    triggerConfig?: any;
    podcastStructure?: any;
    learningMode?: string;
    retentionDays?: number;
  }
): Promise<void> {
  const config = loadConfig();
  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  
  const db = dbManager.getDb();
  const groupRepo = new GroupRepository(db);
  const group = groupRepo.findById(id);
  
  if (!group) {
    dbManager.close();
    throw new Error('Group not found');
  }
  
  const updatedGroup = {
    ...group,
    name: updates.name ?? group.name,
    description: updates.description ?? group.description,
    sourceIds: updates.sourceIds ?? group.sourceIds,
    enabled: updates.enabled ?? group.enabled,
    triggerType: (updates.triggerType ?? group.triggerType) as 'time' | 'count' | 'llm' | 'mixed',
    triggerConfig: updates.triggerConfig ?? group.triggerConfig,
    podcastStructure: updates.podcastStructure ?? group.podcastStructure,
    learningMode: (updates.learningMode ?? group.learningMode) as any,
    retentionDays: updates.retentionDays ?? group.retentionDays,
  };
  
  groupRepo.update(updatedGroup);
  dbManager.close();
}
