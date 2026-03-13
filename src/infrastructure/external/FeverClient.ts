import axios, { AxiosInstance } from 'axios';
import { createHash } from 'crypto';
import { z } from 'zod';
import pino from 'pino';

const logger = pino({ name: 'fever-client' });

/**
 * Fever API response schemas
 */
const FeverAuthSchema = z.object({
  auth: z.number(),
  api_version: z.number(),
});

const FeedSchema = z.object({
  id: z.number(),
  title: z.string(),
  url: z.string(),
  site_url: z.string(),
  is_spark: z.number(),
});

const GroupSchema = z.object({
  id: z.number(),
  title: z.string(),
});

const ItemSchema = z.object({
  id: z.number(),
  title: z.string(),
  html: z.string(),
  url: z.string(),
  feed_id: z.number(),
  is_read: z.number(),
  is_saved: z.number(),
  created_on: z.number(),
});

const FeverFeedsResponse = FeverAuthSchema.extend({
  feeds: z.array(FeedSchema),
  feeds_groups: z.array(z.object({
    group_id: z.number(),
    feed_ids: z.string(),
  })),
});

const FeverGroupsResponse = FeverAuthSchema.extend({
  groups: z.array(GroupSchema),
  feeds_groups: z.array(z.object({
    group_id: z.number(),
    feed_ids: z.string(),
  })),
});

const FeverItemsResponse = FeverAuthSchema.extend({
  items: z.array(ItemSchema),
  total_items: z.number(),
});

const FeverUnreadResponse = FeverAuthSchema.extend({
  unread_item_ids: z.string(),
});

const FeverSavedResponse = FeverAuthSchema.extend({
  saved_item_ids: z.string(),
});

/**
 * Fever API configuration
 */
export interface FeverConfig {
  baseUrl: string;
  email: string;
  password: string;
}

/**
 * Feed data structure
 */
export interface Feed {
  id: number;
  title: string;
  url: string;
  siteUrl: string;
  isSpark: boolean;
}

/**
 * Group data structure
 */
export interface Group {
  id: number;
  title: string;
}

/**
 * Article item from Fever API
 */
export interface FeverItem {
  id: number;
  title: string;
  html: string;
  url: string;
  feedId: number;
  isRead: boolean;
  isSaved: boolean;
  createdOn: Date;
}

/**
 * Fever API Client
 * 
 * Implements the Fever API specification for TT-RSS integration
 * Reference: http://www.feedafever.com/api
 */
export class FeverClient {
  private client: AxiosInstance;
  private apiKey: string;

  constructor(config: FeverConfig) {
    this.apiKey = this.generateApiKey(config.email, config.password);
    
    this.client = axios.create({
      baseURL: config.baseUrl.replace(/\/$/, ''),
      timeout: 30000,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  }

  private generateApiKey(email: string, password: string): string {
    return createHash('md5').update(`${email}:${password}`).digest('hex');
  }

  private async get<T>(params: Record<string, string | number>): Promise<T> {
    try {
      const response = await this.client.get('/', {
        params: { ...params, api_key: this.apiKey },
      });
      return response.data as T;
    } catch (error) {
      logger.error({ error }, 'Fever API GET request failed');
      throw error;
    }
  }

  private async post<T>(params: Record<string, string | number>): Promise<T> {
    try {
      const response = await this.client.post('/', params, {
        params: { api: true },
      });
      return response.data as T;
    } catch (error) {
      logger.error({ error }, 'Fever API POST request failed');
      throw error;
    }
  }

  /**
   * Test API authentication
   */
  async testAuth(): Promise<boolean> {
    try {
      const response = await this.get<{ auth: number }>({ api: 1 });
      return response.auth === 1;
    } catch {
      return false;
    }
  }

  /**
   * Get all feeds
   */
  async getFeeds(): Promise<Feed[]> {
    const response = await this.get<z.infer<typeof FeverFeedsResponse>>({ feeds: 1 });
    const validated = FeverFeedsResponse.parse(response);
    
    return validated.feeds.map(feed => ({
      id: feed.id,
      title: feed.title,
      url: feed.url,
      siteUrl: feed.site_url,
      isSpark: feed.is_spark === 1,
    }));
  }

  /**
   * Get all groups
   */
  async getGroups(): Promise<Group[]> {
    const response = await this.get<z.infer<typeof FeverGroupsResponse>>({ groups: 1 });
    const validated = FeverGroupsResponse.parse(response);
    
    return validated.groups.map(group => ({
      id: group.id,
      title: group.title,
    }));
  }

  /**
   * Get items (articles)
   */
  async getItems(options?: {
    sinceId?: number;
    maxId?: number;
    withIds?: number[];
  }): Promise<FeverItem[]> {
    const params: Record<string, string | number> = { items: 1 };
    
    if (options?.sinceId) params.since_id = options.sinceId;
    if (options?.maxId) params.max_id = options.maxId;
    if (options?.withIds?.length) {
      params.with_ids = options.withIds.slice(0, 50).join(',');
    }

    const response = await this.get<z.infer<typeof FeverItemsResponse>>(params);
    const validated = FeverItemsResponse.parse(response);
    
    return validated.items.map(item => ({
      id: item.id,
      title: item.title,
      html: item.html,
      url: item.url,
      feedId: item.feed_id,
      isRead: item.is_read === 1,
      isSaved: item.is_saved === 1,
      createdOn: new Date(item.created_on * 1000),
    }));
  }

  /**
   * Get unread item IDs
   */
  async getUnreadItemIds(): Promise<number[]> {
    const response = await this.get<z.infer<typeof FeverUnreadResponse>>({ unread_item_ids: 1 });
    const validated = FeverUnreadResponse.parse(response);
    
    return validated.unread_item_ids
      .split(',')
      .filter(Boolean)
      .map(id => parseInt(id, 10));
  }

  /**
   * Get saved item IDs
   */
  async getSavedItemIds(): Promise<number[]> {
    const response = await this.get<z.infer<typeof FeverSavedResponse>>({ saved_item_ids: 1 });
    const validated = FeverSavedResponse.parse(response);
    
    return validated.saved_item_ids
      .split(',')
      .filter(Boolean)
      .map(id => parseInt(id, 10));
  }

  /**
   * Mark item as read
   */
  async markAsRead(itemId: number): Promise<void> {
    await this.post({ mark: 'item', as: 'read', id: itemId.toString() });
  }

  /**
   * Mark item as saved (starred)
   */
  async markAsSaved(itemId: number): Promise<void> {
    await this.post({ mark: 'item', as: 'saved', id: itemId.toString() });
  }

  /**
   * Mark item as unsaved
   */
  async markAsUnsaved(itemId: number): Promise<void> {
    await this.post({ mark: 'item', as: 'unsaved', id: itemId.toString() });
  }

  /**
   * Mark feed as read (before timestamp)
   */
  async markFeedAsRead(feedId: number, beforeTimestamp: number): Promise<void> {
    await this.post({ 
      mark: 'feed', 
      as: 'read', 
      id: feedId.toString(),
      before: beforeTimestamp.toString(),
    });
  }

  /**
   * Mark group as read (before timestamp)
   */
  async markGroupAsRead(groupId: number, beforeTimestamp: number): Promise<void> {
    await this.post({ 
      mark: 'group', 
      as: 'read', 
      id: groupId.toString(),
      before: beforeTimestamp.toString(),
    });
  }

  /**
   * Unread recently read items
   */
  async unreadRecentlyRead(): Promise<void> {
    await this.post({ unread_recently_read: '1' });
  }
}
