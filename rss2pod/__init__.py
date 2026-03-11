"""
RSS2Pod - Podcast RSS Feed Generator

Generate and manage podcast RSS feeds with full enclosure support
and HTML content embedding for AntennaPod compatibility.
"""

from .feed import (
    PodcastFeedGenerator,
    create_podcast_feed,
    FeedManager,
    Episode,
    PodcastGroup,
    create_group,
    add_episode_to_group,
    generate_group_feed
)

__version__ = '1.0.0'
__author__ = 'RSS2Pod Team'

__all__ = [
    'PodcastFeedGenerator',
    'create_podcast_feed',
    'FeedManager',
    'Episode',
    'PodcastGroup',
    'create_group',
    'add_episode_to_group',
    'generate_group_feed'
]
