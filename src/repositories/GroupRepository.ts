import Database from 'better-sqlite3';

export interface Group {
  id: string;
  name: string;
  description?: string;
  sourceIds: string[];
  enabled: boolean;
  triggerType: 'time' | 'count' | 'llm' | 'mixed';
  triggerConfig: TriggerConfig;
  promptOverrides?: Record<string, string>;
  podcastStructure: PodcastStructure;
  learningMode: 'normal' | 'word_explanation' | 'sentence_translation';
  retentionDays: number;
  lastSyncedMaxId?: number;
}

export interface TriggerConfig {
  cron?: string;
  threshold?: number;
  [key: string]: unknown;
}

export interface PodcastStructure {
  type: 'single' | 'dual';
  hostName?: string;
  guestName?: string;
}

export class GroupRepository {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  create(group: Group): void {
    const stmt = this.db.prepare(`
      INSERT INTO groups (
        id, name, description, source_ids, enabled,
        trigger_type, trigger_config, prompt_overrides,
        podcast_structure, learning_mode, retention_days
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      group.id,
      group.name,
      group.description ?? null,
      JSON.stringify(group.sourceIds),
      group.enabled ? 1 : 0,
      group.triggerType,
      JSON.stringify(group.triggerConfig),
      group.promptOverrides ? JSON.stringify(group.promptOverrides) : null,
      JSON.stringify(group.podcastStructure),
      group.learningMode,
      group.retentionDays,
    );
  }

  update(group: Group): void {
    const stmt = this.db.prepare(`
      UPDATE groups SET
        name = ?,
        description = ?,
        source_ids = ?,
        enabled = ?,
        trigger_type = ?,
        trigger_config = ?,
        prompt_overrides = ?,
        podcast_structure = ?,
        learning_mode = ?,
        retention_days = ?,
        last_synced_max_id = ?,
        updated_at = strftime('%s', 'now')
      WHERE id = ?
    `);

    stmt.run(
      group.name,
      group.description ?? null,
      JSON.stringify(group.sourceIds),
      group.enabled ? 1 : 0,
      group.triggerType,
      JSON.stringify(group.triggerConfig),
      group.promptOverrides ? JSON.stringify(group.promptOverrides) : null,
      JSON.stringify(group.podcastStructure),
      group.learningMode,
      group.retentionDays,
      group.lastSyncedMaxId,
      group.id,
    );
  }

  findById(id: string): Group | undefined {
    const row = this.db.prepare(`SELECT * FROM groups WHERE id = ?`).get(id) as Record<string, unknown> | undefined;
    return row ? this.mapRowToGroup(row) : undefined;
  }

  findByName(name: string): Group | undefined {
    const row = this.db.prepare(`SELECT * FROM groups WHERE name = ?`).get(name) as Record<string, unknown> | undefined;
    return row ? this.mapRowToGroup(row) : undefined;
  }

  findAll(options?: { enabledOnly?: boolean }): Group[] {
    const where = options?.enabledOnly ? 'WHERE enabled = 1' : '';
    const rows = this.db.prepare(`SELECT * FROM groups ${where}`).all() as Record<string, unknown>[];
    return rows.map(row => this.mapRowToGroup(row));
  }

  delete(id: string): void {
    this.db.prepare(`DELETE FROM groups WHERE id = ?`).run(id);
  }

  enable(id: string): void {
    this.db.prepare(`
      UPDATE groups SET enabled = 1, updated_at = strftime('%s', 'now') WHERE id = ?
    `).run(id);
  }

  disable(id: string): void {
    this.db.prepare(`
      UPDATE groups SET enabled = 0, updated_at = strftime('%s', 'now') WHERE id = ?
    `).run(id);
  }

  updateLastSyncedMaxId(groupId: string, maxId: number): void {
    this.db.prepare(`
      UPDATE groups 
      SET last_synced_max_id = ?, updated_at = strftime('%s', 'now') 
      WHERE id = ?
    `).run(maxId, groupId);
  }

  private mapRowToGroup(row: Record<string, unknown>): Group {
    return {
      id: row.id as string,
      name: row.name as string,
      description: row.description as string | undefined,
      sourceIds: JSON.parse(row.source_ids as string),
      enabled: (row.enabled as number) === 1,
      triggerType: row.trigger_type as 'time' | 'count' | 'llm' | 'mixed',
      triggerConfig: JSON.parse(row.trigger_config as string),
      promptOverrides: row.prompt_overrides 
        ? JSON.parse(row.prompt_overrides as string) 
        : undefined,
      podcastStructure: JSON.parse(row.podcast_structure as string),
      learningMode: row.learning_mode as 'normal' | 'word_explanation' | 'sentence_translation',
      retentionDays: row.retention_days as number,
      lastSyncedMaxId: (row.last_synced_max_id as number) ?? 0,
    };
  }
}
