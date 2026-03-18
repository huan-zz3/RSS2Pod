import Fastify from 'fastify';
import cors from '@fastify/cors';
import fastifyStatic from '@fastify/static';
import { join } from 'path';
import pino from 'pino';
import { loadConfig } from '../shared/config/index.js';
import { DatabaseManager } from '../infrastructure/database/DatabaseManager.js';
import { GroupRepository } from '../repositories/GroupRepository.js';
import { PodcastFeedGenerator } from '../services/feed/PodcastFeedGenerator.js';

const logger = pino({
  name: 'api',
  timestamp: () => `,"time":"${new Date(new Date().getTime() + 8 * 3600 * 1000).toISOString().replace('Z', '+08:00')}"`,
});

export interface ApiOptions {
  host?: string;
  port?: number;
}

export async function createApiServer(options: ApiOptions = {}) {
  const config = loadConfig();
  
  const host = options.host || config.api.host;
  const port = options.port || config.api.port;

  const fastify = Fastify({
    logger: {
      level: config.logging.level,
    },
    // VPN 环境优化：增加超时配置，避免连接提前关闭
    keepAliveTimeout: 60 * 1000,      // 60 秒 keep-alive（默认 5 秒）
    connectionTimeout: 60 * 1000,     // 60 秒连接超时
    bodyLimit: 10 * 1024 * 1024,      // 10MB 响应体限制（默认 1MB）
    maxRequestsPerSocket: 0,          // 无限制
  });

  await fastify.register(cors, {
    origin: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
  });

  const mediaPath = join(process.cwd(), config.media.basePath);
  await fastify.register(fastifyStatic, {
    root: mediaPath,
    prefix: '/api/media/',
    decorateReply: false,
  });

  const dbManager = new DatabaseManager(config.database.path);
  dbManager.initialize();
  const db = dbManager.getDb();
  const groupRepo = new GroupRepository(db);
  const feedGenerator = new PodcastFeedGenerator();

  fastify.get('/api/health', async () => {
    return { status: 'ok', timestamp: new Date().toISOString() };
  });

  fastify.get('/api/groups', async () => {
    const groups = groupRepo.findAll();
    return { groups: groups.map(g => ({
      id: g.id,
      name: g.name,
      description: g.description,
      enabled: g.enabled,
      triggerType: g.triggerType,
      sourceCount: g.sourceIds.length,
    })) };
  });

  fastify.get('/api/groups/:id', async (request, reply) => {
    const { id } = request.params as { id: string };
    const group = groupRepo.findById(id);
    
    if (!group) {
      return reply.code(404).send({ error: 'Group not found' });
    }
    
    return { group };
  });

  fastify.get('/api/feeds/:groupId', async (request, reply) => {
    try {
      const { groupId } = request.params as { groupId: string };
      
      const group = groupRepo.findById(groupId);
      if (!group) {
        return reply.code(404).send({ error: 'Group not found' });
      }

      const baseUrl = config.api.baseUrl;
      
      const db = dbManager.getDb();
      const episodes = db.prepare(`
        SELECT * FROM episodes 
        WHERE group_id = ? 
        ORDER BY pub_date DESC 
        LIMIT 10
      `).all(groupId) as Array<{
        id: string;
        title: string;
        script: string;
        audio_path?: string;
        pub_date: string;
        guid: string;
      }>;

      logger.info({ groupId, episodeCount: episodes.length }, 'Fetching episodes for feed');

      const feedItems = episodes
        .filter(ep => ep.audio_path)
        .map(ep => {
          // Convert absolute path to relative path for media URL
          const relativePath = ep.audio_path!.startsWith('/') 
            ? ep.audio_path!.replace(/^.*?data\/media\//, '')
            : ep.audio_path;
          
          try {
            const scriptData = JSON.parse(ep.script);
            return {
              title: ep.title,
              description: scriptData.segments?.[0]?.text || ep.title,
              enclosure: {
                url: `${baseUrl}/api/media/${relativePath}`,
                length: 0,
                type: 'audio/mpeg',
              },
              pubDate: new Date(ep.pub_date).toISOString(),
              guid: ep.guid,
            };
          } catch (parseError) {
            logger.warn({ episodeId: ep.id, error: parseError }, 'Failed to parse script, using title as description');
            return {
              title: ep.title,
              description: ep.title,
              enclosure: {
                url: `${baseUrl}/api/media/${relativePath}`,
                length: 0,
                type: 'audio/mpeg',
              },
              pubDate: new Date(ep.pub_date).toISOString(),
              guid: ep.guid,
            };
          }
        });

      logger.info({ groupId, filteredEpisodeCount: feedItems.length }, 'Filtered episodes with audio');

      const feedConfig = {
        groupId,
        title: group.name,
        description: group.description || `${group.name} Podcast`,
        imageUrl: '',
        siteUrl: `${baseUrl}/api/feeds/${groupId}`,
        author: group.name,
        itunesAuthor: group.name,
        itunesExplicit: 'no' as const,
        language: 'en',
        categories: ['News'],
      };

      logger.info({ feedConfig }, 'Generating feed');
      const feedXml = feedGenerator.generateFeed(feedItems, feedConfig);
      
      // 显式设置 Content-Length，避免 VPN/代理对 Chunked Transfer Encoding 的处理问题
      const contentLength = Buffer.byteLength(feedXml, 'utf8');
      logger.info({ contentLength, remoteAddress: request.ip }, 'Sending feed response');
      reply.header('Content-Length', contentLength);
      reply.type('application/rss+xml; charset=utf-8');
      return feedXml;
    } catch (error) {
      logger.error({ error, message: error instanceof Error ? error.message : 'Unknown error' }, 'Failed to generate feed');
      throw error;
    }
  });

  fastify.post('/api/groups/:id/generate', async (request, reply) => {
    const { id } = request.params as { id: string };
    
    const group = groupRepo.findById(id);
    if (!group) {
      return reply.code(404).send({ error: 'Group not found' });
    }

    if (!group.enabled) {
      return reply.code(400).send({ error: 'Group is disabled' });
    }

    logger.info({ groupId: id }, 'Pipeline generation triggered');
    
    return { 
      status: 'started', 
      groupId: id,
      message: 'Pipeline execution started'
    };
  });

  fastify.get('/api/stats', async () => {
    const db = dbManager.getDb();
    
    const articles = db.prepare('SELECT COUNT(*) as count FROM articles').get() as { count: number };
    const groups = db.prepare('SELECT COUNT(*) as count FROM groups').get() as { count: number };
    const episodes = db.prepare('SELECT COUNT(*) as count FROM episodes').get() as { count: number };
    
    return {
      articles: articles.count,
      groups: groups.count,
      episodes: episodes.count,
    };
  });

  fastify.setErrorHandler((error, _request, reply) => {
    logger.error({ 
      error,
      message: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined
    }, 'API error');
    reply.code(500).send({ 
      error: 'Internal server error',
      message: process.env.NODE_ENV === 'development' && error instanceof Error ? error.message : undefined
    });
  });

  return {
    fastify,
    start: async () => {
      try {
        await fastify.listen({ host, port });
        logger.info({ host, port }, 'API server started');
      } catch (err) {
        logger.error({ err }, 'Failed to start API server');
        throw err;
      }
    },
    close: async () => {
      await fastify.close();
      dbManager.close();
      logger.info('API server closed');
    },
  };
}

// Auto-start when executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  // Handle command-line arguments
  const args = process.argv.slice(2);
  
  if (args.includes('-h') || args.includes('--help')) {
    console.log(`
RSS2Pod API Server

Usage: npm run api [options]

Options:
  -h, --help     Show this help message
  --port <num>   Specify port number (default: 3000)
  --host <host>  Specify host (default: 0.0.0.0)

Environment Variables:
  PORT           Override default port
  HOST           Override default host

Examples:
  npm run api                      # Start with default settings
  npm run api -- --port 3001       # Start on port 3001
  PORT=3001 npm run api            # Use environment variable

After starting:
  - Health check: curl http://localhost:3000/api/health
  - Get feed:     curl http://localhost:3000/api/feeds/<groupId>
  - List groups:  curl http://localhost:3000/api/groups
`);
    process.exit(0);
  }
  
  const portArg = args.find((arg, i) => 
    (arg === '--port' || arg === '-p') && args[i + 1]
  );
  const port: number | undefined = portArg 
    ? parseInt(args[args.indexOf(portArg) + 1]!, 10) 
    : process.env.PORT 
      ? parseInt(process.env.PORT, 10) 
      : undefined;
  
  const hostArg = args.find((arg, i) => 
    (arg === '--host' || arg === '-H') && args[i + 1]
  );
  const host: string | undefined = hostArg 
    ? args[args.indexOf(hostArg) + 1]!
    : process.env.HOST ?? undefined;

  createApiServer({ host, port }).then(async (server) => {
    await server.start();
    
    const shutdown = async (signal: string) => {
      logger.info({ signal }, 'Received shutdown signal, closing server...');
      await server.close();
      logger.info('Server shut down complete');
      process.exit(0);
    };
    
    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGTERM', () => shutdown('SIGTERM'));
    process.on('SIGBREAK', () => shutdown('SIGBREAK'));
  }).catch((error) => {
    if (error.code === 'EADDRINUSE') {
      logger.error(`Port ${error.port} is already in use. Try one of these:`);
      logger.error(`  1. Stop the existing process: lsof -i :${error.port} | grep LISTEN | awk '{print $2}' | xargs kill`);
      logger.error(`  2. Use a different port: npm run api -- --port ${error.port + 1}`);
      logger.error(`  3. Set PORT env variable: PORT=${error.port + 1} npm run api`);
    } else {
      logger.error({ error }, 'Failed to start API server');
    }
    process.exit(1);
  });
}
