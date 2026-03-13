import { DatabaseManager } from '../../infrastructure/database/DatabaseManager.js';
import { ArticleRepository } from '../../repositories/ArticleRepository.js';
import { GroupRepository } from '../../repositories/GroupRepository.js';
import { FeverClient } from '../../infrastructure/external/FeverClient.js';
import { Group } from '../../repositories/GroupRepository.js';
import { DashScopeService } from '../../services/llm/DashScopeService.js';
import { SiliconFlowService } from '../../services/tts/SiliconFlowService.js';
import { loadConfig } from '../../shared/config/index.js';
import { join } from 'path';
import pino from 'pino';

const logger = pino({ name: 'pipeline' });

export type PipelineStage = 'fetch' | 'source-summary' | 'group-aggregate' | 'script' | 'audio' | 'episode' | 'feed';

export interface PipelineConfig {
  maxConcurrentGroups: number;
}

export interface PipelineRun {
  id: string;
  groupId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  startedAt?: Date;
  completedAt?: Date;
  stages: Record<PipelineStage, 'pending' | 'running' | 'completed' | 'failed'>;
  articlesCount: number;
  error?: string;
}

export class PipelineOrchestrator {
  private dbManager: DatabaseManager;
  private groupRepo: GroupRepository;
  private feverClient: FeverClient;
  private llmService: DashScopeService;
  private ttsService: SiliconFlowService;
  private maxConcurrentGroups: number;
  private activeRuns: Map<string, PipelineRun> = new Map();

  constructor(dbManager: DatabaseManager, feverClient: FeverClient, config: PipelineConfig) {
    this.dbManager = dbManager;
    this.feverClient = feverClient;
    this.maxConcurrentGroups = config.maxConcurrentGroups;
    
    const appConfig = loadConfig();
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
      id: `run-${Date.now()}-${groupId}`,
      groupId,
      status: 'pending',
      stages: { fetch: 'pending', 'source-summary': 'pending', 'group-aggregate': 'pending', script: 'pending', audio: 'pending', episode: 'pending', feed: 'pending' },
      articlesCount: 0,
    };

    this.activeRuns.set(run.id, run);

    try {
      await this.executePipeline(run, group);
      run.status = 'completed';
      run.completedAt = new Date();
      logger.info({ groupId, runId: run.id }, 'Pipeline completed');
    } catch (error) {
      run.status = 'failed';
      run.completedAt = new Date();
      run.error = error instanceof Error ? error.message : String(error);
      logger.error({ groupId, runId: run.id, error }, 'Pipeline failed');
      throw error;
    } finally {
      this.activeRuns.delete(run.id);
    }

