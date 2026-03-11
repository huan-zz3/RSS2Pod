# Podcast Script Generation Module - Implementation Summary

## Overview

This module provides a comprehensive system for generating podcast scripts from RSS feed content, with built-in support for English learning enhancements and structured speaker output.

## Files Created

### 1. `script_engine.py` (7.7 KB)
**Core abstraction layer for podcast script generation.**

Key Components:
- `SpeakerRole` enum: host, co_host, guest, narrator
- `Speaker` dataclass: Represents a podcast speaker with lines, tone, speaking rate
- `ScriptSegment` dataclass: A segment of the podcast (intro, content, outro, etc.)
- `PodcastScript` dataclass: Complete podcast script container
- `ScriptEngine` abstract base class: Interface for script generation engines
- `BaseScriptEngine`: Base implementation with common functionality
- `create_speaker()`: Factory function for creating speakers

Features:
- Structured data classes with `to_dict()` methods for JSON serialization
- Duration estimation based on word count and speaking rate
- Speaker tracking across segments
- Full JSON export capability

### 2. `prompt_templates.py` (13.7 KB)
**LLM prompt templates for different podcast formats.**

Templates Included:
- `single_host_standard`: Single host narration format
- `dual_host_conversation`: Two-host conversational format
- `educational_standard`: Educational content format
- `interview_standard`: Interview format

Key Components:
- `TemplateType` enum: Categorizes template types
- `PromptTemplate` dataclass: Template with system/user prompts
- `TemplateRegistry`: Manages and provides access to templates
- Convenience functions: `create_single_host_script_prompt()`, `create_dual_host_script_prompt()`

Features:
- Variable substitution in templates
- Type-safe template management
- Pre-configured prompts for common formats
- Easy integration with LLM APIs

### 3. `english_learning.py` (17.5 KB)
**English learning enhancement features.**

Key Components:
- `DifficultyLevel` enum: CEFR levels (A1-C2)
- `VocabularyItem` dataclass: Word with definition, pronunciation, examples
- `SentenceTranslation` dataclass: Sentence with translations and notes
- `LearningEnhancement` dataclass: Complete enhancement for a segment
- `EnglishLearningEnhancer` class: Main enhancement engine

Features:
- Vocabulary analysis and difficulty assessment
- Sentence translation with grammar notes
- Key phrase extraction
- Comprehension question generation
- Study guide creation
- Vocabulary list generation (Markdown, plain text)

### 4. `speaker_output.py` (12.4 KB)
**Speaker list output and analysis utilities.**

Key Components:
- `SpeakerExporter`: Export speakers to JSON, YAML, CSV, Markdown
- `ScriptAnalyzer`: Analyze scripts and generate statistics
- `output_speaker_list()`: Convenience function for formatted output
- `create_sample_script()`: Create demo script for testing

Features:
- Multiple export formats (JSON, YAML, CSV, Markdown)
- Speaker statistics (line counts, speaking time estimates)
- Segment breakdown analysis
- Full script reporting

### 5. `main.py` (13.5 KB)
**High-level integration module.**

Key Components:
- `PodcastScriptGenerator`: Main generator class integrating all components
- `generate_podcast_script()`: Convenience function for quick generation

Features:
- Configuration-driven script generation
- Automatic learning enhancement integration
- Multi-format export (JSON, Markdown)
- Complete workflow from content to final script

### 6. `__init__.py` (2.0 KB)
**Package initialization and public API exports.**

Exports all major classes and functions for easy importing:
```python
from script import (
    Speaker, PodcastScript, ScriptSegment,
    TemplateType, get_template,
    EnglishLearningEnhancer,
    SpeakerExporter, ScriptAnalyzer,
    generate_podcast_script
)
```

### 7. `README.md` (7.4 KB)
**Comprehensive documentation.**

Includes:
- Quick start guide
- API reference
- Usage examples
- Integration examples with LLM APIs
- Output format examples

### 8. `MODULE_SUMMARY.md` (This file)
**Implementation summary and module overview.**

## Module Structure

```
rss2pod/
└── script/
    ├── __init__.py              # Package exports
    ├── script_engine.py         # Core data structures and interfaces
    ├── prompt_templates.py      # LLM prompt templates
    ├── english_learning.py      # English learning features
    ├── speaker_output.py        # Output and analysis utilities
    ├── main.py                  # High-level integration
    ├── README.md                # User documentation
    └── MODULE_SUMMARY.md        # This summary
```

