/**
 * Event Bus - Central event distribution system
 * 
 * Provides decoupled, async communication between components
 */

import pkg from 'eventemitter2';
const EventEmitter2 = pkg.EventEmitter2 || pkg;

import { AppEvent, EventType, EventPayloadMap, EventMetadata, createEvent } from '../../shared/types/events.js';
import { pino, Logger } from 'pino';

export type EventHandler<T extends EventType> = (event: AppEvent<EventPayloadMap[T]>) => Promise<void> | void;

interface Subscription {
  eventType: EventType;
  handler: EventHandler<EventType>;
  once?: boolean;
}

export interface EventBusConfig {
  wildcard?: boolean;
  maxListeners?: number;
  verbose?: boolean;
  logger?: Logger;
}

export class EventBus {
  private emitter: InstanceType<typeof EventEmitter2>;
  private logger: Logger;
  private subscriptions: Subscription[] = [];
  private eventHistory: AppEvent[] = [];
  private readonly maxHistorySize = 100;

  constructor(config: EventBusConfig = {}) {
    this.emitter = new EventEmitter2({
      wildcard: config.wildcard ?? true,
      maxListeners: config.maxListeners ?? 10,
    });
    
    this.logger = config.logger ?? pino({
      name: 'eventbus',
      level: process.env.LOG_LEVEL || 'info',
      timestamp: () => `,"time":"${new Date(new Date().getTime() + 8 * 3600 * 1000).toISOString().replace('Z', '+08:00')}"`,
    });
  }

  /**
   * Publish an event to all subscribers
   */
  publish<T extends EventType>(event: AppEvent<EventPayloadMap[T]>): void {
    // Add to history
    this.eventHistory.push(event);
    if (this.eventHistory.length > this.maxHistorySize) {
      this.eventHistory.shift();
    }

    // Log event
    this.logger.debug({ 
      eventId: event.id, 
      type: event.type, 
      groupId: event.metadata?.groupId 
    }, 'Event published');

    // Emit event
    this.emitter.emit(event.type, event);
    
    // Also emit wildcard event for type-based subscriptions
    this.emitter.emit('*', event);
  }

  /**
   * Create and publish an event
   */
  emit<T extends EventType>(
    type: T,
    payload: EventPayloadMap[T],
    source: string,
    metadata?: EventMetadata
  ): void {
    const event = createEvent(type, payload, source, metadata);
    this.publish(event);
  }

  /**
   * Subscribe to an event type
   */
  subscribe<T extends EventType>(
    eventType: T,
    handler: EventHandler<T>,
    options: { once?: boolean } = {}
  ): () => void {
    const subscription: Subscription = {
      eventType,
      handler: handler as EventHandler<EventType>,
      once: options.once,
    };
    
    this.subscriptions.push(subscription);

    const listener = async (event: AppEvent) => {
      try {
        await handler(event as AppEvent<EventPayloadMap[T]>);
      } catch (error) {
        this.logger.error({ 
          eventId: event.id, 
          type: event.type, 
          error 
        }, 'Event handler error');
        
        // Emit error event
        this.emit(
          'error:service',
          {
            error: error instanceof Error ? error.message : String(error),
            stack: error instanceof Error ? error.stack : undefined,
            context: { eventType, eventId: event.id },
          },
          'EventBus'
        );
      }
    };

    if (options.once) {
      this.emitter.once(eventType, listener);
    } else {
      this.emitter.on(eventType, listener);
    }

    // Return unsubscribe function
    return () => {
      this.emitter.off(eventType, listener);
      this.subscriptions = this.subscriptions.filter(s => s !== subscription);
    };
  }

  /**
   * Subscribe to all events (wildcard)
   */
  subscribeAll(handler: (event: AppEvent) => void): () => void {
    this.emitter.on('*', handler);
    return () => this.emitter.off('*', handler);
  }

  /**
   * Wait for a specific event
   */
  waitFor<T extends EventType>(
    eventType: T,
    timeoutMs: number = 30000
  ): Promise<AppEvent<EventPayloadMap[T]>> {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.emitter.off(eventType, handler);
        reject(new Error(`Timeout waiting for event: ${eventType}`));
      }, timeoutMs);

      const handler = (event: AppEvent) => {
        clearTimeout(timeout);
        resolve(event as AppEvent<EventPayloadMap[T]>);
      };

      this.emitter.once(eventType, handler);
    });
  }

  /**
   * Get event history
   */
  getHistory(filters?: { 
    eventType?: EventType; 
    groupId?: string;
    limit?: number;
  }): AppEvent[] {
    let history = [...this.eventHistory];

    if (filters) {
      if (filters.eventType) {
        history = history.filter(e => e.type === filters.eventType);
      }
      if (filters.groupId) {
        history = history.filter(e => e.metadata?.groupId === filters.groupId);
      }
      if (filters.limit) {
        history = history.slice(-filters.limit);
      }
    }

    return history;
  }

  /**
   * Get listener count for an event type
   */
  getListenerCount(eventType: EventType): number {
    return this.emitter.listenerCount(eventType);
  }

  /**
   * Get all active subscriptions
   */
  getSubscriptions(): Subscription[] {
    return [...this.subscriptions];
  }

  /**
   * Clear event history
   */
  clearHistory(): void {
    this.eventHistory = [];
  }

  /**
   * Remove all listeners (for cleanup)
   */
  destroy(): void {
    this.emitter.removeAllListeners();
    this.subscriptions = [];
    this.clearHistory();
  }
}

/**
 * Singleton EventBus instance
 */
let eventBusInstance: EventBus | null = null;

export function getEventBus(config?: EventBusConfig): EventBus {
  if (!eventBusInstance) {
    eventBusInstance = new EventBus(config);
  }
  return eventBusInstance;
}

export function resetEventBus(): void {
  if (eventBusInstance) {
    eventBusInstance.destroy();
    eventBusInstance = null;
  }
}
