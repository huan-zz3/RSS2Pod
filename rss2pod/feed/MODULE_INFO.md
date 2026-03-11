# Feed Module Structure

## Directory Layout

```
rss2pod/feed/
├── __init__.py           # Module exports
├── feed_generator.py     # Core RSS generation (PodcastFeedGenerator)
├── feed_manager.py       # Multi-group management (FeedManager)
├── test_feed.py          # Test suite
└── README.md             # Usage documentation
```

## Components

### 1. feed_generator.py

**Purpose:** Core RSS 2.0 feed generation with podcast extensions

**Key Classes:**
- `PodcastFeedGenerator` - Main feed generator class

**Key Methods:**
```python
# Create generator
fg = PodcastFeedGenerator(title, link, description, **kwargs)

# Add episode
fg.add_episode(
    episode_id='unique-id',
    title='Episode Title',
    link='https://example.com/episode',
    audio_url='https://example.com/audio.mp3',  # Supports HTTP Range
    audio_length=12345678,  # File size in bytes
    description='Plain text description',
    content_html='<p>Full HTML for AntennaPod</p>',  # HTML content
    duration='00:30:00',
    episode_number=1,
    season_number=1,
    explicit=False,
    image='https://example.com/episode-cover.jpg',
    keywords=['tag1', 'tag2']
)

# Generate RSS
rss_xml = fg.rss_str(pretty=True)
fg.rss_file('output.xml')
```

**Features:**
- ✅ RSS 2.0 compliant
- ✅ iTunes podcast tags (author, summary, duration, episode, season, explicit)
- ✅ Enclosure with proper MIME type and length
- ✅ HTML content in `<content:encoded>` tag
- ✅ Atom feed support

---

### 2. feed_manager.py

**Purpose:** Manage multiple independent feeds (one per Group)

**Key Classes:**
- `FeedManager` - Multi-group feed management
- `Episode` - Episode data structure
- `PodcastGroup` - Group configuration

**Key Methods:**
```python
# Initialize manager
manager = FeedManager(base_dir='./feeds')

# Create group
manager.create_group(
    group_id='unique-group-id',
    title='Group Title',
    link='https://example.com/group',
    description='Group description',
    author='Author Name',
    language='en',
    category='Category'
)

# Add episode
episode = Episode(
    id='ep001',
    title='Episode Title',
    link='https://example.com/episode',
    audio_url='https://example.com/audio.mp3',
    audio_length=12345678,
    description='Description',
    content_html='<p>HTML content</p>',
    duration='00:30:00',
    keywords=['tag1', 'tag2']
)
manager.add_episode('group-id', episode)

# Generate feed
rss_xml = manager.generate_feed('group-id')
feed_path = manager.get_feed_url('group-id')

# Get episodes
episodes = manager.get_episodes('group-id', limit=10)

# Remove episode
manager.remove_episode('group-id', 'ep001')
```

**Storage Structure:**
```
feeds/
├── groups/           # Group configurations (JSON)
│   └── {group_id}.json
├── episodes/         # Episode metadata (JSON)
│   └── {group_id}.json
└── rss/              # Generated RSS feeds (XML)
    └── {group_id}.xml
```

---

### 3. HTTP Range Request Support

Audio enclosures support HTTP Range requests for streaming:

```python
# Get Range headers
headers = manager.get_range_request_headers(
    audio_url='https://example.com/audio.mp3',
    start=0,
    end=1024000  # First 1MB
)
# headers = {'Range': 'bytes=0-1024000'}

# Use in HTTP client
# GET /audio.mp3
# Range: bytes=0-1024000
# 
# Response: 206 Partial Content
# Content-Range: bytes 0-1024000/12345678
```

**Benefits:**
- Progressive streaming
- Seek support in podcast clients
- Bandwidth efficiency
- Better user experience

---

### 4. HTML Content Embedding

Full HTML content is embedded for AntennaPod and advanced clients:

```python
fg.add_episode(
    # ... other parameters ...
    content_html='''
        <p>Episode summary with <strong>formatting</strong>.</p>
        <h3>Key Points</h3>
        <ul>
            <li>Point 1</li>
            <li>Point 2</li>
        </ul>
        <p>Links: <a href="https://example.com">Example</a></p>
        <blockquote>Important quote</blockquote>
    '''
)
```

**Generated XML:**
```xml
<content:encoded><![CDATA[
    <p>Episode summary with <strong>formatting</strong>.</p>
    <h3>Key Points</h3>
    ...
]]></content:encoded>
```

**Supported HTML Tags:**
- Basic: `p`, `br`, `hr`
- Formatting: `strong`, `em`, `b`, `i`, `u`
- Lists: `ul`, `ol`, `li`
- Headers: `h1`-`h6`
- Links: `a href`
- Quotes: `blockquote`, `q`
- Code: `code`, `pre`

---

## Integration Example

```python
from rss2pod.feed import FeedManager, Episode

# Initialize
manager = FeedManager(base_dir='/path/to/feeds')

# For each group in your system:
for group in groups:
    # Create group (if not exists)
    if not manager.get_group(group.id):
        manager.create_group(
            group_id=group.id,
            title=group.name,
            link=group.website,
            description=group.description
        )
    
    # For each episode in the group:
    for episode_data in group.episodes:
        episode = Episode(
            id=episode_data['id'],
            title=episode_data['title'],
            link=episode_data['url'],
            audio_url=episode_data['audio_url'],  # Must support Range
            audio_length=episode_data['size'],
            description=episode_data['summary'],
            content_html=episode_data['content_html'],  # Full HTML
            pub_date=episode_data['pub_date'],
            duration=episode_data['duration'],
            keywords=episode_data['tags']
        )
        manager.add_episode(group.id, episode)

# Generate all feeds
for group in manager.list_groups():
    rss = manager.generate_feed(group.id)
    print(f"Generated feed for {group.title}: {manager.get_feed_url(group.id)}")
```

---

## Testing

Run the test suite:

```bash
# Install dependency
pip install feedgen

# Run tests
cd rss2pod/feed
python3 test_feed.py
```

Expected output:
```
============================================================
RSS2Pod Feed Module Tests
============================================================
Testing imports...
✓ All imports successful

Testing feed generator...
  ✓ RSS root element
  ✓ Channel element
  ✓ Feed title
  ✓ iTunes author
  ✓ Enclosure element
  ✓ HTML content tag
  ✓ HTML content preserved

  Generated RSS (XXXX bytes):
  ...

Testing feed manager...
  ✓ Created group: Test Group Podcast
  ✓ Added episode: First Test Episode
  ✓ Retrieved 1 episode(s)
  ✓ Generated valid RSS feed (XXXX bytes)
  ✓ Feed saved to: /tmp/.../rss/test-group.xml
  ✓ Range request headers correct

============================================================
Test Summary
============================================================
  ✓ PASS: Feed Generator
  ✓ PASS: Feed Manager

Total: 2/2 tests passed

🎉 All tests passed!
```

---

## Dependencies

- Python 3.7+
- feedgen >= 0.9.0

Install:
```bash
pip install -r ../requirements.txt
```

---

## Next Steps

After creating this module:

1. Install feedgen: `pip install feedgen`
2. Run tests: `python3 test_feed.py`
3. Integrate with main RSS2Pod system
4. Configure feed output directory
5. Set up automatic feed regeneration on episode updates
