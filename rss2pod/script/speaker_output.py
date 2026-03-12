#!/usr/bin/env python3
"""
Speaker Output Module - Generate structured speaker lists and reports.

This module provides utilities for outputting speaker information
in various formats (JSON, YAML, Markdown, CSV) for podcast scripts.
"""

import json
import csv
import io
from typing import List, Dict, Any

from .script_engine import Speaker, PodcastScript


class SpeakerExporter:
    """Export speaker information in various formats."""
    
    @staticmethod
    def to_json(speakers: List[Speaker], indent: int = 2) -> str:
        """
        Export speakers to JSON format.
        
        Args:
            speakers: List of Speaker objects
            indent: JSON indentation level
            
        Returns:
            JSON string
        """
        data = [speaker.to_dict() for speaker in speakers]
        return json.dumps(data, indent=indent, ensure_ascii=False)
    
    @staticmethod
    def to_yaml(speakers: List[Speaker]) -> str:
        """
        Export speakers to YAML format.
        
        Args:
            speakers: List of Speaker objects
            
        Returns:
            YAML string
        """
        try:
            import yaml
            data = [speaker.to_dict() for speaker in speakers]
            return yaml.dump(data, allow_unicode=True, default_flow_style=False)
        except ImportError:
            # Fallback to simple YAML-like format
            lines = []
            for speaker in speakers:
                lines.append(f"- name: {speaker.name}")
                lines.append(f"  role: {speaker.role.value}")
                lines.append(f"  tone: {speaker.tone}")
                lines.append(f"  speaking_rate: {speaker.speaking_rate}")
                lines.append("  lines:")
                for line in speaker.lines:
                    lines.append(f"    - \"{line}\"")
                lines.append("")
            return '\n'.join(lines)
    
    @staticmethod
    def to_csv(speakers: List[Speaker], include_lines: bool = False) -> str:
        """
        Export speakers to CSV format.
        
        Args:
            speakers: List of Speaker objects
            include_lines: Whether to include dialogue lines
            
        Returns:
            CSV string
        """
        output = io.StringIO()
        
        if include_lines:
            # Format: name, role, tone, speaking_rate, line_number, line_text
            writer = csv.writer(output)
            writer.writerow(['name', 'role', 'tone', 'speaking_rate', 'line_number', 'line_text'])
            
            for speaker in speakers:
                if speaker.lines:
                    for i, line in enumerate(speaker.lines, 1):
                        writer.writerow([
                            speaker.name,
                            speaker.role.value,
                            speaker.tone,
                            speaker.speaking_rate,
                            i,
                            line
                        ])
                else:
                    writer.writerow([
                        speaker.name,
                        speaker.role.value,
                        speaker.tone,
                        speaker.speaking_rate,
                        0,
                        ""
                    ])
        else:
            # Format: name, role, tone, speaking_rate, line_count
            writer = csv.writer(output)
            writer.writerow(['name', 'role', 'tone', 'speaking_rate', 'line_count'])
            
            for speaker in speakers:
                writer.writerow([
                    speaker.name,
                    speaker.role.value,
                    speaker.tone,
                    speaker.speaking_rate,
                    len(speaker.lines)
                ])
        
        return output.getvalue()
    
    @staticmethod
    def to_markdown(speakers: List[Speaker], include_lines: bool = True) -> str:
        """
        Export speakers to Markdown format.
        
        Args:
            speakers: List of Speaker objects
            include_lines: Whether to include dialogue lines
            
        Returns:
            Markdown string
        """
        lines = ["# Speaker List\n"]
        
        for speaker in speakers:
            lines.append(f"## {speaker.name}")
            lines.append(f"- **Role:** {speaker.role.value}")
            lines.append(f"- **Tone:** {speaker.tone}")
            lines.append(f"- **Speaking Rate:** {speaker.speaking_rate}")
            lines.append(f"- **Total Lines:** {len(speaker.lines)}")
            
            if include_lines and speaker.lines:
                lines.append("\n### Dialogue\n")
                for i, line in enumerate(speaker.lines, 1):
                    lines.append(f"{i}. {line}")
            
            lines.append("")
        
        return '\n'.join(lines)
    
    @staticmethod
    def to_dict(speakers: List[Speaker]) -> List[Dict[str, Any]]:
        """
        Convert speakers to list of dictionaries.
        
        Args:
            speakers: List of Speaker objects
            
        Returns:
            List of dictionaries
        """
        return [speaker.to_dict() for speaker in speakers]


