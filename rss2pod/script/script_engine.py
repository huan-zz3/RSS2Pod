#!/usr/bin/env python3
"""
Script Engine - Abstract interface for podcast script generation.

This module provides the core abstraction for generating podcast scripts
from RSS feed content. It defines the base classes and interfaces that
all script generators must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class SpeakerRole(Enum):
    """Defines the role of a speaker in the podcast."""
    HOST = "host"
    CO_HOST = "co_host"
    GUEST = "guest"
    NARRATOR = "narrator"


@dataclass
class Speaker:
    """Represents a speaker in the podcast script."""
    name: str
    role: SpeakerRole
    lines: List[str] = field(default_factory=list)
    tone: str = "friendly"
    speaking_rate: str = "normal"  # slow, normal, fast
    
    def add_line(self, line: str):
        """Add a line of dialogue for this speaker."""
        self.lines.append(line)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert speaker to dictionary format."""
        return {
            "name": self.name,
            "role": self.role.value,
            "lines": self.lines,
            "tone": self.tone,
            "speaking_rate": self.speaking_rate
        }


@dataclass
class ScriptSegment:
    """Represents a segment of the podcast script."""
    segment_type: str  # intro, content, summary, outro, etc.
    speakers: List[Speaker]
    duration_estimate: float = 0.0  # in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary format."""
        return {
            "segment_type": self.segment_type,
            "speakers": [s.to_dict() for s in self.speakers],
            "duration_estimate": self.duration_estimate,
            "metadata": self.metadata
        }


@dataclass
class PodcastScript:
    """Complete podcast script containing all segments."""
    title: str
    episode_number: Optional[int] = None
    segments: List[ScriptSegment] = field(default_factory=list)
    total_duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_segment(self, segment: ScriptSegment):
        """Add a segment to the script."""
        self.segments.append(segment)
        self.total_duration += segment.duration_estimate
    
    def get_all_speakers(self) -> List[Speaker]:
        """Get all unique speakers in the script."""
        speakers = {}
        for segment in self.segments:
            for speaker in segment.speakers:
                if speaker.name not in speakers:
                    speakers[speaker.name] = speaker
        return list(speakers.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entire script to dictionary format."""
        return {
            "title": self.title,
            "episode_number": self.episode_number,
            "segments": [s.to_dict() for s in self.segments],
            "total_duration": self.total_duration,
            "metadata": self.metadata,
            "speakers": [s.to_dict() for s in self.get_all_speakers()]
        }
    
    def to_json(self) -> str:
        """Convert script to JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class ScriptEngine(ABC):
    """
    Abstract base class for podcast script generation engines.
    
    All script engines must implement this interface to ensure
    consistent script generation across different formats and styles.
    """
    
    @abstractmethod
    def generate_script(self, content: str, config: Dict[str, Any]) -> PodcastScript:
        """
        Generate a complete podcast script from content.
        
        Args:
            content: The source content (e.g., RSS article text)
            config: Configuration options for script generation
            
        Returns:
            PodcastScript: Complete structured script
        """
        pass
    
    @abstractmethod
    def generate_segment(self, segment_type: str, content: str, 
                        speakers: List[Speaker]) -> ScriptSegment:
        """
        Generate a specific segment of the podcast.
        
        Args:
            segment_type: Type of segment (intro, content, summary, outro)
            content: Content for this segment
            speakers: List of speakers for this segment
            
        Returns:
            ScriptSegment: Generated segment
        """
        pass
    
    @abstractmethod
    def estimate_duration(self, text: str, speaking_rate: str = "normal") -> float:
        """
        Estimate speaking duration for given text.
        
        Args:
            text: Text to estimate duration for
            speaking_rate: Rate of speech (slow, normal, fast)
            
        Returns:
            float: Estimated duration in seconds
        """
        pass


class BaseScriptEngine(ScriptEngine):
    """
    Base implementation of ScriptEngine with common functionality.
    
    Provides default implementations for common methods while
    leaving specific generation logic to subclasses.
    """
    
    # Average words per minute for different speaking rates
    WPM_RATES = {
        "slow": 130,
        "normal": 150,
        "fast": 170
    }
    
    def estimate_duration(self, text: str, speaking_rate: str = "normal") -> float:
        """Estimate duration based on word count and speaking rate."""
        word_count = len(text.split())
        wpm = self.WPM_RATES.get(speaking_rate, 150)
        return (word_count / wpm) * 60
    
    def generate_script(self, content: str, config: Dict[str, Any]) -> PodcastScript:
        """Default implementation - should be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement generate_script")
    
    def generate_segment(self, segment_type: str, content: str,
                        speakers: List[Speaker]) -> ScriptSegment:
        """Default implementation - should be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement generate_segment")


def create_speaker(name: str, role: str, tone: str = "friendly", 
                   speaking_rate: str = "normal") -> Speaker:
    """
    Factory function to create a Speaker instance.
    
    Args:
        name: Speaker's name
        role: Role as string (host, co_host, guest, narrator)
        tone: Tone of voice
        speaking_rate: Speaking rate
        
    Returns:
        Speaker: Created speaker instance
    """
    role_enum = SpeakerRole(role)
    return Speaker(
        name=name,
        role=role_enum,
        tone=tone,
        speaking_rate=speaking_rate
    )


# Example usage and testing
if __name__ == "__main__":
    # Create sample speakers
    host = create_speaker("Alex", "host", tone="energetic")
    co_host = create_speaker("Sam", "co_host", tone="friendly")
    
    # Add some lines
    host.add_line("Welcome to today's podcast!")
    co_host.add_line("Thanks for having me, Alex!")
    
    # Create a segment
    segment = ScriptSegment(
        segment_type="intro",
        speakers=[host, co_host],
        duration_estimate=30.0
    )
    
    # Create full script
    script = PodcastScript(
        title="Sample Podcast Episode",
        episode_number=1
    )
    script.add_segment(segment)
    
    # Output structured speaker list
    print("Structured Speakers:")
    for speaker in script.get_all_speakers():
        print(f"  - {speaker.to_dict()}")
    
    print("\nFull Script JSON:")
    print(script.to_json())
