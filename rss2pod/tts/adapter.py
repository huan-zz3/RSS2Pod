#!/usr/bin/env python3
"""
TTS 适配器抽象接口

定义 TTS 适配器的标准接口，支持多模型（如 MOSS、CosyVoice）的插件化扩展。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ReferenceVoice:
    """参考音色"""
    audio: str  # 音频 URL 或 base64
    text: str   # 音频内容文本


class TTSAdapter(ABC):
    """
    TTS 适配器抽象基类
    
    所有 TTS 模型适配器必须实现此接口，以确保统一调用方式。
    """
    
    @abstractmethod
    def convert_to_tts_input(self, segments: List[Dict[str, Any]]) -> str:
        """
        将脚本段落转换为 TTS 输入格式
        
        Args:
            segments: 脚本段落列表，每项包含 speaker, content, emotion
            
        Returns:
            TTS 模型所需的输入格式字符串
        """
        pass
    
    @abstractmethod
    def build_references(self) -> List[ReferenceVoice]:
        """
        构建参考音色列表
        
        Returns:
            参考音色列表，用于 TTS 请求
        """
        pass
    
    @abstractmethod
    def estimate_duration(
        self,
        segments: List[Dict[str, Any]],
        chars_per_second: float = 15.0
    ) -> float:
        """
        估算音频时长
        
        Args:
            segments: 脚本段落列表
            chars_per_second: 每秒字符数
            
        Returns:
            估算时长（秒）
        """
        pass
    
    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """返回适配器名称"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """返回支持的模型列表"""
        pass


class MOSSAdapter(TTSAdapter):
    """
    MOSS-TTSD 模型适配器
    
    支持双人对话，使用 [S1] 和 [S2] 标签区分说话人。
    """
    
    # 说话人到 MOSS 标签的映射
    SPEAKER_TO_MOSS_TAG = {
        "host": "[S1]",
        "co_host": "[S2]",
        "guest": "[S2]",
    }
    
    # 情绪到 MOSS 标记的映射
    EMOTION_TO_MOSS_MARK = {
        "neutral": "",
        "happy": "[laughter]",
        "curious": "",
        "serious": "",
        "excited": "[laughter]",
        "sad": "[breath]",
    }
    
    def __init__(
        self,
        host_voice: str = "alex",
        co_host_voice: str = "claire"
    ):
        """
        初始化适配器
        
        Args:
            host_voice: 主持人音色
            co_host_voice: 协主持人音色
        """
        self.host_voice = host_voice
        self.co_host_voice = co_host_voice
    
    def convert_to_tts_input(self, segments: List[Dict[str, Any]]) -> str:
        """
        将脚本段落转换为 MOSS 格式
        
        Args:
            segments: 脚本段落列表
            
        Returns:
            MOSS 格式字符串，如：[S1] 你好 [S2] 谢谢
        """
        parts = []
        for seg in segments:
            speaker = seg.get("speaker", "host")
            content = seg.get("content", "")
            emotion = seg.get("emotion", "neutral")
            
            # 添加情绪标记
            if emotion in self.EMOTION_TO_MOSS_MARK:
                mark = self.EMOTION_TO_MOSS_MARK[emotion]
                if mark:
                    content = f"{mark}{content}{mark}"
            
            # 转换为 MOSS 标签
            moss_tag = self.SPEAKER_TO_MOSS_TAG.get(speaker, "[S1]")
            parts.append(f"{moss_tag}{content}")
        
        return ''.join(parts)
    
    def build_references(self) -> List[ReferenceVoice]:
        """
        构建 MOSS 参考音色列表
        
        Returns:
            ReferenceVoice 列表
        """
        # 参考音频 URL（SiliconFlow 提供的示例）
        voice_templates = {
            "alex": (
                "https://sf-maas-uat-prod.oss-cn-shanghai.aliyuncs.com/voice_template/fish_audio-Alex.mp3",
                "沉稳男声参考文本"
            ),
            "anna": (
                "https://sf-maas-uat-prod.oss-cn-shanghai.aliyuncs.com/voice_template/fish_audio-Anna.mp3",
                "沉稳女声参考文本"
            ),
            "bella": (
                "https://sf-maas-uat-prod.oss-cn-shanghai.aliyuncs.com/voice_template/fish_audio-Bella.mp3",
                "激情女声参考文本"
            ),
            "benjamin": (
                "https://sf-maas-uat-prod.oss-cn-shanghai.aliyuncs.com/voice_template/fish_audio-Benjamin.mp3",
                "低沉男声参考文本"
            ),
            "charles": (
                "https://sf-maas-uat-prod.oss-cn-shanghai.aliyuncs.com/voice_template/fish_audio-Charles.mp3",
                "磁性男声参考文本"
            ),
            "claire": (
                "https://sf-maas-uat-prod.oss-cn-shanghai.aliyuncs.com/voice_template/fish_audio-Claire.mp3",
                "温柔女声参考文本"
            ),
            "david": (
                "https://sf-maas-uat-prod.oss-cn-shanghai.aliyuncs.com/voice_template/fish_audio-David.mp3",
                "欢快男声参考文本"
            ),
            "diana": (
                "https://sf-maas-uat-prod.oss-cn-shanghai.aliyuncs.com/voice_template/fish_audio-Diana.mp3",
                "欢快女声参考文本"
            ),
        }
        
        references = []
        
        # 主持人音色
        if self.host_voice in voice_templates:
            audio, text = voice_templates[self.host_voice]
            references.append(ReferenceVoice(audio=audio, text=text))
        
        # 协主持人音色
        if self.co_host_voice in voice_templates:
            audio, text = voice_templates[self.co_host_voice]
            references.append(ReferenceVoice(audio=audio, text=text))
        
        return references
    
    def estimate_duration(
        self,
        segments: List[Dict[str, Any]],
        chars_per_second: float = 15.0
    ) -> float:
        """估算音频时长"""
        total_chars = sum(len(seg.get("content", "")) for seg in segments)
        return total_chars / chars_per_second
    
    @property
    def adapter_name(self) -> str:
        return "MOSS-TTSD"
    
    @property
    def supported_models(self) -> List[str]:
        return ["fnlp/MOSS-TTSD-v0.5"]


class CosyVoiceAdapter(TTSAdapter):
    """
    CosyVoice 模型适配器
    
    单人语音合成，使用音色标识符。
    """
    
    def __init__(self, voice: str = "claire"):
        """
        初始化适配器
        
        Args:
            voice: 音色标识符
        """
        self.voice = voice
    
    def convert_to_tts_input(self, segments: List[Dict[str, Any]]) -> str:
        """
        将脚本段落转换为 CosyVoice 格式
        
        CosyVoice 只支持单人模式，会将所有内容合并。
        
        Args:
            segments: 脚本段落列表
            
        Returns:
            合并后的文本
        """
        # 合并所有内容为一个文本
        contents = []
        for seg in segments:
            content = seg.get("content", "")
            if content:
                contents.append(content)
        
        return " ".join(contents)
    
    def build_references(self) -> List[ReferenceVoice]:
        """
        CosyVoice 使用 voice 参数，不需要 references
        
        Returns:
            空列表
        """
        return []
    
    def estimate_duration(
        self,
        segments: List[Dict[str, Any]],
        chars_per_second: float = 15.0
    ) -> float:
        """估算音频时长"""
        total_chars = sum(len(seg.get("content", "")) for seg in segments)
        return total_chars / chars_per_second
    
    @property
    def adapter_name(self) -> str:
        return "CosyVoice"
    
    @property
    def supported_models(self) -> List[str]:
        return ["FunAudioLLM/CosyVoice2-0.5B"]


# 适配器注册表
_ADAPTERS: Dict[str, TTSAdapter] = {}


def register_adapter(name: str, adapter: TTSAdapter):
    """
    注册 TTS 适配器
    
    Args:
        name: 适配器名称
        adapter: 适配器实例
    """
    _ADAPTERS[name] = adapter


def get_adapter(name: str) -> Optional[TTSAdapter]:
    """
    获取 TTS 适配器
    
    Args:
        name: 适配器名称
        
    Returns:
        适配器实例或 None
    """
    return _ADAPTERS.get(name)


def list_adapters() -> List[str]:
    """
    列出所有已注册的适配器
    
    Returns:
        适配器名称列表
    """
    return list(_ADAPTERS.keys())


# 注册默认适配器
def _register_default_adapters():
    """注册默认适配器"""
    register_adapter("moss", MOSSAdapter())
    register_adapter("cosyvoice", CosyVoiceAdapter())


_register_default_adapters()


def create_adapter_from_config(
    provider_config: Dict[str, Any],
    adapter_name: str
) -> TTSAdapter:
    """
    从配置创建 TTS 适配器
    
    Args:
        provider_config: provider 配置，包含 adapters
        adapter_name: 适配器名称 (如 "moss", "cosyvoice")
        
    Returns:
        TTSAdapter 实例
    """
    adapters_config = provider_config.get('adapters', {})
    adapter_config = adapters_config.get(adapter_name, {})
    
    if adapter_name == "moss":
        return MOSSAdapter(
            host_voice=adapter_config.get('voice_host', 'alex'),
            co_host_voice=adapter_config.get('voice_co_host', 'claire')
        )
    elif adapter_name == "cosyvoice":
        return CosyVoiceAdapter(
            voice=adapter_config.get('voice', 'claire')
        )
    else:
        # 默认返回 MOSS 适配器
        return MOSSAdapter()


def get_adapter_from_tts_config(tts_config: Dict[str, Any]) -> TTSAdapter:
    """
    从 tts 配置创建适配器
    
    Args:
        tts_config: tts 配置，包含 active_provider, active_adapter, providers
        
    Returns:
        TTSAdapter 实例
    """
    active_provider = tts_config.get('active_provider', 'siliconflow')
    active_adapter = tts_config.get('active_adapter', 'moss')
    providers = tts_config.get('providers', {})
    
    provider_config = providers.get(active_provider, {})
    
    return create_adapter_from_config(provider_config, active_adapter)
