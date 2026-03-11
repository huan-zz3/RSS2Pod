"""
Pipeline 数据模型

定义管道处理过程中使用的数据类。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class FetchResult:
    """获取文章结果"""
    success: bool
    articles: List[Any] = field(default_factory=list)
    error_message: Optional[str] = None
    fetch_cursor: Optional[str] = None  # since_id for incremental fetch


@dataclass
class SummaryResult:
    """源级摘要结果"""
    success: bool
    summaries: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class GroupSummaryResult:
    """组级摘要结果"""
    success: bool
    summary: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class ScriptResult:
    """脚本生成结果"""
    success: bool
    script: Optional[Dict[str, Any]] = None
    moss_input: Optional[str] = None  # TTS 格式输入
    error_message: Optional[str] = None


@dataclass
class TTSResult:
    """TTS 合成结果"""
    success: bool
    audio_path: Optional[str] = None
    audio_duration: int = 0  # 秒
    error_message: Optional[str] = None
    failed_segments: List[int] = field(default_factory=list)  # 失败段落索引


@dataclass
class EpisodeResult:
    """Episode 保存结果"""
    success: bool
    episode_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class PipelineResult:
    """管道运行总结果"""
    success: bool
    group_id: str
    episode_id: Optional[str] = None
    failed_stage: Optional[str] = None
    error_message: Optional[str] = None
    stages_completed: List[str] = field(default_factory=list)
    articles_fetched: int = 0
    audio_path: Optional[str] = None
    audio_duration: int = 0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PipelineStage:
    """管道阶段定义"""
    name: str
    func: str  # 方法名
    retryable: bool = True
    critical: bool = True  # 是否关键阶段（失败则整体失败）


# 管道阶段定义
PIPELINE_STAGES = [
    PipelineStage("fetch", "_fetch_articles"),
    PipelineStage("summarize", "_generate_source_summaries"),
    PipelineStage("aggregate", "_generate_group_summary"),
    PipelineStage("script", "_generate_script"),
    PipelineStage("tts", "_synthesize_audio"),
    PipelineStage("save", "_save_episode"),
]
