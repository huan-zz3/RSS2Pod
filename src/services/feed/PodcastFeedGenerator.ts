// Podcast feed generator using the 'podcast' npm library
// Generates iTunes-compliant RSS feeds and saves to data/media/feeds/{groupId}.xml

import * as path from 'path';
import * as fs from 'fs';

// Import the podcast library (v2.x)
// eslint-disable-next-line @typescript-eslint/no-var-requires
const PodcastLib = require('podcast');

import { FeedItem, FeedConfig } from '../../shared/types/feed.js';

export class PodcastFeedGenerator {
  generateFeed(items: FeedItem[], config: FeedConfig): string {
    // Build feed options, including iTunes metadata when provided
    const feedOptions: any = {
      title: config.title,
      description: config.description,
      imageUrl: config.imageUrl,
      // The feedUrl should reflect the expected API route for the group
      feedUrl: `http://localhost:3000/api/feeds/${config.groupId}`,
      siteUrl: config.siteUrl,
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
      (podcast as any).item({
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

export { FeedItem, FeedConfig } from '../../shared/types/feed.js';
