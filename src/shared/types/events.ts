/**
 * Event-driven architecture types for RSS2Pod
 */

/** Base event structure */
export interface AppEvent<T = unknown> {
  id: string;
  type: EventType;
  timestamp: Date;
  payload: T;
  source: string;
  correlationId?: string;
  metadata?: EventMetadata;
}

/** Event metadata */
export interface EventMetadata {
  groupId?: string;
  userId?: string;
  priority?: 'low' | 'normal' | 'high';
  [key: string]: unknown;
}

/** Event type enumeration */
export type EventType =
  // Pipeline events
  | 'pipeline:started'
  | 'pipeline:fetch:started'
  | 'pipeline:fetch:completed'
  | 'pipeline:source-summary:started'
  | 'pipeline:source-summary:completed'
  | 'pipeline:group-aggregate:started'
  | 'pipeline:group-aggregate:completed'
  | 'pipeline:script:started'
  | 'pipeline:script:completed'
  | 'pipeline:audio:started'
  | 'pipeline:audio:completed'
  | 'pipeline:episode:started'
  | 'pipeline:episode:completed'
  | 'pipeline:feed:started'
  | 'pipeline:feed:completed'
  | 'pipeline:completed'
  | 'pipeline:failed'
  
  // Article events
  | 'article:fetched'
  | 'article:cached'
  | 'article:processed'
  
  // Group events
  | 'group:created'
  | 'group:updated'
  | 'group:deleted'
  | 'group:enabled'
  | 'group:disabled'
  
  // Episode events
  | 'episode:created'
  | 'episode:published'
  | 'episode:expired'
  | 'episode:deleted'
  
  // Trigger events
  | 'trigger:time'
  | 'trigger:count'
  | 'trigger:llm'
  
  // Error events
  | 'error:pipeline'
  | 'error:service'
  | 'error:database';

/** Pipeline stage enumeration */
export type PipelineStage =
  | 'fetch'
  | 'source-summary'
  | 'group-aggregate'
  | 'script'
  | 'audio'
  | 'episode'
  | 'feed';

/** Pipeline event payload */
export interface PipelineEventPayload {
  groupId: string;
  stage?: PipelineStage;
  runId?: string;
  articlesCount?: number;
  error?: string;
}

/** Article event payload */
export interface ArticleEventPayload {
  groupId: string;
  articleIds: string[];
  sourceId?: string;
  count?: number;
}

/** Group event payload */
export interface GroupEventPayload {
  groupId: string;
  name?: string;
  [key: string]: unknown;
}

/** Episode event payload */
export interface EpisodeEventPayload {
  episodeId: string;
  groupId: string;
  title?: string;
  audioPath?: string;
  scriptPath?: string;
}

/** Error event payload */
export interface ErrorEventPayload {
  groupId?: string;
  stage?: PipelineStage;
  error: string;
  stack?: string;
  context?: Record<string, unknown>;
}

/** Trigger event payload */
export interface TriggerEventPayload {
  groupId: string;
  triggerType: 'time' | 'count' | 'llm';
  triggered: boolean;
  reason?: string;
}

/** Type-safe event payload mapping */
export interface EventPayloadMap {
  // Pipeline
  'pipeline:started': PipelineEventPayload;
  'pipeline:fetch:started': PipelineEventPayload;
  'pipeline:fetch:completed': PipelineEventPayload;
  'pipeline:source-summary:started': PipelineEventPayload;
  'pipeline:source-summary:completed': PipelineEventPayload;
  'pipeline:group-aggregate:started': PipelineEventPayload;
  'pipeline:group-aggregate:completed': PipelineEventPayload;
  'pipeline:script:started': PipelineEventPayload;
  'pipeline:script:completed': PipelineEventPayload;
  'pipeline:audio:started': PipelineEventPayload;
  'pipeline:audio:completed': PipelineEventPayload;
  'pipeline:episode:started': PipelineEventPayload;
  'pipeline:episode:completed': PipelineEventPayload;
  'pipeline:feed:started': PipelineEventPayload;
  'pipeline:feed:completed': PipelineEventPayload;
  'pipeline:completed': PipelineEventPayload;
  'pipeline:failed': PipelineEventPayload & { error: string };
  
  // Articles
  'article:fetched': ArticleEventPayload;
  'article:cached': ArticleEventPayload;
  'article:processed': ArticleEventPayload;
  
  // Groups
  'group:created': GroupEventPayload;
  'group:updated': GroupEventPayload;
  'group:deleted': { groupId: string };
  'group:enabled': { groupId: string };
  'group:disabled': { groupId: string };
  
  // Episodes
  'episode:created': EpisodeEventPayload;
  'episode:published': EpisodeEventPayload;
  'episode:expired': { episodeId: string; groupId: string };
  'episode:deleted': { episodeId: string; groupId: string };
  
  // Triggers
  'trigger:time': TriggerEventPayload;
  'trigger:count': TriggerEventPayload;
  'trigger:llm': TriggerEventPayload;
  
  // Errors
  'error:pipeline': ErrorEventPayload;
  'error:service': ErrorEventPayload;
  'error:database': ErrorEventPayload;
}

/** Type-safe event creator */
export function createEvent<T extends EventType>(
  type: T,
  payload: EventPayloadMap[T],
  source: string,
  metadata?: EventMetadata
): AppEvent<EventPayloadMap[T]> {
  return {
    id: crypto.randomUUID(),
    type,
    timestamp: new Date(),
    payload,
    source,
    correlationId: metadata?.groupId ? `grp-${metadata.groupId}-${Date.now()}` : undefined,
    metadata,
  };
}
