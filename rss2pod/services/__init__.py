"""
RSS2Pod 服务层模块

提供业务逻辑封装，供 API 层和 CLI 调用。

目录结构：
- basic/      原子服务 - llm/tts/fever/group/prompt/asset/stats
- pipeline/  Pipeline服务 - models, orchestrator, processor, service
"""

from .base_service import BaseService, ServiceResult
from .config_service import ConfigService
from .database_service import DatabaseService, get_database_service
from .basic import (
    AssetService,
    FeverService,
    TTSService,
    LLMService,
    PromptService,
    GroupService,
    StatsService,
)
from .pipeline import (
    FetchResult,
    SummaryResult,
    GroupSummaryResult,
    ScriptResult,
    TTSResult,
    EpisodeResult,
    PipelineResult,
    PipelineStage,
    PipelineOrchestrator,
    GroupProcessor,
    PipelineService,
)
from .scheduler_service import SchedulerService
from .feed_service import FeedService

__all__ = [
    # Base
    'BaseService',
    'ServiceResult',
    'ConfigService',
    # Database Service
    'DatabaseService',
    'get_database_service',
    # Basic Services
    'AssetService',
    'FeverService',
    'TTSService',
    'LLMService',
    'PromptService',
    'GroupService',
    'StatsService',
    # Pipeline Services
    'FetchResult',
    'SummaryResult',
    'GroupSummaryResult',
    'ScriptResult',
    'TTSResult',
    'EpisodeResult',
    'PipelineResult',
    'PipelineStage',
    'PipelineOrchestrator',
    'GroupProcessor',
    'PipelineService',
    # Scheduler Service
    'SchedulerService',
    # Feed Service
    'FeedService',
]
