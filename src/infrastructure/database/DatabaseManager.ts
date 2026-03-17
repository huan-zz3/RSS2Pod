import Database from 'better-sqlite3';
import { mkdirSync, existsSync } from 'fs';
import { dirname } from 'path';
import pino from 'pino';

const logger = pino({
  name: 'database',
  timestamp: () => `,"time":"${new Date(new Date().getTime() + 8 * 3600 * 1000).toISOString().replace('Z', '+08:00')}"`,
});

/**
 * Database schema version
 */
const SCHEMA_VERSION = 2;

/**
 * Database manager class
 * 
 * Handles SQLite database initialization and connections
 */
export class DatabaseManager {
  private db: Database.Database | null = null;
  private readonly dbPath: string;

  constructor(dbPath: string) {
    this.dbPath = dbPath;
  }

  /**
   * Initialize database and create tables
   */
  initialize(): Database.Database {
    const dir = dirname(this.dbPath);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }

    logger.info({ path: this.dbPath }, 'Initializing database');

    this.db = new Database(this.dbPath);
    
    this.db.pragma('journal_mode = WAL');
    this.db.pragma('foreign_keys = ON');
    this.db.pragma('busy_timeout = 5000');

    this.createTables();
    
    this.db.prepare(`
      INSERT OR REPLACE INTO schema_info (key, value) 
      VALUES ('version', ?)
    `).run(SCHEMA_VERSION.toString());