## Usage Examples

### Basic Script Generation

```python
from script import generate_podcast_script

script = generate_podcast_script(
    content="Your article text here...",
    title="Episode Title",
    format="dual_host",
    hosts=["Alex", "Sam"],
    duration=10,
    with_learning=True
)

# Access structured speaker list
speakers = script['speakers']
for speaker in speakers:
    print(f"{speaker['name']}: {len(speaker['lines'])} lines")
```

### Advanced Usage

```python
from script import PodcastScriptGenerator, ScriptAnalyzer

config = {
    "format": "dual_host",
    "host_names": ["Alex", "Sam"],
    "tone": "conversational",
    "duration": 15,
    "learning_enhancements": True,
    "target_language": "zh"
}

generator = PodcastScriptGenerator(config)
script = generator.generate_script(content, "Episode Title")

# Get statistics
stats = ScriptAnalyzer.get_speaker_statistics(script)
print(f"Total speakers: {stats['total_speakers']}")
print(f"Speaking time: {stats['speaking_time_estimate']}")

# Export
generator.export_script(script, "output.json", format="json")
```

### English Learning Features

```python
from script import EnglishLearningEnhancer, create_study_guide

enhancer = EnglishLearningEnhancer(target_language="zh")
enhancement = enhancer.enhance_script_segment(
    segment_id="intro",
    text="Podcast script text..."
)

# Get vocabulary
for vocab in enhancement.vocabulary:
    print(f"{vocab.word}: {vocab.definition}")

# Create study guide
guide = create_study_guide(enhancement)
print(guide)
```

## Output Examples

### Structured Speaker List (JSON)

```json
{
  "speakers": [
    {
      "name": "Alex",
      "role": "host",
      "lines": ["Welcome to the podcast!", "Today we discuss AI."],
      "tone": "energetic",
      "speaking_rate": "normal"
    },
    {
      "name": "Sam",
      "role": "co_host",
      "lines": ["Thanks Alex! Exciting topic."],
      "tone": "friendly",
      "speaking_rate": "normal"
    }
  ],
  "statistics": {
    "total_speakers": 2,
    "total_lines": 3,
    "lines_per_speaker": {"Alex": 2, "Sam": 1},
    "speaking_time_estimate": {"Alex": 8.5, "Sam": 6.2}
  }
}
```

### Speaker Statistics

- Total speakers count
- Speakers by role (host, co_host, guest, narrator)
- Speakers by tone
- Total lines and lines per speaker
- Estimated speaking time per speaker

### Learning Enhancements

- Vocabulary lists with definitions, pronunciations, translations
- Sentence translations with grammar notes
- Comprehension questions
- Study guides in Markdown format

## Testing

All modules include self-test functionality:

```bash
cd rss2pod/script
python3 script_engine.py      # Test core structures
python3 prompt_templates.py   # Test templates
python3 english_learning.py   # Test learning features
python3 speaker_output.py     # Test output utilities
python3 main.py               # Full integration test
```

## Integration Points

### LLM API Integration

The `prompt_templates.py` module provides ready-to-use prompts for LLM APIs:

```python
from script import get_template

template = get_template("dual_host_conversation")
prompts = template.render(
    content=article_text,
    host1_name="Alex",
    host2_name="Sam",
    tone="friendly",
    duration_minutes=10
)

# Send to LLM API
# response = llm_api.generate(system=prompts['system'], user=prompts['user'])
```

### RSS Feed Integration

The module is designed to work with RSS feed content:

```python
from rss2pod.fetcher import fetch_article  # hypothetical
from script import generate_podcast_script

article = fetch_article(rss_url)
script = generate_podcast_script(
    content=article.text,
    title=article.title,
    format="dual_host"
)
```

## Future Enhancements

Potential improvements:
1. Real LLM API integration for script generation
2. Actual vocabulary database for accurate difficulty ratings
3. Real translation API integration
4. Audio timing and pacing suggestions
5. Background music and sound effect cues
6. Multi-language support beyond translations
7. Custom template creation interface
8. Script versioning and comparison

## Dependencies

- Python 3.8+
- No external dependencies (pure Python)
- Optional: `pyyaml` for YAML export
- Optional: LLM API access for actual script generation

## License

Part of the RSS2Pod project.
