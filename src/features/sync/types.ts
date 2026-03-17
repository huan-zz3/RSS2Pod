import { z } from 'zod';

export const SyncConfigSchema = z.object({
  enabled: z.boolean().default(true),
  interval: z.number().default(600),
  maxArticlesPerSync: z.number().default(100),
});

export type SyncConfig = z.infer<typeof SyncConfigSchema>;

export interface SyncResult {
  synced: boolean;
  articlesSynced: number;
  maxId: number;
  duration?: number;
  timestamp: Date;
}

export type SyncStrategy = 'incremental' | 'full';

export interface SyncEventPayload {
  groupId?: string;
  articlesSynced?: number;
  maxId?: number;
  error?: string;
  timestamp?: Date;
  groupsCount?: number;
}

export interface SyncStatus {
  isRunning: boolean;
  lastSyncTime: Map<string, Date>;
  intervalSeconds: number;
}
