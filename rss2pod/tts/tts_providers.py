"""
TTS 提供商实现

支持多云服务：Azure, ElevenLabs, Edge TTS, 阿里云
"""

import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import tempfile
import hashlib

from .tts_interface import (
    TTSProvider,
    TTSConfig,
    TTSResponse,
    TTSProviderType,
)


class AzureTTSProvider(TTSProvider):
    """
    Azure Cognitive Services TTS 提供商
    
    支持多种语音和语言，高质量的神经语音合成。
    """

    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self._client = None

    @property
    def provider_type(self) -> TTSProviderType:
        return TTSProviderType.AZURE

    @property
    def provider_name(self) -> str:
        return "Azure TTS"

    def validate_config(self) -> bool:
        """验证 Azure 配置"""
        if not self.config.api_key:
            # 尝试从环境变量获取
            self.config.api_key = os.getenv("AZURE_TTS_KEY")
        if not self.config.region:
            self.config.region = os.getenv("AZURE_TTS_REGION", "eastasia")
        
        return bool(self.config.api_key and self.config.region)

    async def initialize(self) -> bool:
        """初始化 Azure TTS 客户端"""
        if not self.validate_config():
            return False

        try:
            # 使用 azure-cognitiveservices-speech SDK
            import azure.cognitiveservices.speech as speechsdk
            
            speech_config = speechsdk.SpeechConfig(
                subscription=self.config.api_key,
                region=self.config.region
            )
            speech_config.speech_synthesis_voice_name = self.config.voice
            speech_config.set_speech_synthesis_output_format(
                self.config.output_format
            )
            
            self._client = speech_config
            self._initialized = True
            return True
        except ImportError:
            print("Azure TTS SDK not installed. Run: pip install azure-cognitiveservices-speech")
            return False
        except Exception as e:
            print(f"Failed to initialize Azure TTS: {e}")
            return False

    async def synthesize(self, text: str, output_path: Optional[Path] = None) -> TTSResponse:
        """使用 Azure TTS 合成语音"""
        if not self._initialized:
            return TTSResponse(
                success=False,
                error_message="Azure TTS not initialized",
                text_length=len(text)
            )

        try:
            import azure.cognitiveservices.speech as speechsdk
            
            # 创建临时文件或直接合成到内存
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))
            else:
                # 合成到内存
                audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
            
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self._client,
                audio_config=audio_config
            )
            
            # 应用语速、音调、音量设置
            ssml = self._build_ssml(text)
            
            result = synthesizer.speak_ssml_async(ssml).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                duration_ms = int(result.audio_duration.total_seconds() * 1000)
                
                return TTSResponse(
                    success=True,
                    audio_path=output_path,
                    duration_ms=duration_ms,
                    provider=self.provider_name,
                    voice=self.config.voice,
                    text_length=len(text),
                    request_id=result.request_id
                )
            else:
                return TTSResponse(
                    success=False,
                    error_message=f"Azure TTS failed: {result.reason}",
                    text_length=len(text)
                )
                
        except Exception as e:
            return TTSResponse(
                success=False,
                error_message=f"Azure TTS error: {str(e)}",
                text_length=len(text)
            )

    def _build_ssml(self, text: str) -> str:
        """构建 SSML 请求"""
        return f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{self.config.language}">
            <voice name="{self.config.voice}">
                <prosody rate="{self.config.rate}" pitch="{self.config.pitch}" volume="{self.config.volume}">
                    {text}
                </prosody>
            </voice>
        </speak>
        """

    async def list_voices(self) -> List[Dict[str, Any]]:
        """列出 Azure 可用语音"""
        if not self._initialized:
            return []

        try:
            import azure.cognitiveservices.speech as speechsdk
            
            # 创建临时 synthesizer 来获取语音列表
            speech_config = speechsdk.SpeechConfig(
                subscription=self.config.api_key,
                region=self.config.region
            )
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
            
            voices_result = synthesizer.get_voices_async().get()
            
            if voices_result.reason == speechsdk.ResultReason.VoicesListed:
                return [
                    {
                        "name": voice.name,
                        "locale": voice.locale,
                        "gender": str(voice.gender),
                        "voice_type": str(voice.voice_type)
                    }
                    for voice in voices_result.voices
                ]
            return []
        except Exception as e:
            print(f"Failed to list Azure voices: {e}")
            return []

    async def close(self):
        """关闭 Azure 连接"""
        self._client = None
        await super().close()


class ElevenLabsTTSProvider(TTSProvider):
    """
    ElevenLabs TTS 提供商
    
    高质量、情感丰富的 AI 语音合成。
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self._session = None

    @property
    def provider_type(self) -> TTSProviderType:
        return TTSProviderType.ELEVENLABS

    @property
    def provider_name(self) -> str:
        return "ElevenLabs"

    def validate_config(self) -> bool:
        """验证 ElevenLabs 配置"""
        if not self.config.api_key:
            self.config.api_key = os.getenv("ELEVENLABS_API_KEY")
        return bool(self.config.api_key)

    async def initialize(self) -> bool:
        """初始化 ElevenLabs 客户端"""
        if not self.validate_config():
            return False

        try:
            import aiohttp
            self._session = aiohttp.ClientSession(
                headers={
                    "xi-api-key": self.config.api_key,
                    "Content-Type": "application/json"
                }
            )
            self._initialized = True
            return True
        except Exception as e:
            print(f"Failed to initialize ElevenLabs: {e}")
            return False

    async def synthesize(self, text: str, output_path: Optional[Path] = None) -> TTSResponse:
        """使用 ElevenLabs 合成语音"""
        if not self._initialized:
            return TTSResponse(
                success=False,
                error_message="ElevenLabs not initialized",
                text_length=len(text)
            )

        try:
            # ElevenLabs API endpoint
            voice_id = self.config.voice  # Voice ID 而不是名称
            url = f"{self.BASE_URL}/text-to-speech/{voice_id}"
            
            payload = {
                "text": text,
                "model_id": self.config.extra_params.get("model_id", "eleven_monolingual_v1"),
                "voice_settings": {
                    "stability": self.config.extra_params.get("stability", 0.5),
                    "similarity_boost": self.config.extra_params.get("similarity_boost", 0.75),
                    "style": self.config.extra_params.get("style", 0.0),
                    "use_speaker_boost": self.config.extra_params.get("use_speaker_boost", True)
                }
            }

            async with self._session.post(url, json=payload) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    
                    # 保存到文件
                    if output_path:
                        output_path = Path(output_path)
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_bytes(audio_data)
                    
                    # 估算时长（MP3 约 128kbps，16 字节/ms）
                    duration_ms = len(audio_data) * 8 // 128
                    
                    return TTSResponse(
                        success=True,
                        audio_data=audio_data,
                        audio_path=output_path,
                        duration_ms=duration_ms,
                        provider=self.provider_name,
                        voice=self.config.voice,
                        text_length=len(text)
                    )
                else:
                    error_text = await response.text()
                    return TTSResponse(
                        success=False,
                        error_message=f"ElevenLabs API error: {response.status} - {error_text}",
                        text_length=len(text)
                    )
                    
        except Exception as e:
            return TTSResponse(
                success=False,
                error_message=f"ElevenLabs error: {str(e)}",
                text_length=len(text)
            )

    async def list_voices(self) -> List[Dict[str, Any]]:
        """列出 ElevenLabs 可用语音"""
        if not self._initialized:
            return []

        try:
            url = f"{self.BASE_URL}/voices"
            
            async with self._session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return [
                        {
                            "voice_id": voice["voice_id"],
                            "name": voice["name"],
                            "category": voice.get("category", "unknown"),
                            "description": voice.get("description", ""),
                            "preview_url": voice.get("preview_url", "")
                        }
                        for voice in data.get("voices", [])
                    ]
            return []
        except Exception as e:
            print(f"Failed to list ElevenLabs voices: {e}")
            return []

    async def close(self):
        """关闭 ElevenLabs 会话"""
        if self._session:
            await self._session.close()
            self._session = None
        await super().close()


