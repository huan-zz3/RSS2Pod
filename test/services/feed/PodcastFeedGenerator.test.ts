import { PodcastFeedGenerator } from '../../../src/services/feed/PodcastFeedGenerator';
import { FeedItem, FeedConfig } from '../../../src/shared/types/feed';
import * as fs from 'fs';
import * as path from 'path';

describe('PodcastFeedGenerator', () => {
  const items: FeedItem[] = [
    {
      title: 'Episode 1',
      description: '<p>Intro</p>',
      enclosure: {
        url: 'http://example.com/ep1.mp3',
        length: 12345,
        type: 'audio/mpeg',
      },
      pubDate: new Date('2026-03-01T00:00:00Z').toUTCString(),
      guid: 'ep1',
    },
    {
      title: 'Episode 2',
      description: 'Second episode',
      enclosure: {
        url: 'http://example.com/ep2.mp3',
        length: 23456,
        type: 'audio/mpeg',
      },
      pubDate: new Date('2026-03-02T00:00:00Z').toUTCString(),
      guid: 'ep2',
    },
  ];

  const config: FeedConfig = {
    groupId: 'grp1',
    title: 'Test Podcast',
    description: 'A test podcast feed',
    imageUrl: 'http://example.com/image.png',
    siteUrl: 'http://example.com',
    itunesAuthor: 'Test Author',
    itunesExplicit: 'no',
    itunesOwnerName: 'Owner',
    itunesOwnerEmail: 'owner@example.com',
  };

  afterAll(() => {
    const feedPath = path.resolve(process.cwd(), 'data', 'media', 'feeds', 'grp1.xml');
    if (fs.existsSync(feedPath)) {
      fs.unlinkSync(feedPath);
    }
  });

  test('generates XML with iTunes tags and enclosure', () => {
    const generator = new PodcastFeedGenerator();
    const xml = generator.generateFeed(items, config);
    expect(xml).toContain('<rss');
    expect(xml).toContain('itunes:author');
    expect(xml).toContain('<title>Episode 1</title>');
    expect(xml).toContain('<enclosure');
    // Ensure enclosure url is present
    expect(xml).toContain('http://example.com/ep1.mp3');
  });

  test('saves feed to file', () => {
    const generator = new PodcastFeedGenerator();
    generator.generateFeed(items, config);
    const feedPath = path.resolve(process.cwd(), 'data', 'media', 'feeds', 'grp1.xml');
    expect(fs.existsSync(feedPath)).toBe(true);
    const content = fs.readFileSync(feedPath, 'utf8');
    expect(content.length).toBeGreaterThan(0);
  });
});
