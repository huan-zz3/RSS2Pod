#!/usr/bin/env python3
"""
SiliconFlow TTS 提供商实现

支持模型：
- fnlp/MOSS-TTSD-v0.5 (双人对话)
- FunAudioLLM/CosyVoice2-0.5B (单人语音)

参考文档：doc/siliconflow/文本转语音模型.md
"""

import os
import sys
import asyncio
from typing import Optional, List, Dict
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import aiohttp
except ImportError:
    aiohttp = None
    print("警告：aiohttp 未安装，请运行：pip install aiohttp")


@dataclass
class ReferenceVoice:
    """参考音色"""
    audio: str  # 音频 URL 或 base64
    text: str   # 音频内容文本


@dataclass
class TTSRequest:
    """TTS 请求数据结构"""
    model: str = "fnlp/MOSS-TTSD-v0.5"
    input: str = ""                    # 带 [S1][S2] 标签的文本（MOSS）或普通文本（CosyVoice）
    voice: Optional[str] = None        # 单音色（CosyVoice 使用）
    references: List[ReferenceVoice] = field(default_factory=list)  # 参考音色（MOSS 双人对话）
    response_format: str = "mp3"
    sample_rate: int = 32000
    stream: bool = False
    speed: float = 1.0
    gain: float = 0.0
    max_tokens: int = 2048


@dataclass
class TTSResponse:
    """TTS 响应"""
    success: bool
    audio_data: Optional[bytes] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    request_id: Optional[str] = None


class SiliconFlowClient:
    """
    SiliconFlow TTS API 客户端
    
    支持：
    - MOSS-TTSD-v0.5：双人对话模型
    - CosyVoice2-0.5B：单人语音模型
    """
    
    # 可用音色列表
    AVAILABLE_VOICES = [
        ("alex", "沉稳男声"),
        ("benjamin", "低沉男声"),
        ("charles", "磁性男声"),
        ("david", "欢快男声"),
        ("anna", "沉稳女声"),
        ("bella", "激情女声"),
        ("claire", "温柔女声"),
        ("diana", "欢快女声"),
    ]
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.siliconflow.cn/v1",
        model: str = "fnlp/MOSS-TTSD-v0.5"
    ):
        """
        初始化客户端
        
        Args:
            api_key: API Key
            base_url: API 基础 URL
            model: 默认模型
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 HTTP 会话"""
        if self.session is None or self.session.closed:
            if aiohttp is None:
                raise ImportError("aiohttp 未安装")
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def synthesize(self, input_text: str, **kwargs) -> bytes:
        """
        合成音频
        
        Args:
            input_text: 输入文本
            **kwargs: 额外参数
            
        Returns:
            音频数据（二进制）
        """
        request = TTSRequest(
            model=kwargs.get('model', self.model),
            input=input_text,
            voice=kwargs.get('voice'),
            references=kwargs.get('references', []),
            response_format=kwargs.get('response_format', 'mp3'),
            sample_rate=kwargs.get('sample_rate', 32000),
            stream=kwargs.get('stream', False),
            speed=kwargs.get('speed', 1.0),
            gain=kwargs.get('gain', 0.0),
            max_tokens=kwargs.get('max_tokens', 2048)
        )
        
        response = await self._send_request(request)
        
        if not response.success:
            raise Exception(f"TTS 合成失败：{response.error_message}")
        
        return response.audio_data
    
    async def _send_request(self, request: TTSRequest) -> TTSResponse:
        """
        发送 TTS 请求
        
        Args:
            request: TTS 请求
            
        Returns:
            TTS 响应
        """
        session = await self._get_session()
        
        # 构建请求体
        body = {
            "model": request.model,
            "input": request.input,
            "response_format": request.response_format,
            "sample_rate": request.sample_rate,
            "stream": request.stream,
            "speed": request.speed,
            "gain": request.gain,
            "max_tokens": request.max_tokens
        }
        
        # 添加 voice 或 references
        if request.references:
            # MOSS 双人对话模式
            body["references"] = [
                {"audio": ref.audio, "text": ref.text}
                for ref in request.references
            ]
        elif request.voice:
            # CosyVoice 单人模式
            body["voice"] = request.voice
        
        # 过滤 None 值
        body = {k: v for k, v in body.items() if v is not None}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/audio/speech"
        
        try:
            async with session.post(url, json=body, headers=headers) as resp:
                if resp.status == 200:
                    audio_data = await resp.read()
                    
                    # 尝试从响应头获取 request_id
                    request_id = resp.headers.get('x-siliconcloud-trace-id')
                    
                    return TTSResponse(
                        success=True,
                        audio_data=audio_data,
                        request_id=request_id
                    )
                else:
                    error_text = await resp.text()
                    return TTSResponse(
                        success=False,
                        error_message=f"API 错误 ({resp.status}): {error_text}"
                    )
                    
        except asyncio.CancelledError:
            raise
        except Exception as e:
            return TTSResponse(
                success=False,
                error_message=f"请求失败：{str(e)}"
            )
    
    @classmethod
    def get_available_voices(cls, model: str = "fnlp/MOSS-TTSD-v0.5") -> List[Dict[str, str]]:
        """
        获取可用音色列表
        
        Args:
            model: 模型名称，用于确定音色前缀
            
        Returns:
            音色列表
        """
        # 根据模型确定音色前缀
        if 'CosyVoice' in model:
            prefix = "FunAudioLLM/CosyVoice2-0.5B"
        elif 'MOSS' in model:
            prefix = "fnlp/MOSS-TTSD-v0.5"
        else:
            prefix = "FunAudioLLM/CosyVoice2-0.5B"  # 默认
        
        return [
            {"id": f"{prefix}:{voice_id}", "name": name}
            for voice_id, name in cls.AVAILABLE_VOICES
        ]
    
    @classmethod
    def get_voice_prefix(cls, model: str) -> str:
        """
        获取模型的音色前缀
        
        Args:
            model: 模型名称
            
        Returns:
            音色前缀
        """
        if 'CosyVoice' in model:
            return "FunAudioLLM/CosyVoice2-0.5B"
        elif 'MOSS' in model:
            return "fnlp/MOSS-TTSD-v0.5"
        else:
            return "FunAudioLLM/CosyVoice2-0.5B"  # 默认
    
    @classmethod
    def build_moss_input(cls, segments: List[Dict[str, str]]) -> str:
        """
        构建 MOSS 格式输入
        
        Args:
            segments: 段落列表，每项包含 speaker 和 content
            
        Returns:
            MOSS 格式字符串
        """
        parts = []
        for seg in segments:
            speaker = seg.get('speaker', 'host')
            content = seg.get('content', '')
            
            # 转换为 [S1] 或 [S2] 标签
            moss_tag = '[S1]' if speaker == 'host' else '[S2]'
            parts.append(f"{moss_tag}{content}")
        
        return ''.join(parts)
    
    @classmethod
    def build_references(
        cls,
        host_voice: str = "alex",
        co_host_voice: str = "claire"
    ) -> List[ReferenceVoice]:
        """
        构建参考音色列表
        
        Args:
            host_voice: 主持人音色
            co_host_voice: 协主持人音色
            
        Returns:
            ReferenceVoice 列表
        """
        # 参考音频 URL（使用 SiliconFlow 提供的示例）
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
        if host_voice in voice_templates:
            audio, text = voice_templates[host_voice]
            references.append(ReferenceVoice(audio=audio, text=text))
        
        # 协主持人音色
        if co_host_voice in voice_templates:
            audio, text = voice_templates[co_host_voice]
            references.append(ReferenceVoice(audio=audio, text=text))
        
        return references


