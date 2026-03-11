#!/usr/bin/env python3
"""
RSS2Pod Script Generation Module.

This package provides tools for generating podcast scripts from RSS feed content,
including support for:
- Single and dual host formats
- Educational content enhancement
- English learning features
- Structured speaker output

Modules:
    script_engine: Core abstraction for script generation
    prompt_templates: LLM prompt templates for different formats
    english_learning: English learning enhancement features
    speaker_output: Speaker list output and analysis utilities
"""

from .script_engine import (
    Speaker,
    SpeakerRole,
    ScriptSegment,
    PodcastScript,
    ScriptEngine,
    BaseScriptEngine,
    create_speaker
)

from .prompt_templates import (
    TemplateType,
    PromptTemplate,
    TemplateRegistry,
    registry,
    get_template,
    create_single_host_script_prompt,
    create_dual_host_script_prompt
)

from .english_learning import (
    DifficultyLevel,
    VocabularyItem,
    SentenceTranslation,
    LearningEnhancement,
    EnglishLearningEnhancer,
    create_vocabulary_list,
    create_study_guide
)

from .speaker_output import (
    SpeakerExporter,
    ScriptAnalyzer,
    output_speaker_list,
    create_sample_script
)

__version__ = "0.1.0"
__author__ = "RSS2Pod Team"

__all__ = [
    # Script Engine
    "Speaker",
    "SpeakerRole",
    "ScriptSegment",
    "PodcastScript",
    "ScriptEngine",
    "BaseScriptEngine",
    "create_speaker",
    
    # Prompt Templates
    "TemplateType",
    "PromptTemplate",
    "TemplateRegistry",
    "registry",
    "get_template",
    "create_single_host_script_prompt",
    "create_dual_host_script_prompt",
    
    # English Learning
    "DifficultyLevel",
    "VocabularyItem",
    "SentenceTranslation",
    "LearningEnhancement",
    "EnglishLearningEnhancer",
    "create_vocabulary_list",
    "create_study_guide",
    
    # Speaker Output
    "SpeakerExporter",
    "ScriptAnalyzer",
    "output_speaker_list",
    "create_sample_script",
]
