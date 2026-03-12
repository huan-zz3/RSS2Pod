#!/usr/bin/env python3
"""
Podcast RSS Feed Generator

Generates RSS 2.0 feeds with podcast extensions (iTunes/Apple Podcasts)
using python-feedgen library.

Features:
- RSS 2.0 compliant feeds
- iTunes podcast tags support
- Enclosure support with HTTP Range requests
- HTML content embedding (AntennaPod compatible)
"""

from feedgen.feed import FeedGenerator
from feedgen.entry import FeedEntry
from datetime import datetime, timezone
import html
from typing import List


class PodcastFeedGenerator:
    """Generate podcast RSS feeds with full enclosure and HTML support."""
    
    def __init__(self, title: str, link: str, description: str, 
                 language: str = 'en', author: str = None,
                 image: str = None, category: str = None):
        """
        Initialize the podcast feed generator.
        
        Args:
            title: Podcast title
            link: Podcast website/main link
            description: Podcast description
            language: Language code (default: 'en')
            author: Author name
            image: Podcast cover image URL
            category: Podcast category
        """
        self.fg = FeedGenerator()
        
        # Load iTunes podcast extension FIRST
        self.fg.load_extension('podcast')
        
        self.fg.title(title)
        self.fg.link(href=link, rel='alternate')
        self.fg.description(description)
        self.fg.language(language)
        self.fg.generator('rss2pod', '1.0.0', 'https://github.com/rss2pod')
        self.fg.pubDate(datetime.now(timezone.utc))
        self.fg.lastBuildDate(datetime.now(timezone.utc))
        
        # iTunes podcast extension
        self.fg.podcast.itunes_author(author or title)
        self.fg.podcast.itunes_summary(description)
        self.fg.podcast.itunes_type('episodic')  # or 'serial'
        
        if image:
            self.fg.image(image)
            self.fg.podcast.itunes_image(image)
        
        if category:
            # iTunes category format: itunes_category(category, subcategory)
            # category: main category like 'Technology'
            # subcategory: optional subcategory like 'Podcasting'
            self.fg.podcast.itunes_category(category)
        
        self.entries: List[FeedEntry] = []
    
    def add_episode(self, 
                   episode_id: str,
                   title: str,
                   link: str,
                   audio_url: str,
                   audio_length: int,
                   audio_type: str = 'audio/mpeg',
                   description: str = None,
                   content_html: str = None,
                   pub_date: datetime = None,
                   duration: str = None,
                   episode_number: int = None,
                   season_number: int = None,
                   explicit: bool = False,
                   image: str = None,
                   keywords: List[str] = None) -> FeedEntry:
        """
        Add an episode to the feed.
        
        Args:
            episode_id: Unique identifier for the episode
            title: Episode title
            link: Episode page link
            audio_url: Direct URL to audio file (supports HTTP Range)
            audio_length: File size in bytes
            audio_type: MIME type (default: audio/mpeg)
            description: Episode description
            content_html: Full HTML content (AntennaPod compatible)
            pub_date: Publication date (default: now)
            duration: Duration in HH:MM:SS or seconds
            episode_number: Episode number
            season_number: Season number
            explicit: Explicit content flag
            image: Episode-specific image
            keywords: List of keywords/tags
        
        Returns:
            The created FeedEntry
        """
        fe = self.fg.add_entry(order='append')
        
        # Basic RSS fields
        fe.id(self._generate_guid(episode_id))
        fe.title(title)
        fe.link(href=link, rel='alternate')
        
        # Publication date
        if pub_date is None:
            pub_date = datetime.now(timezone.utc)
        fe.pubDate(pub_date)
        fe.updated(pub_date)
        
        # Description and content
        if description:
            fe.description(description)
        
        # HTML content embedding (AntennaPod compatible)
        if content_html:
            # Use content:encoded for full HTML content
            fe.content(content_html, type='html')
            # Also set as description for broader compatibility
            if not description:
                fe.description(self._strip_html(content_html)[:500])
        
        # Enclosure (critical for podcast clients)
        # HTTP Range requests are supported automatically by most HTTP servers
        fe.enclosure(
            url=audio_url,
            type=audio_type,
            length=audio_length
        )
        
        # iTunes specific fields - use podcast extension on entry
        if duration:
            fe.podcast.itunes_duration(duration)
        
        if episode_number is not None:
            fe.podcast.itunes_episode(episode_number)
        
        if season_number is not None:
            fe.podcast.itunes_season(season_number)
        
        fe.podcast.itunes_explicit('yes' if explicit else 'no')
        
        if image:
            fe.podcast.itunes_image(image)
        
        if keywords:
            fe.podcast.itunes_keywords(keywords)
        
        # Store reference for later access
        self.entries.append(fe)
        return fe
    
    def _generate_guid(self, episode_id: str) -> str:
        """Generate a unique GUID for an episode."""
        # Use tag URI scheme for permanent identifiers
        timestamp = datetime.now().strftime('%Y-%m-%d')
        return f"tag:rss2pod,{timestamp}:{episode_id}"
    
    def _strip_html(self, html_content: str) -> str:
        """Strip HTML tags to get plain text."""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        # Unescape HTML entities
        text = html.unescape(text)
        # Clean up whitespace
        text = ' '.join(text.split())
        return text
    
    def rss_str(self, pretty: bool = True) -> str:
        """
        Generate RSS feed as string.
        
        Args:
            pretty: Pretty print XML (default: True)
        
        Returns:
            RSS feed as XML string
        """
        return self.fg.rss_str(pretty=pretty)
    
    def rss_file(self, filepath: str, pretty: bool = True) -> None:
        """
        Write RSS feed to file.
        
        Args:
            filepath: Output file path
            pretty: Pretty print XML (default: True)
        """
        self.fg.rss_file(filepath, pretty=pretty)
    
    def atom_str(self, pretty: bool = True) -> str:
        """Generate Atom feed as string."""
        return self.fg.atom_str(pretty=pretty)
    
    def atom_file(self, filepath: str, pretty: bool = True) -> None:
        """Write Atom feed to file."""
        self.fg.atom_file(filepath, pretty=pretty)
    
    def get_entries(self) -> List[FeedEntry]:
        """Get all entries in the feed."""
        return self.entries
    
    def entry_count(self) -> int:
        """Get number of entries in the feed."""
        return len(self.entries)


def create_podcast_feed(title: str, link: str, description: str, **kwargs) -> PodcastFeedGenerator:
    """
    Factory function to create a podcast feed generator.
    
    Args:
        title: Podcast title
        link: Podcast link
        description: Podcast description
        **kwargs: Additional arguments for PodcastFeedGenerator
    
    Returns:
        PodcastFeedGenerator instance
    """
    return PodcastFeedGenerator(title, link, description, **kwargs)


if __name__ == '__main__':
    # Example usage
    fg = create_podcast_feed(
        title='My Podcast',
        link='https://example.com/podcast',
        description='An amazing podcast about interesting things',
        author='Podcast Host',
        image='https://example.com/cover.jpg',
        category='Technology'
    )
    
    fg.add_episode(
        episode_id='ep001',
        title='First Episode',
        link='https://example.com/podcast/ep001',
        audio_url='https://example.com/audio/ep001.mp3',
        audio_length=12345678,
        description='This is the first episode',
        content_html='<p>This is the <strong>full HTML content</strong> of the episode.</p>',
        duration='00:45:30',
        episode_number=1,
        keywords=['tech', 'podcast', 'first']
    )
    
    print(fg.rss_str())