class EdgeTTSProvider(TTSProvider):
    """
    Microsoft Edge TTS 提供商
    
    免费的 TTS 服务，通过 Edge 浏览器接口访问。
    """

    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self._client = None

    @property
    def provider_type(self) -> TTSProviderType:
        return TTSProviderType.EDGE

    @property
    def provider_name(self) -> str:
        return "Edge TTS"

    def validate_config(self) -> bool:
        """Edge TTS 不需要 API 密钥"""
        return True

    async def initialize(self) -> bool:
        """初始化 Edge TTS"""
        try:
            import edge_tts
            self._initialized = True
            return True
        except ImportError:
            print("Edge TTS not installed. Run: pip install edge-tts")
            return False
        except Exception as e:
            print(f"Failed to initialize Edge TTS: {e}")
            return False

    async def synthesize(self, text: str, output_path: Optional[Path] = None) -> TTSResponse:
        """使用 Edge TTS 合成语音"""
        if not self._initialized:
            return TTSResponse(
                success=False,
                error_message="Edge TTS not initialized",
                text_length=len(text)
            )

        try:
            import edge_tts
            
            if not output_path:
                # 创建临时文件
                temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                output_path = Path(temp_file.name)
                temp_file.close()
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 构建 communicate 对象
            communicate = edge_tts.Communicate(
                text,
                self.config.voice,
                rate=f"{int((self.config.rate - 1.0) * 100)}%",
                pitch=f"{int(self.config.pitch * 100)}Hz",
                volume=f"{int(self.config.volume * 100)}%"
            )
            
            # 合成并保存
            await communicate.save(str(output_path))
            
            # 获取音频时长
            duration_ms = await self._get_audio_duration(output_path)
            
            return TTSResponse(
                success=True,
                audio_path=output_path,
                duration_ms=duration_ms,
                provider=self.provider_name,
                voice=self.config.voice,
                text_length=len(text)
            )
            
        except Exception as e:
            return TTSResponse(
                success=False,
                error_message=f"Edge TTS error: {str(e)}",
                text_length=len(text)
            )

    async def _get_audio_duration(self, audio_path: Path) -> int:
        """获取音频文件时长（毫秒）"""
        try:
            import mutagen
            audio = mutagen.File(audio_path)
            if audio:
                return int(audio.info.length * 1000)
        except Exception:
            pass
        return 0  # 未知时长

    async def list_voices(self) -> List[Dict[str, Any]]:
        """列出 Edge TTS 可用语音"""
        try:
            import edge_tts
            
            voices = await edge_tts.list_voices()
            return [
                {
                    "name": voice["ShortName"],
                    "full_name": voice["FriendlyName"],
                    "locale": voice["Locale"],
                    "gender": voice["Gender"],
                }
                for voice in voices
            ]
        except Exception as e:
            print(f"Failed to list Edge TTS voices: {e}")
            return []

    async def close(self):
        """Edge TTS 无需特殊清理"""
        await super().close()