async def synthesize_audio(
    text: str,
    api_key: str,
    model: str = "fnlp/MOSS-TTSD-v0.5",
    voice: Optional[str] = None,
    references: Optional[List[ReferenceVoice]] = None,
    output_path: Optional[str] = None
) -> str:
    """
    便捷函数：合成音频并保存到文件
    
    Args:
        text: 输入文本
        api_key: API Key
        model: 模型
        voice: 音色
        references: 参考音色
        output_path: 输出文件路径
        
    Returns:
        输出文件路径
    """
    client = SiliconFlowClient(api_key=api_key, model=model)
    
    try:
        audio_data = await client.synthesize(
            text,
            voice=voice,
            references=references
        )
        
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(audio_data)
            return output_path
        else:
            # 保存到临时文件
            import tempfile
            fd, path = tempfile.mkstemp(suffix='.mp3')
            with os.fdopen(fd, 'wb') as f:
                f.write(audio_data)
            return path
            
    finally:
        await client.close()


if __name__ == '__main__':
    # 测试 SiliconFlow 客户端
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='测试 SiliconFlow TTS')
    parser.add_argument('--api-key', help='API Key')
    parser.add_argument('--text', default='[S1] 你好，欢迎收听。[S2] 谢谢，很高兴和你一起。', help='输入文本')
    parser.add_argument('--output', default='test_output.mp3', help='输出文件')
    parser.add_argument('--model', default='fnlp/MOSS-TTSD-v0.5', help='模型')
    args = parser.parse_args()
    
    # 从配置文件加载 API Key（如果未提供）
    api_key = args.api_key
    if not api_key:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            api_key = config.get('tts', {}).get('api_key', '')
    
    if not api_key:
        print("错误：请提供 API Key (--api-key) 或在 config.json 中配置")
        sys.exit(1)
    
    print(f"使用模型：{args.model}")
    print(f"输入文本：{args.text[:50]}...")
    print(f"输出文件：{args.output}")
    
    async def run_test():
        client = SiliconFlowClient(api_key=api_key, model=args.model)
        
        try:
            # 构建 MOSS 双人对话引用
            references = client.build_references(host_voice="alex", co_host_voice="claire")
            
            print("\n开始合成...")
            audio_data = await client.synthesize(args.text, references=references)
            
            # 保存文件
            with open(args.output, 'wb') as f:
                f.write(audio_data)
            
            print("\n合成完成！")
            print(f"输出文件：{args.output}")
            print(f"文件大小：{os.path.getsize(args.output)} 字节")
            
        except Exception as e:
            print(f"\n合成失败：{e}")
            sys.exit(1)
        finally:
            await client.close()
    
    asyncio.run(run_test())