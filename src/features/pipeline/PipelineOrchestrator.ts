import { DatabaseManager } from '../../infrastructure/database/DatabaseManager.js';
import { ArticleRepository } from '../../repositories/ArticleRepository.js';
import { GroupRepository } from '../../repositories/GroupRepository.js';
import { Group } from '../../repositories/GroupRepository.js';
import { DashScopeService } from '../../services/llm/DashScopeService.js';
import { SiliconFlowService } from '../../services/tts/SiliconFlowService.js';
import { PodcastFeedGenerator } from '../../services/feed/PodcastFeedGenerator.js';
import type { FeedItem, FeedConfig } from '../../services/feed/PodcastFeedGenerator.js';
import { loadConfig } from '../../shared/config/index.js';
import { getEventBus } from '../../features/events/EventBus.js';
import { join, dirname } from 'path';
import { mkdirSync, writeFileSync, statSync } from 'fs';
import { writeFile } from 'fs/promises';
import { exec } from 'child_process';
import pino from 'pino';

const logger = pino({
  name: 'pipeline',
  timestamp: () => `,"time":"${new Date(new Date().getTime() + 8 * 3600 * 1000).toISOString().replace('Z', '+08:00')}"`,
});

export type PipelineStage = 'source-summary' | 'group-aggregate' | 'script' | 'audio' | 'episode' | 'feed';

export interface PipelineConfig {
  maxConcurrentGroups: number;
}

export interface PipelineRun {
  id: string;
  groupId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  startedAt?: Date;
  completedAt?: Date;
  stages: Record<PipelineStage, 'pending' | 'running' | 'completed' | 'failed'>;
  articlesCount: number;
  error?: string;
}

export class PipelineOrchestrator {
  private dbManager: DatabaseManager;
  private groupRepo: GroupRepository;
  private llmService: DashScopeService;
  private ttsService: SiliconFlowService;
  private eventBus = getEventBus();
  private maxConcurrentGroups: number;
  private maxArticlesPerRun: number;
  private activeRuns: Map<string, PipelineRun> = new Map();

  constructor(dbManager: DatabaseManager, config: PipelineConfig) {
    this.dbManager = dbManager;
    this.maxConcurrentGroups = config.maxConcurrentGroups;
    
    const appConfig = loadConfig();
    this.maxArticlesPerRun = appConfig.pipeline.maxArticlesPerRun;
    this.llmService = new DashScopeService(appConfig.llm);
    this.ttsService = new SiliconFlowService(appConfig.tts);
    
    const db = dbManager.getDb();
    this.groupRepo = new GroupRepository(db);
  }

  async runForGroup(groupId: string): Promise<PipelineRun> {
    const group = this.groupRepo.findById(groupId);
    if (!group) throw new Error(`Group not found: ${groupId}`);
    if (!group.enabled) throw new Error(`Group is disabled: ${groupId}`);
    if (this.activeRuns.size >= this.maxConcurrentGroups) throw new Error(`Max concurrent groups reached`);

    const run: PipelineRun = {
      id: `run-${new Date().toISOString().replace(/[:.]/g, '-')}-${groupId}`,
      groupId,
      status: 'pending',
      stages: { 'source-summary': 'pending', 'group-aggregate': 'pending', script: 'pending', audio: 'pending', episode: 'pending', feed: 'pending' },
      articlesCount: 0,
    };

    this.activeRuns.set(run.id, run);

    const db = this.dbManager.getDb();
    db.prepare(`
      INSERT INTO pipeline_runs (id, group_id, status, stages, articles_count, started_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `).run(run.id, group.id, run.status, JSON.stringify(run.stages), run.articlesCount, null);

    try {
      await this.executePipeline(run, group);
      run.status = 'completed';
      run.completedAt = new Date();
      logger.info({ groupId, runId: run.id }, 'Pipeline completed');

      this.eventBus.emit('pipeline:completed', {
        groupId,
        runId: run.id,
      }, 'PipelineOrchestrator');

      db.prepare(`
        UPDATE pipeline_runs 
        SET status = ?, completed_at = ?, articles_count = ?
        WHERE id = ?
      `).run(run.status, run.completedAt.getTime() / 1000, run.articlesCount, run.id);
    } catch (error) {
      run.status = 'failed';
      run.completedAt = new Date();
      run.error = error instanceof Error ? error.message : String(error);
      logger.error({ groupId, runId: run.id, error }, 'Pipeline failed');

      this.eventBus.emit('pipeline:failed', {
        groupId,
        runId: run.id,
        error: run.error,
      }, 'PipelineOrchestrator');

      db.prepare(`
        UPDATE pipeline_runs 
        SET status = ?, completed_at = ?, error = ?
        WHERE id = ?
      `).run(run.status, run.completedAt.getTime() / 1000, run.error, run.id);
      throw error;
    } finally {
      this.activeRuns.delete(run.id);
    }

    return run;
  }

