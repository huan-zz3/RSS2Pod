#!/usr/bin/env python3
"""
LLM Module for RSS2Pod
Provides LLM client, source summarization, group aggregation, and trigger engine.
"""

from .llm_client import (
    LLMClient,
    DashScopeClient,
    MockLLMClient,
    create_llm_client
)

from .source_summarizer import (
    Article,
    SourceSummarizer,
    summarize_source
)

from .group_aggregator import (
    SourceSummary,
    GroupAggregator,
    aggregate_group
)

from .trigger_engine import (
    TriggerType,
    TriggerConfig,
    TriggerResult,
    TriggerEngine,
    create_cron_trigger,
    create_count_trigger,
    create_llm_trigger
)

__all__ = [
    # LLM Client
    "LLMClient",
    "DashScopeClient",
    "MockLLMClient",
    "create_llm_client",
    
    # Source Summarizer
    "Article",
    "SourceSummarizer",
    "summarize_source",
    
    # Group Aggregator
    "SourceSummary",
    "GroupAggregator",
    "aggregate_group",
    
    # Trigger Engine
    "TriggerType",
    "TriggerConfig",
    "TriggerResult",
    "TriggerEngine",
    "create_cron_trigger",
    "create_count_trigger",
    "create_llm_trigger",
]

__version__ = "1.0.0"
