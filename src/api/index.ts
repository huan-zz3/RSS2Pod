import Fastify from 'fastify';
import cors from '@fastify/cors';
import fastifyStatic from '@fastify/static';
import { join } from 'path';
import pino from 'pino';
import { loadConfig } from '../shared/config/index.js';
import { DatabaseManager } from '../infrastructure/database/DatabaseManager.js';
import { GroupRepository } from '../repositories/GroupRepository.js';
import { PodcastFeedGenerator } from '../services/feed/PodcastFeedGenerator.js';

const logger = pino({ name: 'api' });

export interface ApiOptions {
  host?: string;
  port?: number;
}

export async function createApiServer(options: ApiOptions = {}) {
  const config = loadConfig();
  
  const host = options.host || config.server.host;
  const port = options.port || config.server.port;

  const fastify = Fastify({
    logger: {
      level: config.logging.level,
    },
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
    const { groupId } = request.params as { groupId: string };
    
    const group = groupRepo.findById(groupId);
    if (!group) {
      return reply.code(404).send({ error: 'Group not found' });
    }

    const feedUrl = `http://${host}:${port}/api/feeds/${groupId}`;
    
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
      pub_date: number;
      guid: string;
    }>;

    const feedItems = episodes
      .filter(ep => ep.audio_path)
      .map(ep => ({
        title: ep.title,
        description: JSON.parse(ep.script).segments?.[0]?.text || ep.title,
        enclosure: {
          url: `http://${host}:${port}/api/media/${ep.audio_path}`,
          length: 0,
          type: 'audio/mpeg',
        },
        pubDate: new Date(ep.pub_date * 1000).toISOString(),
        guid: ep.guid,
      }));

    const feedConfig = {
      groupId,
      title: group.name,
      description: group.description || `${group.name} Podcast`,
      imageUrl: '',
      siteUrl: feedUrl,
      author: group.name,
      itunesAuthor: group.name,
      itunesExplicit: 'no' as const,
      language: 'en',
      categories: ['News'],
    };

    const feedXml = feedGenerator.generateFeed(feedItems, feedConfig);
    
    reply.type('application/rss+xml');
    return feedXml;
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
    logger.error({ error }, 'API error');
    reply.code(500).send({ error: 'Internal server error' });
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