class AliyunTTSProvider(TTSProvider):
    """
    阿里云智能语音交互 TTS 提供商
    
    支持多种中文语音，适合中文内容合成。
    """

    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self._client = None

    @property
    def provider_type(self) -> TTSProviderType:
        return TTSProviderType.ALIYUN

    @property
    def provider_name(self) -> str:
        return "Aliyun TTS"

    def validate_config(self) -> bool:
        """验证阿里云配置"""
        if not self.config.api_key:
            self.config.api_key = os.getenv("ALIYUN_ACCESS_KEY_ID")
        if not self.config.extra_params.get("access_key_secret"):
            self.config.extra_params["access_key_secret"] = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
        if not self.config.extra_params.get("app_key"):
            self.config.extra_params["app_key"] = os.getenv("ALIYUN_TTS_APP_KEY")
        
        return bool(
            self.config.api_key and 
            self.config.extra_params.get("access_key_secret") and
            self.config.extra_params.get("app_key")
        )

    async def initialize(self) -> bool:
        """初始化阿里云 TTS 客户端"""
        if not self.validate_config():
            return False

        try:
            # 使用 nls-python-sdk
            from aliyun_speech import SpeechSynthesizer
            
            self._client = SpeechSynthesizer(
                access_key_id=self.config.api_key,
                access_key_secret=self.config.extra_params["access_key_secret"],
                app_key=self.config.extra_params["app_key"]
            )
            
            self._initialized = True
            return True
        except ImportError:
            print("Aliyun TTS SDK not installed. Run: pip install nls-python-sdk")
            return False
        except Exception as e:
            print(f"Failed to initialize Aliyun TTS: {e}")
            return False

    async def synthesize(self, text: str, output_path: Optional[Path] = None) -> TTSResponse:
        """使用阿里云 TTS 合成语音"""
        if not self._initialized:
            return TTSResponse(
                success=False,
                error_message="Aliyun TTS not initialized",
                text_length=len(text)
            )

        try:
            if not output_path:
                temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                output_path = Path(temp_file.name)
                temp_file.close()
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 设置参数
            self._client.set_voice(self.config.voice)
            self._client.set_volume(self.config.volume * 100)
            self._client.set_speech_rate(self.config.rate)
            self._client.set_pitch_rate(self.config.pitch)
            
            # 合成
            self._client.set_text(text)
            result = self._client.synthesize(str(output_path))
            
            if result.get("status") == "SUCCESS":
                duration_ms = int(result.get("duration", 0))
                
                return TTSResponse(
                    success=True,
                    audio_path=output_path,
                    duration_ms=duration_ms,
                    provider=self.provider_name,
                    voice=self.config.voice,
                    text_length=len(text),
                    request_id=result.get("task_id")
                )
            else:
                return TTSResponse(
                    success=False,
                    error_message=f"Aliyun TTS failed: {result.get('message', 'Unknown error')}",
                    text_length=len(text)
                )
                
        except Exception as e:
            return TTSResponse(
                success=False,
                error_message=f"Aliyun TTS error: {str(e)}",
                text_length=len(text)
            )

    async def list_voices(self) -> List[Dict[str, Any]]:
        """列出阿里云可用语音"""
        # 阿里云语音列表需要查询文档或 API
        # 这里返回常见的中文语音
        return [
            {"name": "xiaoyun", "description": "女声，标准普通话"},
            {"name": "xiaogang", "description": "男声，标准普通话"},
            {"name": "aili", "description": "女声，温柔"},
            {"name": "sijing", "description": "女声，新闻播报"},
            {"name": "aitong", "description": "男声，儿童故事"},
        ]

    async def close(self):
        """关闭阿里云连接"""
        self._client = None
        await super().close()


