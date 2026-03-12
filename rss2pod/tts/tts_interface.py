"""
TTS 统一接口抽象

定义 TTS 引擎和提供商的标准接口，支持多云服务插件化。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Union


class TTSProviderType(str, Enum):
    """支持的 TTS 提供商类型"""
    AZURE = "azure"
    ELEVENLABS = "elevenlabs"
    EDGE = "edge"
    ALIYUN = "aliyun"
    SILICONFLOW = "siliconflow"
    CUSTOM = "custom"


@dataclass
class TTSConfig:
    """TTS 配置参数"""
    provider: TTSProviderType = TTSProviderType.AZURE
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: float = 1.0  # 语速 0.5-2.0
    pitch: float = 0.0  # 音调 -1.0 to 1.0
    volume: float = 1.0  # 音量 0.0-1.0
    output_format: str = "audio-24khz-48kbitrate-mono-mp3"
    language: str = "zh-CN"
    api_key: Optional[str] = None
    region: Optional[str] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """验证配置参数"""
        if not 0.5 <= self.rate <= 2.0:
            raise ValueError("rate must be between 0.5 and 2.0")
        if not -1.0 <= self.pitch <= 1.0:
            raise ValueError("pitch must be between -1.0 and 1.0")
        if not 0.0 <= self.volume <= 1.0:
            raise ValueError("volume must be between 0.0 and 1.0")
        return True


@dataclass
class TTSResponse:
    """TTS 合成响应"""
    success: bool
    audio_data: Optional[bytes] = None
    audio_path: Optional[Path] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    provider: Optional[str] = None
    voice: Optional[str] = None
    text_length: int = 0
    request_id: Optional[str] = None

    def save_to_file(self, output_path: Union[str, Path]) -> Path:
        """保存音频到文件"""
        if not self.audio_data:
            raise ValueError("No audio data to save")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.audio_path and self.audio_path.exists():
            # 如果已有文件路径，直接复制
            import shutil
            shutil.copy2(self.audio_path, output_path)
        else:
            # 否则保存音频数据
            output_path.write_bytes(self.audio_data)
        
        return output_path


class TTSProvider(ABC):
    """TTS 提供商抽象基类"""

    def __init__(self, config: TTSConfig):
        self.config = config
        self._initialized = False

    @property
    @abstractmethod
    def provider_type(self) -> TTSProviderType:
        """返回提供商类型"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """返回提供商名称"""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """初始化提供商连接"""
        pass

    @abstractmethod
    async def synthesize(self, text: str, output_path: Optional[Path] = None) -> TTSResponse:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            output_path: 可选的输出文件路径
            
        Returns:
            TTSResponse 包含合成结果
        """
        pass

    @abstractmethod
    async def list_voices(self) -> List[Dict[str, Any]]:
        """列出可用的语音"""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """验证配置是否有效"""
        pass

    async def close(self):
        """关闭连接，清理资源"""
        self._initialized = False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider_type.value}, voice={self.config.voice})"


class TTSEngine:
    """
    TTS 引擎 - 统一管理多个 TTS 提供商
    
    提供统一的接口来调用不同的 TTS 服务，支持自动故障转移和负载均衡。
    """

    def __init__(self, default_provider: Optional[TTSProvider] = None):
        self._providers: Dict[TTSProviderType, TTSProvider] = {}
        self._default_provider = default_provider
        self._initialized = False

    def register_provider(self, provider: TTSProvider) -> None:
        """注册 TTS 提供商"""
        self._providers[provider.provider_type] = provider

    def get_provider(self, provider_type: TTSProviderType) -> Optional[TTSProvider]:
        """获取指定的 TTS 提供商"""
        return self._providers.get(provider_type)

    def set_default_provider(self, provider_type: TTSProviderType) -> bool:
        """设置默认提供商"""
        provider = self._providers.get(provider_type)
        if provider:
            self._default_provider = provider
            return True
        return False

    async def initialize(self) -> bool:
        """初始化所有注册的提供商"""
        success = True
        for provider in self._providers.values():
            try:
                if not await provider.initialize():
                    success = False
            except Exception as e:
                print(f"Failed to initialize {provider.provider_name}: {e}")
                success = False
        self._initialized = success
        return success

    async def synthesize(
        self,
        text: str,
        provider_type: Optional[TTSProviderType] = None,
        output_path: Optional[Path] = None,
        config: Optional[TTSConfig] = None
    ) -> TTSResponse:
        """
        使用指定的或默认的提供商合成语音
        
        Args:
            text: 要合成的文本
            provider_type: 可选的提供商类型，不指定则使用默认
            output_path: 可选的输出文件路径
            config: 可选的配置覆盖
            
        Returns:
            TTSResponse 包含合成结果
        """
        if provider_type:
            provider = self._providers.get(provider_type)
        else:
            provider = self._default_provider

        if not provider:
            return TTSResponse(
                success=False,
                error_message="No TTS provider available",
                text_length=len(text)
            )

        # 如果提供了配置覆盖，临时更新
        original_config = None
        if config:
            original_config = provider.config
            provider.config = config

        try:
            return await provider.synthesize(text, output_path)
        finally:
            if original_config:
                provider.config = original_config

    async def synthesize_with_fallback(
        self,
        text: str,
        provider_order: List[TTSProviderType],
        output_path: Optional[Path] = None
    ) -> Optional[TTSResponse]:
        """
        按顺序尝试多个提供商，直到成功
        
        Args:
            text: 要合成的文本
            provider_order: 提供商尝试顺序
            output_path: 可选的输出文件路径
            
        Returns:
            成功的 TTSResponse 或 None
        """
        for provider_type in provider_order:
            provider = self._providers.get(provider_type)
            if not provider:
                continue

            try:
                response = await provider.synthesize(text, output_path)
                if response.success:
                    return response
            except Exception as e:
                print(f"Provider {provider_type.value} failed: {e}")
                continue

        return None

    async def close(self):
        """关闭所有提供商连接"""
        for provider in self._providers.values():
            await provider.close()
        self._initialized = False

    def list_available_providers(self) -> List[str]:
        """列出已注册的提供商"""
        return [p.provider_name for p in self._providers.values()]