  private async executePipeline(run: PipelineRun, group: Group): Promise<void> {
    const stages: PipelineStage[] = ['source-summary', 'group-aggregate', 'script', 'audio', 'episode', 'feed'];
    run.status = 'running';
    run.startedAt = new Date();

    this.eventBus.emit('pipeline:started', {
      groupId: group.id,
      runId: run.id,
    }, 'PipelineOrchestrator');

    const db = this.dbManager.getDb();
    db.prepare(`
      UPDATE pipeline_runs 
      SET status = ?, started_at = ?
      WHERE id = ?
    `).run(run.status, run.startedAt.getTime() / 1000, run.id);

    for (const stage of stages) {
      run.stages[stage] = 'running';
      try {
        await this.executeStage(stage, run, group);
        run.stages[stage] = 'completed';
      } catch (error) {
        run.stages[stage] = 'failed';
        throw error;
      }
    }
  }

  private async executeStage(stage: PipelineStage, run: PipelineRun, group: Group): Promise<void> {
    const startTime = new Date();
    logger.info({ stage, groupId: group.id, runId: run.id, timestamp: startTime.toISOString() }, 'Executing pipeline stage');

    this.eventBus.emit(`pipeline:${stage}:started` as any, {
      groupId: group.id,
      stage,
      runId: run.id,
    }, 'PipelineOrchestrator');

    try {
      switch (stage) {
        case 'source-summary': await this.executeSourceSummary(run, group); break;
        case 'group-aggregate': await this.executeGroupAggregate(run, group); break;
        case 'script': await this.executeScript(run, group); break;
        case 'audio': await this.executeAudio(run, group); break;
        case 'episode': await this.executeEpisode(run, group); break;
        case 'feed': await this.executeFeed(run, group); break;
      }
      
      // Add small delay between stages to avoid API rate limiting
      if (stage !== 'feed') {
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      const elapsed = (Date.now() - startTime.getTime()) / 1000;
      logger.info({ stage, groupId: group.id, elapsed }, 'Pipeline stage completed');

      this.eventBus.emit(`pipeline:${stage}:completed` as any, {
        groupId: group.id,
        stage,
        runId: run.id,
      }, 'PipelineOrchestrator');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      const errorStack = error instanceof Error ? error.stack : undefined;
      
      logger.error({ 
        stage, 
        groupId: group.id, 
        runId: run.id,
        error: errorMessage,
        stack: errorStack,
        timestamp: new Date().toISOString()
      }, `Pipeline stage failed: ${stage}`);

      this.eventBus.emit('pipeline:failed', {
        groupId: group.id,
        stage,
        runId: run.id,
        error: errorMessage,
      }, 'PipelineOrchestrator');
      
      throw error;
    }
  }

  private async executeSourceSummary(run: PipelineRun, group: Group): Promise<void> {
    const db = this.dbManager.getDb();
    const articleRepo = new ArticleRepository(db);
    // 使用配置中的限制，避免 LLM 超时和处理质量下降
    const unprocessed = articleRepo.findUnprocessed(group.id, this.maxArticlesPerRun);

    if (unprocessed.length === 0) {
      const errorMessage = `No unprocessed articles found for group ${group.id} (${group.name}). Please ensure the group has sources and articles are synced. Run 'npm run cli -- source:list' to view available sources.`;
      logger.warn({ groupId: group.id, runId: run.id }, errorMessage);
      throw new Error(errorMessage);
    }

    const sourceGroups = new Map<string, typeof unprocessed>();
    for (const article of unprocessed) {
      const existing = sourceGroups.get(article.sourceId) ?? [];
      existing.push(article);
      sourceGroups.set(article.sourceId, existing);
    }

    for (const [sourceId, articles] of sourceGroups.entries()) {
      const articlesText = articles.map(a => `${a.title}\n${a.content}`).join('\n\n');
      const response = await this.llmService.generateSummary(articlesText, { sourceName: sourceId, articleCount: articles.length, style: 'balanced' });

      db.prepare(`INSERT INTO source_summaries (id, group_id, source_id, summary, article_ids, run_id) VALUES (?, ?, ?, ?, ?, ?)`)
        .run(`src-sum-${run.id}-${sourceId}`, group.id, sourceId, response.content, JSON.stringify(articles.map(a => a.id)), run.id);

      for (const article of articles) {
        articleRepo.markProcessed(article.id, group.id);
      }
    }

    logger.info({ groupId: group.id, sourceCount: sourceGroups.size }, 'Source summaries generated');
  }

  private async executeGroupAggregate(run: PipelineRun, group: Group): Promise<void> {
    const db = this.dbManager.getDb();
    const summaries = db.prepare(`SELECT * FROM source_summaries WHERE group_id = ? AND run_id = ?`).all(group.id, run.id) as Array<{ summary: string; id: string }>;
    const groupSummary = summaries.map(s => s.summary).join('\n\n');
    
    db.prepare(`INSERT INTO group_summaries (id, group_id, summary, source_summary_ids, run_id) VALUES (?, ?, ?, ?, ?)`)
      .run(`grp-sum-${run.id}`, group.id, groupSummary, JSON.stringify(summaries.map(s => s.id)), run.id);

    logger.info({ groupId: group.id }, 'Group summary aggregated');
  }

  private async executeScript(run: PipelineRun, group: Group): Promise<void> {
    const db = this.dbManager.getDb();
    const summary = db.prepare(`SELECT * FROM group_summaries WHERE group_id = ? AND run_id = ?`).get(group.id, run.id) as { summary: string } | undefined;
    if (!summary) throw new Error('No group summary found');

    const response = await this.llmService.generateScript(summary.summary, {
      groupStructure: group.podcastStructure.type,
      learningMode: group.learningMode,
      hostName: group.podcastStructure.hostName,
      guestName: group.podcastStructure.guestName,
    });

    const scriptContent = {
      type: group.podcastStructure.type,
      host: group.podcastStructure.hostName ?? 'Host',
      guest: group.podcastStructure.guestName ?? 'Guest',
      segments: this.parseScriptSegments(response.content),
    };

    const mediaDir = join(process.cwd(), 'data', 'media', group.id, `episode_${Date.now()}`);
    mkdirSync(mediaDir, { recursive: true });

    const scriptJsonPath = join(mediaDir, 'script.json');
    writeFileSync(scriptJsonPath, JSON.stringify(scriptContent, null, 2));

    const scriptTxtPath = join(mediaDir, 'script.txt');
    const plainText = scriptContent.segments.map(s => s.text).join('\n\n');
    writeFileSync(scriptTxtPath, plainText);

    const pubDate = new Date();
    const guid = `rss2pod-${group.id}-${pubDate.toISOString()}`;
    db.prepare(`INSERT INTO episodes (id, group_id, title, script, script_path, guid, pub_date) VALUES (?, ?, ?, ?, ?, ?, ?)`)
      .run(`script-${run.id}`, group.id, `RSS2Pod Episode - ${pubDate.toISOString().split('T')[0]}`, JSON.stringify(scriptContent), scriptJsonPath, guid, pubDate.toISOString());

    logger.info({ groupId: group.id, scriptJsonPath, scriptTxtPath }, 'Script generated and saved');
  }

  private parseScriptSegments(scriptText: string): Array<{ speaker: string; text: string }> {
    const segments: Array<{ speaker: string; text: string }> = [];
    const lines = scriptText.split('\n').filter(line => line.trim().length > 0);
    let currentSpeaker = 'host';
    let currentText = '';
    
    for (const line of lines) {
      const speakerMatch = line.match(/^(Host|Guest|主持人 | 嘉宾):/i);
      if (speakerMatch) {
        if (currentText.trim()) segments.push({ speaker: currentSpeaker, text: currentText.trim() });
        currentSpeaker = speakerMatch[1]?.toLowerCase() === 'host' || speakerMatch[1] === '主持人' ? 'host' : 'guest';
        currentText = line.replace(/^(Host|Guest|主持人 | 嘉宾):/i, '').trim();
      } else {
        currentText += ' ' + line;
      }
    }
    
    if (currentText.trim()) segments.push({ speaker: currentSpeaker, text: currentText.trim() });
    return segments.length > 0 ? segments : [{ speaker: 'host', text: scriptText }];
  }

  private async executeAudio(run: PipelineRun, group: Group): Promise<void> {
    const db = this.dbManager.getDb();
    const episode = db.prepare(`SELECT * FROM episodes WHERE group_id = ? AND script IS NOT NULL ORDER BY created_at DESC LIMIT 1`).get(group.id) as { id: string; script: string; script_path?: string } | undefined;
    if (!episode) throw new Error('No episode script found');

    const scriptContent = JSON.parse(episode.script);
    const mediaDir = episode.script_path ? dirname(episode.script_path) : join(process.cwd(), 'data', 'media', group.id, `episode_${Date.now()}`);
    const audioSegments: string[] = [];
    const totalSegments = scriptContent.segments.length;
    
    logger.info({ 
      groupId: group.id, 
      totalSegments,
      scriptLength: episode.script.length 
    }, 'Starting audio synthesis');
    
    this.eventBus.emit('pipeline:audio:started', {
      groupId: group.id,
      stage: 'audio',
      runId: run.id,
    }, 'PipelineOrchestrator');
    
    for (let i = 0; i < scriptContent.segments.length; i++) {
      const segment = scriptContent.segments[i]!;
      const speaker = segment.speaker === 'host' ? 'host' : 'guest';
      const segmentPath = join(mediaDir, `segment_${String(i + 1).padStart(3, '0')}_${speaker}.mp3`);
      
      const textPreview = segment.text.length > 100 
        ? `${segment.text.substring(0, 100)}...` 
        : segment.text;
      
      logger.info({ 
        segment: i + 1, 
        total: totalSegments,
        speaker,
        textLength: segment.text.length,
        preview: textPreview.replace(/\n/g, ' ')
      }, `Synthesizing segment ${i + 1}/${totalSegments}`);
      
      const response = await this.ttsService.synthesize(segment.text, segmentPath, { segment: true });
      audioSegments.push(response.audioPath);
      
      this.eventBus.emit('pipeline:audio:segment-completed' as any, {
        groupId: group.id,
        segmentIndex: i + 1,
        totalSegments,
        duration: response.duration,
      }, 'PipelineOrchestrator');
    }

    const finalAudioPath = join(mediaDir, 'final.mp3');
    
    logger.info({ 
      groupId: group.id,
      segments: audioSegments.length,
      output: finalAudioPath 
    }, 'Merging audio segments with ffmpeg');
    
    // Calculate estimated total duration
    const totalDuration = await audioSegments.reduce(async (acc, _path) => {
      return (await acc) + 30;
    }, Promise.resolve(0));
    
    // Create segments list file for ffmpeg concat demuxer
    const segmentsListPath = join(mediaDir, 'segments.txt');
    const segmentsContent = audioSegments
      .map(p => `file '${p.replace(/'/g, "'\\''")}'`)
      .join('\n');
    await writeFile(segmentsListPath, segmentsContent);
    
    // Merge segments using ffmpeg
    await new Promise<void>((resolve, reject) => {
      exec(
        `ffmpeg -f concat -safe 0 -i "${segmentsListPath}" -c copy "${finalAudioPath}"`,
        (error, stdout, stderr) => {
          if (error) {
            logger.error({ error, stderr }, 'ffmpeg merge failed');
            reject(error);
          } else {
            logger.info({ stdout, stderr }, 'ffmpeg merge completed');
            resolve();
          }
        }
      );
    });
    
    // Calculate actual audio duration using ffprobe
    const duration = await new Promise<number>((resolve) => {
      exec(
        `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${finalAudioPath}"`,
        (error, stdout) => {
          if (error || !stdout) {
            resolve(totalDuration); // Fallback to estimated
          } else {
            resolve(parseFloat(stdout.trim()) || totalDuration);
          }
        }
      );
    });
    
    // Only update database after ffmpeg succeeds
    db.prepare(`UPDATE episodes SET audio_path = ?, duration_seconds = ? WHERE id = ?`)
      .run(finalAudioPath, duration, episode.id);
      
    logger.info({ 
      groupId: group.id, 
      finalAudioPath, 
      duration 
    }, 'Audio synthesis completed');
    
    this.eventBus.emit('pipeline:audio:completed', {
      groupId: group.id,
      stage: 'audio',
      runId: run.id,
    }, 'PipelineOrchestrator');
  }

  private async executeEpisode(_run: PipelineRun, group: Group): Promise<void> {
    logger.info({ groupId: group.id }, 'Episode saved');
  }

  private async executeFeed(_run: PipelineRun, group: Group): Promise<void> {
    const db = this.dbManager.getDb();
    const episodes = db.prepare(`
      SELECT * FROM episodes 
      WHERE group_id = ? AND audio_path IS NOT NULL 
      ORDER BY pub_date DESC
    `).all(group.id) as Array<{
      id: string;
      title: string;
      script: string;
      audio_path: string;
      duration_seconds: number;
      guid: string;
      pub_date: string;
    }>;
    
    if (episodes.length === 0) {
      logger.warn({ groupId: group.id }, 'No episodes with audio found for feed generation');
      return;
    }

    const feedGen = new PodcastFeedGenerator();
    const config: FeedConfig = {
      groupId: group.id,
      title: group.name,
      description: group.description || 'Generated podcast feed',
      imageUrl: undefined,
      siteUrl: 'http://localhost:3000',
      author: 'RSS2Pod',
      itunesAuthor: 'RSS2Pod',
      itunesExplicit: 'no',
      itunesOwnerName: 'RSS2Pod',
      itunesOwnerEmail: 'noreply@localhost',
      itunesCategory: 'Technology',
      language: 'en',
    };

    const feedItems: FeedItem[] = episodes.map((episode) => {
      const scriptContent = episode.script ? JSON.parse(episode.script) : null;
      const relativePath = episode.audio_path.replace(/^.*[/\\]data[/\\]media[/\\]/, '');
      
      return {
        title: episode.title || `${group.name} - ${new Date(episode.pub_date).toLocaleDateString()}`,
        description: scriptContent?.summary || 'Generated episode',
        enclosure: {
          url: `http://localhost:3000/api/media/${relativePath}`,
          length: statSync(episode.audio_path).size,
          type: 'audio/mpeg',
        },
        pubDate: episode.pub_date,
        guid: episode.guid,
      };
    });

    feedGen.generateFeed(feedItems, config);
    logger.info({ groupId: group.id, feedPath: `data/media/feeds/${group.id}.xml`, episodeCount: feedItems.length }, 'Feed generated');
  }

  getActiveRuns(): PipelineRun[] {
    return Array.from(this.activeRuns.values());
  }

  /**
   * Stop a running pipeline by runId
   * @param runId - The pipeline run ID to stop
   * @returns Information about the stopped pipeline
   * @throws Error if the pipeline run is not found or not running
   */
  stopPipeline(runId: string): { runId: string; groupId: string; status: 'cancelled' } {
    const db = this.dbManager.getDb();
    const run = this.activeRuns.get(runId);
    
    if (run) {
      if (run.status !== 'running') {
        throw new Error(`Pipeline run is not running (current status: ${run.status})`);
      }
      
      this.activeRuns.delete(runId);
      
      this.eventBus.emit('pipeline:cancelled', {
        runId,
        groupId: run.groupId,
        completedAt: new Date(),
      }, 'PipelineOrchestrator');
      
      logger.info({ runId, groupId: run.groupId }, 'Pipeline cancelled by user');
    } else {
      const dbRun = db.prepare(`
        SELECT id, group_id, status FROM pipeline_runs WHERE id = ?
      `).get(runId) as { id: string; group_id: string; status: string } | undefined;
      
      if (!dbRun) {
        throw new Error(`Pipeline run not found: ${runId}`);
      }
      
      if (dbRun.status !== 'running') {
        throw new Error(`Pipeline run is not running (current status: ${dbRun.status})`);
      }
      
      logger.warn({ runId, groupId: dbRun.group_id }, 'Cancelling stuck pipeline run');
    }
    
    db.prepare(`
      UPDATE pipeline_runs 
      SET status = ?, completed_at = ?
      WHERE id = ?
    `).run('cancelled', new Date().getTime() / 1000, runId);
    
    const dbRun = db.prepare('SELECT group_id FROM pipeline_runs WHERE id = ?').get(runId) as { group_id: string } | undefined;
    const groupId = run?.groupId || dbRun?.group_id || 'unknown';
    
    return {
      runId,
      groupId,
      status: 'cancelled',
    };
  }
}
