import Database from 'better-sqlite3';

export interface Article {
  id: string;
  feverId: number;
  title: string;
  content: string;
  sourceId: string;
  sourceName?: string;
  publishedAt: Date;
  fetchedAt: Date;
  isRead: boolean;
  isSaved: boolean;
  processedByGroup: string[];
}

export class ArticleRepository {
  private db: Database.Database;

  constructor(db: Database.Database) {
    this.db = db;
  }

  insert(article: Article): void {
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO articles (
        id, fever_id, title, content, source_id, source_name,
        published_at, fetched_at, is_read, is_saved, processed_by_group
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      article.id,
      article.feverId,
      article.title,
      article.content,
      article.sourceId,
      article.sourceName ?? null,
      Math.floor(article.publishedAt.getTime() / 1000),
      Math.floor(article.fetchedAt.getTime() / 1000),
      article.isRead ? 1 : 0,
      article.isSaved ? 1 : 0,
      JSON.stringify(article.processedByGroup),
    );
  }

  insertMany(articles: Article[]): void {
    const transaction = this.db.transaction((items: Article[]) => {
      for (const article of items) {
        this.insert(article);
      }
    });
    transaction(articles);
  }

  findById(id: string): Article | undefined {
    const row = this.db.prepare(`
      SELECT * FROM articles WHERE id = ?
    `).get(id) as Record<string, unknown> | undefined;

    return row ? this.mapRowToArticle(row) : undefined;
  }

  findByFeverId(feverId: number): Article | undefined {
    const row = this.db.prepare(`
      SELECT * FROM articles WHERE fever_id = ?
    `).get(feverId) as Record<string, unknown> | undefined;

    return row ? this.mapRowToArticle(row) : undefined;
  }

  findUnprocessed(groupId: string, limit: number = 100): Article[] {
    const rows = this.db.prepare(`
      SELECT * FROM articles 
      WHERE processed_by_group IS NULL 
         OR processed_by_group NOT LIKE ?
      ORDER BY published_at ASC
      LIMIT ?
    `).all(`%"${groupId}"%`, limit) as Record<string, unknown>[];

    return rows.map(row => this.mapRowToArticle(row));
  }

  findBySource(sourceId: string, limit: number = 50): Article[] {
    const rows = this.db.prepare(`
      SELECT * FROM articles 
      WHERE source_id = ?
      ORDER BY published_at DESC
      LIMIT ?
    `).all(sourceId, limit) as Record<string, unknown>[];

    return rows.map(row => this.mapRowToArticle(row));
  }

  markProcessed(articleId: string, groupId: string): void {
    const article = this.findById(articleId);
    if (!article) return;

    const groups = article.processedByGroup.includes(groupId)
      ? article.processedByGroup
      : [...article.processedByGroup, groupId];

    this.db.prepare(`
      UPDATE articles 
      SET processed_by_group = ?, updated_at = strftime('%s', 'now')
      WHERE id = ?
    `).run(JSON.stringify(groups), articleId);
  }

  deleteOlderThan(days: number): number {
    const cutoff = Math.floor(Date.now() / 1000) - (days * 24 * 60 * 60);
    
    const stmt = this.db.prepare(`
      DELETE FROM articles WHERE published_at < ?
    `);
    
    const result = stmt.run(cutoff);
    return result.changes;
  }

  count(): number {
    const row = this.db.prepare(`SELECT COUNT(*) as count FROM articles`).get() as { count: number };
    return row.count;
  }

  countUnprocessed(groupId: string): number {
    const row = this.db.prepare(`
      SELECT COUNT(*) as count FROM articles 
      WHERE processed_by_group IS NULL 
         OR processed_by_group NOT LIKE ?
    `).get(`%"${groupId}"%`) as { count: number };
    
    return row.count;
  }

  private mapRowToArticle(row: Record<string, unknown>): Article {
    return {
      id: row.id as string,
      feverId: row.fever_id as number,
      title: row.title as string,
      content: row.content as string,
      sourceId: row.source_id as string,
      sourceName: row.source_name as string | undefined,
      publishedAt: new Date((row.published_at as number) * 1000),
      fetchedAt: new Date((row.fetched_at as number) * 1000),
      isRead: (row.is_read as number) === 1,
      isSaved: (row.is_saved as number) === 1,
      processedByGroup: row.processed_by_group 
        ? JSON.parse(row.processed_by_group as string) 
        : [],
    };
  }
}
