// Podcast feed generator using the 'podcast' npm library
// Generates iTunes-compliant RSS feeds and saves to data/media/feeds/{groupId}.xml

import * as path from 'path';
import * as fs from 'fs';
import { createRequire } from 'module';
import { getConfig } from '../../shared/config/index.js';

const require = createRequire(import.meta.url);
// eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
const PodcastModule: any = require('podcast');
// eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
const PodcastLib: any = PodcastModule.Podcast;

import type { FeedItem, FeedConfig } from '../../shared/types/feed.js';

export class PodcastFeedGenerator {
  generateFeed(items: FeedItem[], config: FeedConfig): string {
    const appConfig = getConfig();
    const baseUrl = appConfig.api.baseUrl;
    
    // Build feed options, including iTunes metadata when provided
    const feedOptions: any = {
      title: config.title,
      description: config.description,
      imageUrl: config.imageUrl,
      // The feedUrl should reflect the expected API route for the group
      feedUrl: `${baseUrl}/api/feeds/${config.groupId}`,
      siteUrl: config.siteUrl ?? baseUrl,
      author: config.author,
      // iTunes specific metadata
      itunesAuthor: config.itunesAuthor ?? undefined,
      itunesExplicit: config.itunesExplicit ?? 'no',
      itunesOwner: config.itunesOwnerName
        ? {
            name: config.itunesOwnerName,
            email: config.itunesOwnerEmail ?? '',
          }
        : undefined,
      itunesCategory: config.itunesCategory,
      language: config.language,
    };

    const podcast: any = new PodcastLib(feedOptions);

    // Attach items
    items.forEach((it) => {
      (podcast as any).addItem({
        title: it.title,
        description: it.description,
        // Enclosure for the audio file
        enclosure: {
          url: it.enclosure.url,
          length: String(it.enclosure.length),
          type: it.enclosure.type ?? 'audio/mpeg',
        },
        date: it.pubDate,
        guid: it.guid,
      } as any);
    });

    const xml: string = podcast.buildXml(true);

    // Persist feed file
    const feedDir = path.resolve(process.cwd(), 'data', 'media', 'feeds');
    fs.mkdirSync(feedDir, { recursive: true });
    const feedPath = path.join(feedDir, `${config.groupId}.xml`);
    fs.writeFileSync(feedPath, xml, { encoding: 'utf8' });

    return xml;
  }
}

export default PodcastFeedGenerator;
export type { FeedItem, FeedConfig } from '../../shared/types/feed.js';