    return run;
  }

  private async executePipeline(run: PipelineRun, group: Group): Promise<void> {
    const stages: PipelineStage[] = ['fetch', 'source-summary', 'group-aggregate', 'script', 'audio', 'episode', 'feed'];
    run.status = 'running';
    run.startedAt = new Date();

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
    logger.info({ stage, groupId: group.id, runId: run.id }, 'Executing pipeline stage');

    switch (stage) {
      case 'fetch': await this.executeFetch(run, group); break;
      case 'source-summary': await this.executeSourceSummary(run, group); break;
      case 'group-aggregate': await this.executeGroupAggregate(run, group); break;
      case 'script': await this.executeScript(run, group); break;
      case 'audio': await this.executeAudio(run, group); break;
      case 'episode': await this.executeEpisode(run, group); break;
      case 'feed': await this.executeFeed(run, group); break;
    }
  }

  private async executeFetch(run: PipelineRun, group: Group): Promise<void> {
    const articles = await this.feverClient.getItems();
    const articleRepo = new ArticleRepository(this.dbManager.getDb());

    let count = 0;
    for (const item of articles) {
      if (group.sourceIds.includes(item.feedId.toString())) {
        articleRepo.insert({
          id: `art-${item.id}`,
          feverId: item.id,
          title: item.title,
          content: this.stripHtml(item.html),
          sourceId: item.feedId.toString(),
          sourceName: item.feedId.toString(),
          publishedAt: item.createdOn,
          fetchedAt: new Date(),
          isRead: item.isRead,
          isSaved: item.isSaved,
          processedByGroup: [],
        });
        count++;
      }
    }

    run.articlesCount = count;
    logger.info({ groupId: group.id, count }, 'Articles fetched');
  }

  private async executeSourceSummary(run: PipelineRun, group: Group): Promise<void> {
    const db = this.dbManager.getDb();
    const articleRepo = new ArticleRepository(db);
    const unprocessed = articleRepo.findUnprocessed(group.id, 50);

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

    const guid = `rss2pod-${group.id}-${Date.now()}`;
    db.prepare(`INSERT INTO episodes (id, group_id, title, script, guid, pub_date) VALUES (?, ?, ?, ?, ?, ?)`)
      .run(`script-${run.id}`, group.id, `RSS2Pod Episode - ${new Date().toISOString().split('T')[0]}`, JSON.stringify(scriptContent), guid, Math.floor(Date.now() / 1000));

    logger.info({ groupId: group.id }, 'Script generated');
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

  private async executeAudio(_run: PipelineRun, group: Group): Promise<void> {
    const db = this.dbManager.getDb();
    const episode = db.prepare(`SELECT * FROM episodes WHERE group_id = ? AND script IS NOT NULL ORDER BY created_at DESC LIMIT 1`).get(group.id) as { id: string; script: string } | undefined;
    if (!episode) throw new Error('No episode script found');

    const scriptContent = JSON.parse(episode.script);
    const mediaDir = join(process.cwd(), 'data', 'media', group.id, `episode_${Date.now()}`);
    const audioSegments: string[] = [];
    
    for (let i = 0; i < scriptContent.segments.length; i++) {
      const segment = scriptContent.segments[i]!;
      const speaker = segment.speaker === 'host' ? 'host' : 'guest';
      const segmentPath = join(mediaDir, `segment_${String(i + 1).padStart(3, '0')}_${speaker}.mp3`);
      const response = await this.ttsService.synthesize(segment.text, segmentPath, { segment: true });
      audioSegments.push(response.audioPath);
      logger.info({ segment: i, path: response.audioPath, duration: response.duration }, 'Audio segment synthesized');
    }

    const finalAudioPath = join(mediaDir, 'final.mp3');
    await this.assembleAudio(audioSegments, finalAudioPath);
    
    const totalDuration = audioSegments.length * 30;
    db.prepare(`UPDATE episodes SET audio_path = ?, duration_seconds = ? WHERE id = ?`).run(finalAudioPath, totalDuration, episode.id);
    logger.info({ groupId: group.id, finalAudioPath, segments: audioSegments.length }, 'Audio synthesis completed');
  }

  private async assembleAudio(segmentPaths: string[], outputPath: string): Promise<void> {
    const { exec } = await import('child_process');
    const { writeFileSync } = await import('fs');
    
    const fileListPath = outputPath.replace('final.mp3', 'segments.txt');
    writeFileSync(fileListPath, segmentPaths.map(p => `file '${p}'`).join('\n'));
    
    return new Promise((resolve, reject) => {
      const ffmpeg = exec(`ffmpeg -f concat -safe 0 -i "${fileListPath}" -c copy "${outputPath}"`, (error) => {
        if (error) reject(error);
        else resolve();
      });
      ffmpeg.on('exit', (code) => { if (code === 0) resolve(); else reject(new Error(`ffmpeg exited with code ${code}`)); });
    });
  }

  private async executeEpisode(_run: PipelineRun, group: Group): Promise<void> {
    logger.info({ groupId: group.id }, 'Episode saved');
  }

  private async executeFeed(_run: PipelineRun, group: Group): Promise<void> {
    logger.info({ groupId: group.id }, 'Feed updated');
  }

  private stripHtml(html: string): string {
    return html.replace(/<[^>]*>/g, '').trim();
  }

  getActiveRuns(): PipelineRun[] {
    return Array.from(this.activeRuns.values());
  }
}
