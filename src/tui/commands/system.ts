import { loadConfig } from '../../shared/config/index.js';
import { DatabaseManager } from '../../infrastructure/database/DatabaseManager.js';

export interface SystemStats {
  version: string;
  database: string;
  fever: string;
  llm: string;
  tts: string;
  groups: number;
  articles: number;
  episodes: number;
}

export async function getSystemStats(): Promise<SystemStats> {
  const config = loadConfig();
  const pkg = await import('../../../package.json');
  
  let groups = 0;
  let articles = 0;
  let episodes = 0;
  
  try {
    const dbManager = new DatabaseManager(config.database.path);
    dbManager.initialize();
    const db = dbManager.getDb();
    
    const groupsResult = db.prepare('SELECT COUNT(*) as count FROM groups').get() as { count: number };
    const articlesResult = db.prepare('SELECT COUNT(*) as count FROM articles').get() as { count: number };
    const episodesResult = db.prepare('SELECT COUNT(*) as count FROM episodes').get() as { count: number };
    
    groups = groupsResult.count;
    articles = articlesResult.count;
    episodes = episodesResult.count;
    
    dbManager.close();
  } catch {
  }
  
  return {
    version: (pkg.default || pkg).version || '3.0.0',
    database: config.database.path,
    fever: config.fever.baseUrl,
    llm: `${config.llm.provider}/${config.llm.model}`,
    tts: `${config.tts.provider}/${config.tts.model}`,
    groups,
    articles,
    episodes,
  };
}
