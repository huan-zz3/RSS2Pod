#!/usr/bin/env python3
"""
Main Script Generator - Integration module for podcast script generation.

This module demonstrates how to use all components together to generate
complete podcast scripts with learning enhancements.
"""

import json
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from script_engine import PodcastScript, ScriptSegment, create_speaker, SpeakerRole
from prompt_templates import create_dual_host_script_prompt, create_single_host_script_prompt
from english_learning import EnglishLearningEnhancer, create_study_guide
from speaker_output import output_speaker_list, ScriptAnalyzer


class PodcastScriptGenerator:
    """
    Main podcast script generator that integrates all components.
    
    This class provides a high-level interface for generating complete
    podcast scripts with optional learning enhancements.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the script generator.
        
        Args:
            config: Configuration dictionary with options like:
                - format: "single_host" or "dual_host"
                - host_names: List of host names
                - tone: Desired tone
                - duration: Target duration in minutes
                - learning_enhancements: Whether to add learning features
                - target_language: Language for translations
        """
        self.config = config or {
            "format": "dual_host",
            "host_names": ["Host 1", "Host 2"],
            "tone": "conversational",
            "duration": 10,
            "learning_enhancements": True,
            "target_language": "zh"
        }
        
        self.learning_enhancer = None
        if self.config.get("learning_enhancements", True):
            self.learning_enhancer = EnglishLearningEnhancer(
                target_language=self.config.get("target_language", "zh")
            )
    
    def generate_script(self, content: str, title: str,
                       episode_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate a complete podcast script from content.
        
        Args:
            content: Source content (RSS article, text, etc.)
            title: Podcast episode title
            episode_number: Optional episode number
            
        Returns:
            Complete script dictionary with all components
        """
        # Create basic script structure
        script = PodcastScript(
            title=title,
            episode_number=episode_number
        )
        
        # Create speakers based on format
        speakers = self._create_speakers()
        
        # Generate script segments
        segments = self._generate_segments(content, speakers)
        for segment in segments:
            script.add_segment(segment)
        
        # Build result
        result = script.to_dict()
        
        # Add learning enhancements if enabled
        if self.learning_enhancer:
            result["learning_enhancements"] = self._add_learning_enhancements(script)
        
        # Add speaker statistics
        result["speaker_statistics"] = ScriptAnalyzer.get_speaker_statistics(script)
        
        return result
    
    def _create_speakers(self) -> list:
        """Create speaker instances based on configuration."""
        speakers = []
        format_type = self.config.get("format", "dual_host")
        host_names = self.config.get("host_names", ["Host 1", "Host 2"])
        
        if format_type == "single_host":
            speaker = create_speaker(
                host_names[0],
                "host",
                tone=self.config.get("tone", "friendly"),
                speaking_rate="normal"
            )
            speakers.append(speaker)
        else:  # dual_host
            speaker1 = create_speaker(
                host_names[0],
                "host",
                tone=self.config.get("tone", "energetic"),
                speaking_rate="normal"
            )
            speaker2 = create_speaker(
                host_names[1],
                "co_host",
                tone=self.config.get("tone", "friendly"),
                speaking_rate="normal"
            )
            speakers.extend([speaker1, speaker2])
        
        return speakers
    
    def _generate_segments(self, content: str, speakers: list) -> list:
        """
        Generate script segments from content.
        
        This is a simplified implementation. In production, this would
        use LLM APIs with the prompt templates to generate actual content.
        """
        segments = []
        
        # Intro segment
        intro = ScriptSegment(
            segment_type="intro",
            speakers=speakers.copy(),
            duration_estimate=30.0
        )
        speakers[0].add_line(f"Welcome to our podcast!")
        if len(speakers) > 1:
            speakers[1].add_line("Great to be here today!")
        segments.append(intro)
        
        # Content segment
        content_segment = ScriptSegment(
            segment_type="content",
            speakers=speakers.copy(),
            duration_estimate=self.config.get("duration", 10) * 60 - 60
        )
        
        # Split content into lines for each speaker
        sentences = content.split('.')
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                speaker_idx = i % len(speakers)
                speakers[speaker_idx].add_line(sentence.strip() + '.')
        
        segments.append(content_segment)
        
        # Outro segment
        outro = ScriptSegment(
            segment_type="outro",
            speakers=[speakers[0]],
            duration_estimate=30.0
        )
        speakers[0].add_line("Thanks for listening! See you next time.")
        segments.append(outro)
        
        return segments
    
    def _add_learning_enhancements(self, script: PodcastScript) -> Dict[str, Any]:
        """Add learning enhancements to the script."""
        if not self.learning_enhancer:
            return {}
        
        enhancements = {
            "segments": [],
            "vocabulary_list": [],
            "study_guides": []
        }
        
        # Process each segment
        for i, segment in enumerate(script.segments):
            # Combine all text from segment
            text_parts = []
            for speaker in segment.speakers:
                text_parts.extend(speaker.lines)
            segment_text = ' '.join(text_parts)
            
            if segment_text:
                enhancement = self.learning_enhancer.enhance_script_segment(
                    segment_id=f"segment_{i}_{segment.segment_type}",
                    text=segment_text
                )
                enhancements["segments"].append(enhancement.to_dict())
                
                # Collect vocabulary (convert to dict for JSON serialization)
                for vocab in enhancement.vocabulary:
                    enhancements["vocabulary_list"].append(vocab.to_dict())
                
                # Create study guide
                study_guide = create_study_guide(enhancement)
                enhancements["study_guides"].append({
                    "segment_id": enhancement.segment_id,
                    "guide": study_guide
                })
        
        return enhancements
    
    def export_script(self, script_dict: Dict[str, Any], 
                     output_path: str,
                     format: str = "json") -> None:
        """
        Export script to file.
        
        Args:
            script_dict: Script dictionary
            output_path: Path to output file
            format: Export format (json, yaml, markdown)
        """
        if format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(script_dict, f, indent=2, ensure_ascii=False)
        
        elif format == "markdown":
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# {script_dict['title']}\n\n")
                
                # Write segments
                f.write("## Script Content\n\n")
                for segment in script_dict.get('segments', []):
                    f.write(f"### {segment['segment_type']}\n\n")
                    for speaker in segment.get('speakers', []):
                        f.write(f"**{speaker['name']}:**\n")
                        for line in speaker.get('lines', []):
                            f.write(f"- {line}\n")
                        f.write("\n")
                
                # Write speaker list
                f.write("## Speakers\n\n")
                speaker_md = output_speaker_list(
                    self._dict_to_script(script_dict),
                    format="markdown"
                )
                f.write(speaker_md)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _dict_to_script(self, script_dict: Dict[str, Any]) -> PodcastScript:
        """Convert dictionary back to PodcastScript object."""
        script = PodcastScript(
            title=script_dict['title'],
            episode_number=script_dict.get('episode_number')
        )
        
        for seg_dict in script_dict.get('segments', []):
            segment = ScriptSegment(
                segment_type=seg_dict['segment_type'],
                speakers=[],
                duration_estimate=seg_dict.get('duration_estimate', 0)
            )
            
            for spk_dict in seg_dict.get('speakers', []):
                speaker = create_speaker(
                    spk_dict['name'],
                    spk_dict['role'],
                    tone=spk_dict.get('tone', 'friendly'),
                    speaking_rate=spk_dict.get('speaking_rate', 'normal')
                )
                speaker.lines = spk_dict.get('lines', [])
                segment.speakers.append(speaker)
            
            script.add_segment(segment)
        
        return script


def generate_podcast_script(content: str,
                           title: str,
                           format: str = "dual_host",
                           hosts: list = None,
                           duration: int = 10,
                           with_learning: bool = True) -> Dict[str, Any]:
    """
    Convenience function to generate a podcast script.
    
    Args:
        content: Source content
        title: Episode title
        format: "single_host" or "dual_host"
        hosts: List of host names
        duration: Target duration in minutes
        with_learning: Whether to include learning enhancements
        
    Returns:
        Complete script dictionary
    """
    config = {
        "format": format,
        "host_names": hosts or (["Host"] if format == "single_host" else ["Host 1", "Host 2"]),
        "tone": "conversational",
        "duration": duration,
        "learning_enhancements": with_learning,
        "target_language": "zh"
    }
    
    generator = PodcastScriptGenerator(config)
    return generator.generate_script(content, title)


# Example usage and testing
if __name__ == "__main__":
    print("=== RSS2Pod Script Generator Demo ===\n")
    
    # Sample content
    sample_content = """
    Artificial intelligence is transforming healthcare. Machine learning algorithms 
    can now analyze medical images with accuracy matching expert radiologists. 
    Furthermore, AI-powered diagnostic tools are helping doctors identify diseases 
    earlier than ever before. Personalized treatment plans are becoming more 
    sophisticated thanks to AI analysis of patient data.
    """
    
    # Generate script
    print("Generating podcast script...\n")
    script = generate_podcast_script(
        content=sample_content,
        title="AI in Healthcare",
        format="dual_host",
        hosts=["Alex", "Sam"],
        duration=5,
        with_learning=True
    )
    
    # Output structured speaker list
    print("=== Structured Speaker List ===")
    print(json.dumps(script.get('speakers', []), indent=2, ensure_ascii=False))
    
    # Output speaker statistics
    print("\n=== Speaker Statistics ===")
    stats = script.get('speaker_statistics', {})
    print(f"Total Speakers: {stats.get('total_speakers', 0)}")
    print(f"Total Lines: {stats.get('total_lines', 0)}")
    print(f"Lines per Speaker: {stats.get('lines_per_speaker', {})}")
    print(f"Speaking Time Estimate: {stats.get('speaking_time_estimate', {})}")
    
    # Output learning enhancements summary
    if script.get('learning_enhancements'):
        print("\n=== Learning Enhancements ===")
        enhancements = script['learning_enhancements']
        print(f"Segments enhanced: {len(enhancements.get('segments', []))}")
        print(f"Vocabulary items: {len(enhancements.get('vocabulary_list', []))}")
        print(f"Study guides: {len(enhancements.get('study_guides', []))}")
    
    # Save to file
    print("\n=== Saving Script ===")
    config = {
        "format": "dual_host",
        "host_names": ["Alex", "Sam"],
        "tone": "conversational",
        "duration": 5,
        "learning_enhancements": True
    }
    generator = PodcastScriptGenerator(config)
    generator.export_script(script, "/tmp/podcast_script.json", format="json")
    print("Script saved to /tmp/podcast_script.json")
    
    print("\n=== Demo Complete ===")
