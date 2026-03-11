"""
TTS 与音频处理模块

提供统一的 TTS 接口抽象、多云服务支持、音频拼接与管理功能。
"""

from .tts_interface import TTSEngine, TTSProvider, TTSConfig, TTSResponse
from .tts_providers import (
    AzureTTSProvider,
    ElevenLabsTTSProvider,
    EdgeTTSProvider,
    AliyunTTSProvider,
    get_provider,
    list_available_providers,
)
from .audio_assembler import AudioAssembler, AudioSegment
from .audio_manager import AudioManager, AudioCleanupPolicy
from .adapter import (
    TTSAdapter,
    MOSSAdapter,
    CosyVoiceAdapter,
    ReferenceVoice,
    get_adapter,
    register_adapter,
    list_adapters,
)

__all__ = [
    # Interface
    "TTSEngine",
    "TTSProvider",
    "TTSConfig",
    "TTSResponse",
    # Providers
    "AzureTTSProvider",
    "ElevenLabsTTSProvider",
    "EdgeTTSProvider",
    "AliyunTTSProvider",
    "get_provider",
    "list_available_providers",
    # Audio Assembly
    "AudioAssembler",
    "AudioSegment",
    # Audio Management
    "AudioManager",
    "AudioCleanupPolicy",
    # TTS Adapters
    "TTSAdapter",
    "MOSSAdapter",
    "CosyVoiceAdapter",
    "ReferenceVoice",
    "get_adapter",
    "register_adapter",
    "list_adapters",
]
