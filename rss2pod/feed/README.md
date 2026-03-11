# RSS2Pod Feed Module

Podcast RSS feed generation and management module using `python-feedgen`.

## Features

- ✅ RSS 2.0 compliant feeds with podcast extensions
- ✅ iTunes/Apple Podcasts tags support
- ✅ Enclosure support with HTTP Range requests
- ✅ HTML content embedding (AntennaPod compatible)
- ✅ Per-group feed management
- ✅ Feed persistence and automatic regeneration

## Installation

Requires `python-feedgen`:

```bash
pip install feedgen
```

## Quick Start

### Basic Feed Generation

```python
from rss2pod.feed import create_podcast_feed

# Create feed generator
fg = create_podcast_feed(
    title='My Podcast',
    link='https://example.com/podcast',
    description='An amazing podcast',
    author='Podcast Host',
    image='https://example.com/cover.jpg'
)

# Add episode
fg.add_episode(
    episode_id='ep001',
    title='First Episode',
    link='https://example.com/ep001',
    audio_url='https://example.com/audio/ep001.mp3',
    audio_length=12345678,
    description='Episode description',
    content_html='<p>Full <strong>HTML</strong> content</p>',
    duration='00:45:30'
)

# Generate RSS
rss_xml = fg.rss_str()
print(rss_xml)
```

### Feed Manager (Per-Group Feeds)

```python
from rss2pod.feed import FeedManager, Episode

# Initialize manager
manager = FeedManager(base_dir='./feeds')

# Create a group
manager.create_group(
    group_id='tech-podcast',
    title='Tech Podcast',
    link='https://example.com/tech',
    description='Technology discussions',
    author='Tech Team'
)

# Add episode
episode = Episode(
    id='ep001',
    title='AI Revolution',
    link='https://example.com/tech/ep001',
    audio_url='https://example.com/audio/ep001.mp3',
    audio_length=12345678,
    description='About AI',
    content_html='<p>Full HTML content for AntennaPod</p>',
    duration='00:30:00',
    keywords=['AI', 'tech']
)

manager.add_episode('tech-podcast', episode)

# Generate feed
rss_xml = manager.generate_feed('tech-podcast')

# Get feed file path
feed_path = manager.get_feed_url('tech-podcast')
print(f"Feed saved to: {feed_path}")
```

## HTTP Range Request Support

The module supports HTTP Range requests for audio enclosures. This allows podcast clients to:

- Stream audio progressively
- Seek within episodes
- Download partial content

Example of manual Range request:

```python
from rss2pod.feed import FeedManager

manager = FeedManager()

# Get headers for Range request
headers = manager.get_range_request_headers(
    audio_url='https://example.com/audio.mp3',
    start=0,
    end=1024000  # First 1MB
)

# Use headers in your HTTP client
# Range: bytes=0-1024000
```

## HTML Content for AntennaPod

AntennaPod and other advanced podcast clients can render HTML content in episode descriptions. Use the `content_html` parameter:

```python
fg.add_episode(
    # ... other parameters ...
    content_html='''
        <p>Episode summary with <strong>formatting</strong>.</p>
        <ul>
            <li>Point 1</li>
            <li>Point 2</li>
        </ul>
        <p>Links: <a href="https://example.com">Example</a></p>
    '''
)
```

The HTML is embedded in the `<content:encoded>` tag for maximum compatibility.

## Feed Structure

Each group gets its own independent RSS feed:

```
feeds/
├── groups/           # Group configurations
│   ├── tech-podcast.json
│   └── news-podcast.json
├── episodes/         # Episode metadata
│   ├── tech-podcast.json
│   └── news-podcast.json
└── rss/              # Generated RSS feeds
    ├── tech-podcast.xml
    └── news-podcast.xml
```

## API Reference

### PodcastFeedGenerator

Core feed generation class.

**Methods:**
- `add_episode(**kwargs)` - Add episode to feed
- `rss_str(pretty=True)` - Generate RSS string
- `rss_file(filepath)` - Write RSS to file
- `atom_str()` - Generate Atom feed
- `get_entries()` - Get all episodes

### FeedManager

Multi-group feed management.

**Methods:**
- `create_group(group_id, title, link, description, **kwargs)` - Create group
- `get_group(group_id)` - Get group info
- `list_groups()` - List all groups
- `delete_group(group_id)` - Delete group
- `add_episode(group_id, episode)` - Add episode
- `get_episodes(group_id, limit)` - Get episodes
- `remove_episode(group_id, episode_id)` - Remove episode
- `generate_feed(group_id)` - Generate RSS
- `get_feed_url(group_id)` - Get feed file path

### Episode

Episode data structure.

**Fields:**
- `id` - Unique identifier
- `title` - Episode title
- `link` - Episode page URL
- `audio_url` - Direct audio URL (supports Range)
- `audio_length` - File size in bytes
- `audio_type` - MIME type (default: audio/mpeg)
- `description` - Plain text description
- `content_html` - Full HTML content
- `pub_date` - Publication date (ISO format)
- `duration` - Duration (HH:MM:SS)
- `episode_number` - Episode number
- `season_number` - Season number
- `explicit` - Explicit content flag
- `image` - Episode image URL
- `keywords` - List of tags

## Best Practices

1. **Audio URLs**: Use direct, permanent URLs that support HTTP Range requests
2. **Episode IDs**: Use stable, unique identifiers (avoid changing them)
3. **Content HTML**: Keep HTML simple and semantic for best compatibility
4. **Feed Updates**: Regenerate feeds after each episode addition
5. **File Sizes**: Always provide accurate `audio_length` for proper client behavior

## Compatibility

- ✅ Apple Podcasts
- ✅ Google Podcasts
- ✅ Spotify
- ✅ AntennaPod (Android)
- ✅ Overcast
- ✅ Pocket Casts
- ✅ Any RSS 2.0 podcast client

## License

Part of RSS2Pod project.
