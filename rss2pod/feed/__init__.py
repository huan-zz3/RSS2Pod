"""
RSS2Pod Feed Module

Podcast RSS feed generation and management.
"""

from .feed_generator import (
    PodcastFeedGenerator,
    create_podcast_feed
)

from .feed_manager import (
    FeedManager,
    Episode,
    PodcastGroup,
    create_group,
    add_episode_to_group,
    generate_group_feed
)

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
