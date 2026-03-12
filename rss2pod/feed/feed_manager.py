#!/usr/bin/env python3
"""
Podcast Feed Manager

Manages multiple podcast feeds, one per Group.
Handles feed persistence, updates, and HTTP Range request support.

Features:
- Per-group feed management
- Feed persistence and caching
- Enclosure URL management with HTTP Range support
- HTML content embedding for AntennaPod compatibility
- Automatic feed updates
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import hashlib

from .feed_generator import PodcastFeedGenerator, create_podcast_feed


@dataclass
class Episode:
    """Episode data structure."""
    id: str
    title: str
    link: str
    audio_url: str
    audio_length: int
    audio_type: str = 'audio/mpeg'
    description: str = ''
    content_html: str = ''
    pub_date: str = ''  # ISO format
    duration: str = ''
    episode_number: int = None
    season_number: int = None
    explicit: bool = False
    image: str = ''
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if not self.pub_date:
            self.pub_date = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Episode':
        """Create Episode from dictionary."""
        return cls(**data)


@dataclass
class PodcastGroup:
    """Podcast group configuration."""
    id: str
    title: str
    link: str
    description: str
    language: str = 'en'
    author: str = ''
    image: str = ''
    category: str = ''
    created_at: str = ''
    updated_at: str = ''
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
    
    @property
    def name(self) -> str:
        """兼容别名：返回 title，与 database.models.Group 保持一致"""
        return self.title
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PodcastGroup':
        """Create PodcastGroup from dictionary."""
        return cls(**data)


class FeedManager:
    """
    Manage multiple podcast feeds, one per Group.
    
    Each group has its own independent RSS feed.
    Feeds are persisted to disk and can be regenerated on demand.
    """
    
    def __init__(self, base_dir: str = None):
        """
        Initialize the feed manager.
        
        Args:
            base_dir: Base directory for feed storage (default: ./feeds)
        """
        if base_dir is None:
            base_dir = Path(__file__).parent.parent / 'feeds'
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Groups directory
        self.groups_dir = self.base_dir / 'groups'
        self.groups_dir.mkdir(parents=True, exist_ok=True)
        
        # Feeds directory (generated RSS files)
        self.feeds_dir = self.base_dir / 'rss'
        self.feeds_dir.mkdir(parents=True, exist_ok=True)
        
        # Episodes directory (episode metadata)
        self.episodes_dir = self.base_dir / 'episodes'
        self.episodes_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache
        self._groups: Dict[str, PodcastGroup] = {}
        self._episodes: Dict[str, List[Episode]] = {}  # group_id -> episodes
        self._feeds: Dict[str, PodcastFeedGenerator] = {}  # group_id -> feed generator
        
        # Load existing data
        self._load_all_groups()
    
    def create_group(self, group_id: str, title: str, link: str, 
                    description: str, **kwargs) -> PodcastGroup:
        """
        Create a new podcast group (idempotent).
        
        Args:
            group_id: Unique group identifier
            title: Group/podcast title
            link: Group website link
            description: Group description
            **kwargs: Additional group parameters
        
        Returns:
            Created or updated PodcastGroup
        """
        # 幂等性：如果 group 已存在，更新而不是报错
        if group_id in self._groups:
            existing = self._groups[group_id]
            existing.title = title
            existing.link = link
            existing.description = description
            # 更新其他可选参数
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc).isoformat()
            self._save_group(existing)
            return existing
        
        group = PodcastGroup(
            id=group_id,
            title=title,
            link=link,
            description=description,
            **kwargs
        )
        
        # Save group
        self._save_group(group)
        self._groups[group_id] = group
        
        # Initialize episodes list
        if group_id not in self._episodes:
            self._episodes[group_id] = []
            self._save_episodes(group_id, [])
        
        # Initialize feed
        self._create_feed_generator(group_id)
        
        return group
    
    def sync_group(self, group_id: str, group_data: Dict[str, Any]) -> PodcastGroup:
        """
        Sync a group from external data source (e.g., database) to FeedManager.
        
        This method ensures that the group exists in FeedManager's memory cache.
        If the group already exists, it updates the metadata.
        
        Args:
            group_id: Group identifier
            group_data: Group data dictionary with keys:
                       - title: Group title
                       - link: Group link
                       - description: Group description
                       - language: (optional) Language code
                       - author: (optional) Author name
                       - image: (optional) Image URL
                       - category: (optional) Category
        
        Returns:
            Synced PodcastGroup
        """
        title = group_data.get('title', group_id)
        link = group_data.get('link', '')
        description = group_data.get('description', '')
        language = group_data.get('language', 'zh-cn')
        author = group_data.get('author', 'RSS2Pod')
        image = group_data.get('image', '')
        category = group_data.get('category', '')
        
        # Use create_group which is idempotent
        return self.create_group(
            group_id=group_id,
            title=title,
            link=link,
            description=description,
            language=language,
            author=author,
            image=image,
            category=category
        )
    
    def get_group(self, group_id: str) -> Optional[PodcastGroup]:
        """Get a group by ID."""
        return self._groups.get(group_id)
    
    def list_groups(self) -> List[PodcastGroup]:
        """List all groups."""
        return list(self._groups.values())
    
    def delete_group(self, group_id: str) -> bool:
        """
        Delete a group and all its data.
        
        Args:
            group_id: Group to delete
        
        Returns:
            True if deleted, False if not found
        """
        if group_id not in self._groups:
            return False
        
        # Remove from memory
        del self._groups[group_id]
        self._episodes.pop(group_id, None)
        self._feeds.pop(group_id, None)
        
        # Remove files
        group_file = self.groups_dir / f'{group_id}.json'
        episodes_file = self.episodes_dir / f'{group_id}.json'
        feed_file = self.feeds_dir / f'{group_id}.xml'
        
        for f in [group_file, episodes_file, feed_file]:
            if f.exists():
                f.unlink()
        
        return True
    
    def add_episode(self, group_id: str, episode: Episode) -> Episode:
        """
        Add an episode to a group.
        
        Args:
            group_id: Target group
            episode: Episode to add
        
        Returns:
            Added episode
        """
        if group_id not in self._groups:
            raise ValueError(f"Group {group_id} not found")
        
        if group_id not in self._episodes:
            self._episodes[group_id] = []
        
        # Add to episodes list
        self._episodes[group_id].append(episode)
        
        # Save episodes
        self._save_episodes(group_id, self._episodes[group_id])
        
        # Regenerate feed
        self._regenerate_feed(group_id)
        
        return episode
    
    def get_episodes(self, group_id: str, limit: int = None) -> List[Episode]:
        """
        Get episodes for a group.
        
        Args:
            group_id: Group ID
            limit: Maximum number of episodes (default: all)
        
        Returns:
            List of episodes (newest first)
        """
        episodes = self._episodes.get(group_id, [])
        # Sort by publication date (newest first)
        episodes = sorted(episodes, 
                         key=lambda e: e.pub_date, 
                         reverse=True)
        if limit:
            episodes = episodes[:limit]
        return episodes
    
    def remove_episode(self, group_id: str, episode_id: str) -> bool:
        """
        Remove an episode from a group.
        
        Args:
            group_id: Group ID
            episode_id: Episode ID to remove
        
        Returns:
            True if removed, False if not found
        """
        if group_id not in self._episodes:
            return False
        
        episodes = self._episodes[group_id]
        original_count = len(episodes)
        self._episodes[group_id] = [e for e in episodes if e.id != episode_id]
        
        if len(self._episodes[group_id]) < original_count:
            self._save_episodes(group_id, self._episodes[group_id])
            self._regenerate_feed(group_id)
            return True
        
        return False
    
    def generate_feed(self, group_id: str) -> str:
        """
        Generate RSS feed for a group.
        
        Args:
            group_id: Group ID
        
        Returns:
            RSS feed as XML string
        """
        if group_id not in self._groups:
            raise ValueError(f"Group {group_id} not found")
        
        # Create or get feed generator
        fg = self._create_feed_generator(group_id)
        
        # Add all episodes
        episodes = self.get_episodes(group_id)
        for ep in episodes:
            self._add_episode_to_feed(fg, ep)
        
        # Generate RSS
        rss = fg.rss_str(pretty=True)
        
        # Save to file (rss_str returns bytes)
        feed_file = self.feeds_dir / f'{group_id}.xml'
        with open(feed_file, 'wb') as f:
            f.write(rss)
        
        return rss
    
    def get_feed_url(self, group_id: str) -> str:
        """
        Get the URL for a group's feed.
        
        Args:
            group_id: Group ID
        
        Returns:
            Feed file path (can be converted to URL)
        """
        feed_file = self.feeds_dir / f'{group_id}.xml'
        return str(feed_file.absolute())
    
    def _create_feed_generator(self, group_id: str) -> PodcastFeedGenerator:
        """Create a feed generator for a group."""
        group = self._groups[group_id]
        
        fg = create_podcast_feed(
            title=group.title,
            link=group.link,
            description=group.description,
            language=group.language,
            author=group.author or group.title,
            image=group.image,
            category=group.category
        )
        
        self._feeds[group_id] = fg
        return fg
    
    def _add_episode_to_feed(self, fg: PodcastFeedGenerator, 
                            episode: Episode) -> None:
        """Add an episode to a feed generator."""
        from datetime import datetime, timezone
        
        # Parse publication date
        try:
            pub_date = datetime.fromisoformat(episode.pub_date.replace('Z', '+00:00'))
            # 如果解析后的 datetime 没有时区信息，添加 UTC 时区
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
        except:
            pub_date = datetime.now(timezone.utc)
        
        fg.add_episode(
            episode_id=episode.id,
            title=episode.title,
            link=episode.link,
            audio_url=episode.audio_url,
            audio_length=episode.audio_length,
            audio_type=episode.audio_type,
            description=episode.description,
            content_html=episode.content_html,
            pub_date=pub_date,
            duration=episode.duration,
            episode_number=episode.episode_number,
            season_number=episode.season_number,
            explicit=episode.explicit,
            image=episode.image,
            keywords=episode.keywords
        )
    
    def _regenerate_feed(self, group_id: str) -> None:
        """Regenerate feed for a group."""
        if group_id in self._feeds:
            del self._feeds[group_id]
        self.generate_feed(group_id)
        
        # Update group timestamp
        if group_id in self._groups:
            self._groups[group_id].updated_at = datetime.now(timezone.utc).isoformat()
            self._save_group(self._groups[group_id])
    
    def _save_group(self, group: PodcastGroup) -> None:
        """Save group to disk."""
        group_file = self.groups_dir / f'{group.id}.json'
        with open(group_file, 'w', encoding='utf-8') as f:
            json.dump(group.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _save_episodes(self, group_id: str, episodes: List[Episode]) -> None:
        """Save episodes to disk."""
        episodes_file = self.episodes_dir / f'{group_id}.json'
        data = [ep.to_dict() for ep in episodes]
        with open(episodes_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _load_all_groups(self) -> None:
        """Load all groups from disk."""
        if not self.groups_dir.exists():
            return
        
        for group_file in self.groups_dir.glob('*.json'):
            try:
                with open(group_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    group = PodcastGroup.from_dict(data)
                    self._groups[group.id] = group
                
                # Load episodes for this group
                episodes_file = self.episodes_dir / f'{group.id}.json'
                if episodes_file.exists():
                    with open(episodes_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        episodes = [Episode.from_dict(ep) for ep in data]
                        self._episodes[group.id] = episodes
                else:
                    self._episodes[group.id] = []
                
                # Create feed generator
                self._create_feed_generator(group.id)
                
            except Exception as e:
                print(f"Error loading group {group_file}: {e}")
    
    def get_range_request_headers(self, audio_url: str, 
                                  start: int = 0, 
                                  end: int = None) -> Dict[str, str]:
        """
        Get headers for HTTP Range request.
        
        Args:
            audio_url: Audio file URL
            start: Start byte
            end: End byte (None for to-end)
        
        Returns:
            Headers dictionary for Range request
        """
        headers = {}
        if end is not None:
            headers['Range'] = f'bytes={start}-{end}'
        else:
            headers['Range'] = f'bytes={start}-'
        return headers
    
    def validate_enclosure_url(self, audio_url: str) -> bool:
        """
        Validate that an enclosure URL supports HTTP Range requests.
        
        Args:
            audio_url: URL to validate
        
        Returns:
            True if Range requests are supported
        """
        import urllib.request
        
        try:
            req = urllib.request.Request(audio_url, method='HEAD')
            req.add_header('Range', 'bytes=0-0')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                # Check for 206 Partial Content or 200 OK
                return response.status in [200, 206]
        except Exception:
            return False


# Convenience functions
def create_group(group_id: str, title: str, link: str, 
                description: str, base_dir: str = None, **kwargs) -> PodcastGroup:
    """Create a new podcast group."""
    manager = FeedManager(base_dir)
    return manager.create_group(group_id, title, link, description, **kwargs)


def add_episode_to_group(group_id: str, episode_data: Dict, 
                        base_dir: str = None) -> Episode:
    """Add an episode to a group."""
    manager = FeedManager(base_dir)
    episode = Episode.from_dict(episode_data)
    return manager.add_episode(group_id, episode)


def generate_group_feed(group_id: str, base_dir: str = None) -> str:
    """Generate RSS feed for a group."""
    manager = FeedManager(base_dir)
    return manager.generate_feed(group_id)


if __name__ == '__main__':
    # Example usage
    manager = FeedManager()
    
    # Create a group
    group = manager.create_group(
        group_id='tech-talks',
        title='Tech Talks',
        link='https://example.com/tech-talks',
        description='Weekly discussions about technology',
        author='Tech Team',
        language='en',
        category='Technology'
    )
    
    # Add an episode
    episode = Episode(
        id='ep001',
        title='Introduction to AI',
        link='https://example.com/tech-talks/ep001',
        audio_url='https://example.com/audio/ep001.mp3',
        audio_length=12345678,
        description='An introduction to artificial intelligence',
        content_html='<p>Full <strong>HTML content</strong> here.</p>',
        duration='00:30:00',
        episode_number=1,
        keywords=['AI', 'technology', 'intro']
    )
    
    manager.add_episode('tech-talks', episode)
    
    # Generate feed
    rss = manager.generate_feed('tech-talks')
    print(f"Feed URL: {manager.get_feed_url('tech-talks')}")
    print(rss[:500])
