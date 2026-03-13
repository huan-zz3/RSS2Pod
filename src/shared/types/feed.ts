// Shared feed types for RSS2Pod podcast feeds

export interface Enclosure {
  url: string;
  length: number; // in bytes
  type?: string; // mime type, defaults to application/octet-stream or audio/mpeg
}

export interface FeedItem {
  title: string;
  description: string; // can contain HTML
  enclosure: Enclosure;
  pubDate: string; // RFC 2822 date string
  guid: string;
}

export interface FeedConfig {
  groupId: string; // unique group/feed identifier
  title: string;
  description: string;
  imageUrl?: string;
  siteUrl?: string;
  author?: string;
  // iTunes specific metadata
  itunesAuthor?: string;
  itunesExplicit?: 'yes' | 'no' | 'clean' | 'explicit';
  itunesOwnerName?: string;
  itunesOwnerEmail?: string;
  itunesCategory?: string;
  language?: string;
  categories?: string[];
}

export interface PodcastFeed {
  generateFeed(items: FeedItem[], config: FeedConfig): string;
}