# 提供商工厂函数
def get_provider(provider_type: TTSProviderType, config: TTSConfig) -> Optional[TTSProvider]:
    """
    获取 TTS 提供商实例
    
    Args:
        provider_type: 提供商类型
        config: TTS 配置
        
    Returns:
        TTSProvider 实例或 None
    """
    providers = {
        TTSProviderType.AZURE: AzureTTSProvider,
        TTSProviderType.ELEVENLABS: ElevenLabsTTSProvider,
        TTSProviderType.EDGE: EdgeTTSProvider,
        TTSProviderType.ALIYUN: AliyunTTSProvider,
        TTSProviderType.SILICONFLOW: SiliconFlowTTSProvider,
    }
    
    provider_class = providers.get(provider_type)
    if provider_class:
        return provider_class(config)
    return None


def list_available_providers() -> List[str]:
    """列出所有可用的提供商类型"""
    return [
        TTSProviderType.AZURE.value,
        TTSProviderType.ELEVENLABS.value,
        TTSProviderType.EDGE.value,
        TTSProviderType.ALIYUN.value,
        TTSProviderType.SILICONFLOW.value,
    ]


class SiliconFlowTTSProvider(TTSProvider):
    """
    SiliconFlow TTS 提供商
    
    支持 FunAudioLLM/CosyVoice2-0.5B 和 fnlp/MOSS-TTSD-v0.5 模型
    文档：https://docs.siliconflow.cn/api-reference/audio/create-speech
    """

    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self._client = None
        self._api_key = None
        self._base_url = config.extra_params.get("base_url", "https://api.siliconflow.cn/v1")
        self._model = config.extra_params.get("model", "FunAudioLLM/CosyVoice2-0.5B")

    @property
    def provider_type(self) -> TTSProviderType:
        return TTSProviderType.SILICONFLOW

    @property
    def provider_name(self) -> str:
        return "SiliconFlow TTS"

    def validate_config(self) -> bool:
        """验证 SiliconFlow 配置"""
        if not self.config.api_key:
            self._api_key = os.getenv("SILICONFLOW_API_KEY")
        else:
            self._api_key = self.config.api_key
        
        return bool(self._api_key)

    async def initialize(self) -> bool:
        """初始化 SiliconFlow 客户端"""
        if not self.validate_config():
            return False

        try:
            # 使用 OpenAI 兼容客户端
            from openai import OpenAI
            
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url
            )
            self._initialized = True
            return True
        except ImportError:
            print("OpenAI SDK not installed. Run: pip install openai")
            return False
        except Exception as e:
            print(f"Failed to initialize SiliconFlow TTS: {e}")
            return False

    async def synthesize(self, text: str, output_path: Optional[Path] = None) -> TTSResponse:
        """使用 SiliconFlow TTS 合成语音"""
        if not self._initialized:
            return TTSResponse(
                success=False,
                error_message="SiliconFlow TTS not initialized",
                text_length=len(text)
            )

        try:
            from pathlib import Path as PathLib
            
            # 准备输出路径
            temp_file = None
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                # 创建临时文件
                temp_fd, temp_path = tempfile.mkstemp(suffix=".mp3")
                os.close(temp_fd)
                temp_file = PathLib(temp_path)
                output_path = temp_file

            # 调用 SiliconFlow API
            speech_file_path = PathLib(output_path)
            
            with self._client.audio.speech.with_streaming_response.create(
                model=self._model,
                voice=self.config.voice,
                input=text,
                response_format="mp3",
                speed=self.config.rate
            ) as response:
                response.stream_to_file(speech_file_path)

            # 读取音频数据
            audio_data = speech_file_path.read_bytes()
            
            # 获取时长（估算）
            duration_ms = None
            try:
                import mutagen
                audio = mutagen.File(str(speech_file_path))
                if audio:
                    duration_ms = int(audio.info.length * 1000)
            except:
                pass

            return TTSResponse(
                success=True,
                audio_data=audio_data,
                audio_path=speech_file_path,
                duration_ms=duration_ms,
                provider=self.provider_name,
                voice=self.config.voice,
                text_length=len(text)
            )

        except Exception as e:
            return TTSResponse(
                success=False,
                error_message=f"SiliconFlow TTS synthesis failed: {e}",
                text_length=len(text),
                provider=self.provider_name
            )

    async def list_voices(self) -> List[Dict[str, Any]]:
        """列出 SiliconFlow 可用语音"""
        return [
            # 系统预置音色 - 男生
            {"name": "FunAudioLLM/CosyVoice2-0.5B:alex", "description": "沉稳男声"},
            {"name": "FunAudioLLM/CosyVoice2-0.5B:benjamin", "description": "低沉男声"},
            {"name": "FunAudioLLM/CosyVoice2-0.5B:charles", "description": "磁性男声"},
            {"name": "FunAudioLLM/CosyVoice2-0.5B:david", "description": "欢快男声"},
            # 系统预置音色 - 女生
            {"name": "FunAudioLLM/CosyVoice2-0.5B:anna", "description": "沉稳女声"},
            {"name": "FunAudioLLM/CosyVoice2-0.5B:bella", "description": "激情女声"},
            {"name": "FunAudioLLM/CosyVoice2-0.5B:claire", "description": "温柔女声"},
            {"name": "FunAudioLLM/CosyVoice2-0.5B:diana", "description": "欢快女声"},
            # MOSS 模型
            {"name": "fnlp/MOSS-TTSD-v0.5", "description": "高表现力语音，支持双人对话"},
        ]

    async def close(self):
        """关闭连接"""
        self._client = None
        await super().close()