class ScriptAnalyzer:
    """Analyze podcast scripts and generate reports."""
    
    @staticmethod
    def get_speaker_statistics(script: PodcastScript) -> Dict[str, Any]:
        """
        Get statistics about speakers in a script.
        
        Args:
            script: PodcastScript object
            
        Returns:
            Dictionary with speaker statistics
        """
        speakers = script.get_all_speakers()
        
        stats = {
            "total_speakers": len(speakers),
            "speakers_by_role": {},
            "speakers_by_tone": {},
            "total_lines": 0,
            "lines_per_speaker": {},
            "speaking_time_estimate": {}
        }
        
        for speaker in speakers:
            # Count by role
            role = speaker.role.value
            stats["speakers_by_role"][role] = stats["speakers_by_role"].get(role, 0) + 1
            
            # Count by tone
            tone = speaker.tone
            stats["speakers_by_tone"][tone] = stats["speakers_by_tone"].get(tone, 0) + 1
            
            # Count lines
            line_count = len(speaker.lines)
            stats["total_lines"] += line_count
            stats["lines_per_speaker"][speaker.name] = line_count
            
            # Estimate speaking time
            total_words = sum(len(line.split()) for line in speaker.lines)
            wpm = {"slow": 130, "normal": 150, "fast": 170}.get(speaker.speaking_rate, 150)
            speaking_time = (total_words / wpm) * 60
            stats["speaking_time_estimate"][speaker.name] = round(speaking_time, 2)
        
        return stats
    
    @staticmethod
    def get_segment_breakdown(script: PodcastScript) -> List[Dict[str, Any]]:
        """
        Get breakdown of script segments.
        
        Args:
            script: PodcastScript object
            
        Returns:
            List of segment information dictionaries
        """
        breakdown = []
        
        for i, segment in enumerate(script.segments):
            info = {
                "segment_number": i + 1,
                "segment_type": segment.segment_type,
                "duration_estimate": segment.duration_estimate,
                "speaker_count": len(segment.speakers),
                "speakers": [s.name for s in segment.speakers],
                "total_lines": sum(len(s.lines) for s in segment.speakers)
            }
            breakdown.append(info)
        
        return breakdown
    
    @staticmethod
    def generate_full_report(script: PodcastScript) -> Dict[str, Any]:
        """
        Generate a comprehensive report about the script.
        
        Args:
            script: PodcastScript object
            
        Returns:
            Complete report dictionary
        """
        return {
            "script_info": {
                "title": script.title,
                "episode_number": script.episode_number,
                "total_duration": script.total_duration,
                "segment_count": len(script.segments),
                "metadata": script.metadata
            },
            "speaker_statistics": ScriptAnalyzer.get_speaker_statistics(script),
            "segment_breakdown": ScriptAnalyzer.get_segment_breakdown(script),
            "speakers": SpeakerExporter.to_dict(script.get_all_speakers())
        }


def output_speaker_list(script: PodcastScript, format: str = "json",
                       include_stats: bool = True) -> str:
    """
    Output speaker list from a script in specified format.
    
    Args:
        script: PodcastScript object
        format: Output format (json, yaml, csv, markdown, dict)
        include_stats: Whether to include statistics
        
    Returns:
        Formatted speaker list
    """
    speakers = script.get_all_speakers()
    exporter = SpeakerExporter()
    
    if format == "json":
        if include_stats:
            output = {
                "speakers": exporter.to_dict(speakers),
                "statistics": ScriptAnalyzer.get_speaker_statistics(script)
            }
            return json.dumps(output, indent=2, ensure_ascii=False)
        else:
            return exporter.to_json(speakers)
    
    elif format == "yaml":
        return exporter.to_yaml(speakers)
    
    elif format == "csv":
        return exporter.to_csv(speakers, include_lines=True)
    
    elif format == "markdown":
        return exporter.to_markdown(speakers, include_lines=True)
    
    elif format == "dict":
        if include_stats:
            return {
                "speakers": exporter.to_dict(speakers),
                "statistics": ScriptAnalyzer.get_speaker_statistics(script)
            }
        else:
            return exporter.to_dict(speakers)
    
    else:
        raise ValueError(f"Unsupported format: {format}")


def create_sample_script() -> PodcastScript:
    """Create a sample podcast script for testing."""
    from script_engine import create_speaker, ScriptSegment
    
    # Create speakers
    host = create_speaker("Alex", "host", tone="energetic", speaking_rate="normal")
    host.add_line("Welcome to Tech Talk Daily!")
    host.add_line("Today we're discussing the future of AI.")
    
    co_host = create_speaker("Sam", "co_host", tone="friendly", speaking_rate="normal")
    co_host.add_line("Thanks Alex! This is such an exciting topic.")
    co_host.add_line("I've been reading about some amazing developments.")
    
    # Create segments
    intro = ScriptSegment(
        segment_type="intro",
        speakers=[host, co_host],
        duration_estimate=45.0
    )
    
    content = ScriptSegment(
        segment_type="content",
        speakers=[host, co_host],
        duration_estimate=300.0
    )
    
    host.add_line("Let's dive into the main content.")
    co_host.add_line("Absolutely! There's so much to cover.")
    
    content.speakers.append(host)
    content.speakers.append(co_host)
    
    outro = ScriptSegment(
        segment_type="outro",
        speakers=[host],
        duration_estimate=30.0
    )
    host.add_line("Thanks for listening! See you next time.")
    
    # Create script
    script = PodcastScript(
        title="Tech Talk Daily - AI Future",
        episode_number=42
    )
    script.add_segment(intro)
    script.add_segment(content)
    script.add_segment(outro)
    
    return script


# Example usage and testing
if __name__ == "__main__":
    print("=== Creating Sample Script ===\n")
    script = create_sample_script()
    
    print("=== JSON Output ===")
    json_output = output_speaker_list(script, format="json")
    print(json_output)
    
    print("\n=== Markdown Output ===")
    md_output = output_speaker_list(script, format="markdown")
    print(md_output)
    
    print("\n=== CSV Output ===")
    csv_output = output_speaker_list(script, format="csv")
    print(csv_output)
    
    print("\n=== Full Report ===")
    analyzer = ScriptAnalyzer()
    report = analyzer.generate_full_report(script)
    print(json.dumps(report, indent=2, ensure_ascii=False))