    logger.info('Database initialized successfully');
    return this.db;
  }

  /**
   * Create all database tables
   */
  private createTables(): void {
    if (!this.db) throw new Error('Database not initialized');

    this.db.exec(`
      -- Schema version tracking
      CREATE TABLE IF NOT EXISTS schema_info (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      );

      -- Articles table
      CREATE TABLE IF NOT EXISTS articles (
        id TEXT PRIMARY KEY,
        fever_id INTEGER UNIQUE NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        source_id TEXT NOT NULL,
        source_name TEXT,
        published_at INTEGER NOT NULL,
        fetched_at INTEGER NOT NULL,
        is_read INTEGER DEFAULT 0,
        is_saved INTEGER DEFAULT 0,
        processed_by_group TEXT, -- JSON array of group IDs
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        updated_at INTEGER DEFAULT (strftime('%s', 'now'))
      );

      CREATE INDEX IF NOT EXISTS idx_articles_fever_id ON articles(fever_id);
      CREATE INDEX IF NOT EXISTS idx_articles_source_id ON articles(source_id);
      CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at);
      CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles(processed_by_group);

      -- Groups table
      CREATE TABLE IF NOT EXISTS groups (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        source_ids TEXT NOT NULL, -- JSON array
        enabled INTEGER DEFAULT 1,
        trigger_type TEXT DEFAULT 'time', -- time, count, llm, mixed
        trigger_config TEXT, -- JSON configuration
        prompt_overrides TEXT, -- JSON overrides
        podcast_structure TEXT DEFAULT '{"type":"single"}', -- single or dual
        learning_mode TEXT DEFAULT 'normal', -- normal, word_explanation, sentence_translation
        retention_days INTEGER DEFAULT 30,
        last_synced_max_id INTEGER DEFAULT 0, -- Incremental sync tracking
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        updated_at INTEGER DEFAULT (strftime('%s', 'now'))
      );

      CREATE INDEX IF NOT EXISTS idx_groups_enabled ON groups(enabled);

      -- Group-RSS source mapping
      CREATE TABLE IF NOT EXISTS group_sources (
        group_id TEXT NOT NULL,
        source_id TEXT NOT NULL,
        PRIMARY KEY (group_id, source_id),
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
      );

      -- Episodes table
      CREATE TABLE IF NOT EXISTS episodes (
        id TEXT PRIMARY KEY,
        group_id TEXT NOT NULL,
        title TEXT NOT NULL,
        script TEXT NOT NULL, -- JSON script content
        audio_path TEXT,
        script_path TEXT,
        duration_seconds INTEGER,
        file_size_bytes INTEGER,
        guid TEXT UNIQUE NOT NULL,
        pub_date INTEGER NOT NULL,
        starred INTEGER DEFAULT 0,
        expire_at INTEGER,
        feed_url TEXT,
        article_ids TEXT, -- JSON array of included article IDs
        source_summary_ids TEXT, -- JSON array of source summary IDs
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        updated_at INTEGER DEFAULT (strftime('%s', 'now')),
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
      );

      CREATE INDEX IF NOT EXISTS idx_episodes_group_id ON episodes(group_id);
      CREATE INDEX IF NOT EXISTS idx_episodes_pub_date ON episodes(pub_date);
      CREATE INDEX IF NOT EXISTS idx_episodes_starred ON episodes(starred);
      CREATE INDEX IF NOT EXISTS idx_episodes_expire_at ON episodes(expire_at);

      -- Source summaries table
      CREATE TABLE IF NOT EXISTS source_summaries (
        id TEXT PRIMARY KEY,
        group_id TEXT NOT NULL,
        source_id TEXT NOT NULL,
        summary TEXT NOT NULL,
        article_ids TEXT NOT NULL, -- JSON array
        run_id TEXT NOT NULL,
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
      );

      CREATE INDEX IF NOT EXISTS idx_source_summaries_group ON source_summaries(group_id);
      CREATE INDEX IF NOT EXISTS idx_source_summaries_run ON source_summaries(run_id);

      -- Group summaries table
      CREATE TABLE IF NOT EXISTS group_summaries (
        id TEXT PRIMARY KEY,
        group_id TEXT NOT NULL,
        summary TEXT NOT NULL,
        source_summary_ids TEXT NOT NULL, -- JSON array
        run_id TEXT NOT NULL,
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
      );

      CREATE INDEX IF NOT EXISTS idx_group_summaries_group ON group_summaries(group_id);
      CREATE INDEX IF NOT EXISTS idx_group_summaries_run ON group_summaries(run_id);

      -- Pipeline run history
      CREATE TABLE IF NOT EXISTS pipeline_runs (
        id TEXT PRIMARY KEY,
        group_id TEXT NOT NULL,
        status TEXT NOT NULL, -- pending, running, completed, failed, cancelled
        started_at INTEGER,
        completed_at INTEGER,
        stages TEXT, -- JSON array of stage statuses
        articles_count INTEGER,
        error TEXT,
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
      );

      CREATE INDEX IF NOT EXISTS idx_pipeline_runs_group ON pipeline_runs(group_id);
      CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
      CREATE INDEX IF NOT EXISTS idx_pipeline_runs_created ON pipeline_runs(created_at);

      -- Processing state (for locking)
      CREATE TABLE IF NOT EXISTS processing_state (
        group_id TEXT PRIMARY KEY,
        is_running INTEGER DEFAULT 0,
        lock_time INTEGER,
        lock_token TEXT,
        last_run_at INTEGER,
        next_run_at INTEGER,
        updated_at INTEGER DEFAULT (strftime('%s', 'now')),
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
      );
    `);

    logger.info('Database tables created');
  }

  /**
   * Get database instance
   */
  getDb(): Database.Database {
    if (!this.db) {
      throw new Error('Database not initialized. Call initialize() first.');
    }
    return this.db;
  }

  /**
   * Close database connection
   */
  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
      logger.info('Database connection closed');
    }
  }

  /**
   * Run a transaction
   */
  transaction<T>(fn: () => T): T {
    const db = this.getDb();
    const transaction = db.transaction(fn);
    return transaction();
  }

  /**
   * Get schema version
   */
  getSchemaVersion(): number {
    const db = this.getDb();
    const result = db.prepare('SELECT value FROM schema_info WHERE key = ?').get('version') as { value: string } | undefined;
    return result ? parseInt(result.value, 10) : 0;
  }

  /**
   * Run database migrations
   */
  migrate(): void {
    const currentVersion = this.getSchemaVersion();
    
    if (currentVersion < SCHEMA_VERSION) {
      logger.info({ currentVersion, targetVersion: SCHEMA_VERSION }, 'Running migrations');
      
      this.db!.transaction(() => {
        if (currentVersion < 2) {
          this.db!.exec(`
            ALTER TABLE groups ADD COLUMN last_synced_max_id INTEGER DEFAULT 0;
          `);
          logger.info('Migration to v2 completed: Added last_synced_max_id column');
        }
      })();
      
      this.db!.prepare(`
        INSERT OR REPLACE INTO schema_info (key, value) 
        VALUES ('version', ?)
      `).run(SCHEMA_VERSION.toString());
      
      logger.info({ newVersion: SCHEMA_VERSION }, 'Migrations completed');
    }
  }
}

// Singleton instance
let dbManagerInstance: DatabaseManager | null = null;

/**
 * Get database manager instance
 */
export function getDatabaseManager(dbPath?: string): DatabaseManager {
  if (!dbManagerInstance) {
    const path = dbPath ?? './data/rss2pod.db';
    dbManagerInstance = new DatabaseManager(path);
  }
  return dbManagerInstance;
}

/**
 * Reset database manager (for testing)
 */
export function resetDatabaseManager(): void {
  if (dbManagerInstance) {
    dbManagerInstance.close();
    dbManagerInstance = null;
  }
}
