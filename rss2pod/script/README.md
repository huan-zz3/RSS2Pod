# RSS2Pod Script Generation Module

This module provides comprehensive tools for generating podcast scripts from RSS feed content, with support for English learning enhancements.

## Features

- **Multiple Format Support**: Single host, dual host, interview, and educational formats
- **Structured Output**: JSON, YAML, CSV, and Markdown export options
- **English Learning**: Vocabulary explanations, sentence translations, comprehension questions
- **Speaker Management**: Create, track, and analyze speaker roles and dialogue
- **LLM Integration**: Ready-to-use prompt templates for AI script generation

## Module Structure

```
script/
├── __init__.py              # Package initialization and exports
├── script_engine.py         # Core abstraction (Speaker, PodcastScript, ScriptEngine)
├── prompt_templates.py      # LLM prompt templates for different formats
├── english_learning.py      # English learning enhancement features
├── speaker_output.py        # Speaker list output and analysis utilities
├── main.py                  # High-level integration and examples
└── README.md                # This file
```

## Quick Start

### Basic Usage

```python
from script import (
    generate_podcast_script,
    PodcastScriptGenerator,
    output_speaker_list
)

# Quick generation
script = generate_podcast_script(
    content="Your article text here...",
    title="Episode Title",
    format="dual_host",
    hosts=["Alex", "Sam"],
    duration=10,
    with_learning=True
)

# Get structured speaker list
speakers_json = output_speaker_list(script, format="json")
print(speakers_json)
```

### Advanced Usage

```python
from script import PodcastScriptGenerator, EnglishLearningEnhancer

# Custom configuration
config = {
    "format": "dual_host",
    "host_names": ["Alex", "Sam"],
    "tone": "conversational",
    "duration": 15,
    "learning_enhancements": True,
    "target_language": "zh"
}

generator = PodcastScriptGenerator(config)
script = generator.generate_script(
    content="Article text...",
    title="My Podcast Episode",
    episode_number=1
)

# Export to different formats
generator.export_script(script, "output.json", format="json")
generator.export_script(script, "output.md", format="markdown")
```

### English Learning Features

```python
from script import EnglishLearningEnhancer, create_study_guide

enhancer = EnglishLearningEnhancer(target_language="zh")

# Enhance a text segment
enhancement = enhancer.enhance_script_segment(
    segment_id="intro_001",
    text="Your podcast script text..."
)

# Get vocabulary list
vocab_items = enhancement.vocabulary
for item in vocab_items:
    print(f"{item.word}: {item.definition}")

# Create study guide
study_guide = create_study_guide(enhancement)
print(study_guide)
```

### Speaker Analysis

```python
from script import ScriptAnalyzer, create_sample_script

script = create_sample_script()
analyzer = ScriptAnalyzer()

# Get speaker statistics
stats = analyzer.get_speaker_statistics(script)
print(f"Total speakers: {stats['total_speakers']}")
print(f"Lines per speaker: {stats['lines_per_speaker']}")

# Get segment breakdown
breakdown = analyzer.get_segment_breakdown(script)
for segment in breakdown:
    print(f"Segment {segment['segment_number']}: {segment['segment_type']}")
    print(f"  Duration: {segment['duration_estimate']}s")
    print(f"  Speakers: {segment['speakers']}")
```

## API Reference

### Core Classes

#### `PodcastScript`
Complete podcast script container.
- `title`: Episode title
- `episode_number`: Optional episode number
- `segments`: List of ScriptSegment objects
- `total_duration`: Total estimated duration
- `get_all_speakers()`: Get all unique speakers
- `to_dict()`: Convert to dictionary
- `to_json()`: Convert to JSON string

#### `ScriptSegment`
A segment of the podcast script.
- `segment_type`: Type (intro, content, summary, outro)
- `speakers`: List of Speaker objects
- `duration_estimate`: Estimated duration in seconds
- `metadata`: Additional metadata

#### `Speaker`
Represents a podcast speaker.
- `name`: Speaker's name
- `role`: SpeakerRole enum (host, co_host, guest, narrator)
- `lines`: List of dialogue lines
- `tone`: Voice tone
- `speaking_rate`: Speaking rate (slow, normal, fast)
- `add_line(line)`: Add a dialogue line
- `to_dict()`: Convert to dictionary

### Prompt Templates

Available templates:
- `single_host_standard`: Single host narration
- `dual_host_conversation`: Two-host dialogue
- `educational_standard`: Educational content
- `interview_standard`: Interview format

```python
from script import get_template, create_dual_host_script_prompt

# Get a template
template = get_template("dual_host_conversation")
prompts = template.render(
    content="Your content...",
    host1_name="Alex",
    host2_name="Sam",
    tone="conversational",
    duration_minutes=10
)

# Or use convenience function
prompts = create_dual_host_script_prompt(
    content="Your content...",
    host1="Alex",
    host2="Sam"
)
```

### Output Formats

Supported export formats:
- `json`: Structured JSON with all details
- `yaml`: YAML format for configuration
- `csv`: CSV for spreadsheet analysis
- `markdown`: Human-readable documentation
- `dict`: Python dictionary

## Integration with LLM APIs

The prompt templates are designed to work with LLM APIs:

```python
from script import get_template
import requests  # or your preferred LLM client

template = get_template("dual_host_conversation")
prompts = template.render(
    content=article_text,
    host1_name="Alex",
    host2_name="Sam",
    tone="friendly",
    duration_minutes=10,
    include_elements="introduction, main points, summary"
)

# Send to LLM API
response = requests.post(
    "https://api.example.com/generate",
    json={
        "system": prompts["system"],
        "user": prompts["user"]
    }
)

# Parse LLM response into script structure
script_data = response.json()
```

## Output Examples

### Structured Speaker List (JSON)

```json
{
  "speakers": [
    {
      "name": "Alex",
      "role": "host",
      "lines": [
        "Welcome to the podcast!",
        "Today we're discussing AI."
      ],
      "tone": "energetic",
      "speaking_rate": "normal"
    },
    {
      "name": "Sam",
      "role": "co_host",
      "lines": [
        "Thanks Alex! Exciting topic."
      ],
      "tone": "friendly",
      "speaking_rate": "normal"
    }
  ],
  "statistics": {
    "total_speakers": 2,
    "total_lines": 3,
    "lines_per_speaker": {
      "Alex": 2,
      "Sam": 1
    }
  }
}
```

### Study Guide (Markdown)

```markdown
# Study Guide: segment_0_intro

## Summary
Welcome to the podcast where we discuss artificial intelligence...

## New Vocabulary
- **artificial** (/ˌɑːrtɪˈfɪʃl/): Made by humans
- **intelligence** (/ɪnˈtelɪdʒəns/): Ability to learn and understand

## Key Sentences
- Welcome to the podcast!
  - zh: 欢迎来到播客！

## Comprehension Questions
1. What is the main topic of this episode?
2. Who are the hosts?
3. What new vocabulary did you learn?
```

## Testing

Run the module directly to see examples:

```bash
cd rss2pod/script
python main.py
python script_engine.py
python prompt_templates.py
python english_learning.py
python speaker_output.py
```

## Dependencies

- Python 3.8+
- Optional: `pyyaml` for YAML export
- Optional: LLM API access for script generation

## License

Part of the RSS2Pod project.
