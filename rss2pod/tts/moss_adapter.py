#!/usr/bin/env python3
"""
MOSS-TTSD 适配器

将结构化播客脚本转换为 MOSS-TTSD 模型所需的输入格式。
MOSS-TTSD 支持双人对话，使用 [S1] 和 [S2] 标签区分说话人。

参考文档：doc/siliconflow/创建文本转语音请求 MOSS 模型 - SiliconFlow.md
"""

import os
import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class MOSSSegment:
    """MOSS 格式段落"""
    speaker: str       # host 或 co_host
    content: str       # 台词内容
    emotion: str = "neutral"  # 情绪：neutral, happy, curious, serious


@dataclass
class MOSSInput:
    """MOSS 模型输入"""
    segments: List[MOSSSegment] = field(default_factory=list)
    
    def to_moss_string(self) -> str:
        """
        转换为 MOSS 格式字符串
        
        Returns:
            MOSS 格式字符串，如：[S1] 你好 [S2] 谢谢
        """
        parts = []
        for seg in self.segments:
            moss_tag = "[S1]" if seg.speaker == "host" else "[S2]"
            parts.append(f"{moss_tag} {seg.content}")
        return " ".join(parts)
    
    @classmethod
    def from_script_segments(cls, segments: List[Dict[str, Any]]) -> "MOSSInput":
        """
        从脚本段落创建 MOSSInput
        
        Args:
            segments: 脚本段落列表，每项包含 speaker, content, emotion
            
        Returns:
            MOSSInput 实例
        """
        moss_segments = []
        for seg in segments:
            moss_segments.append(MOSSSegment(
                speaker=seg.get("speaker", "host"),
                content=seg.get("content", ""),
                emotion=seg.get("emotion", "neutral")
            ))
        return cls(segments=moss_segments)


class MOSSAdapter:
    """
    MOSS-TTSD 适配器
    
    负责：
    - 将结构化脚本转换为 MOSS 格式
    - 管理双人对话的说话人映射
    - 处理情绪和语调标记
    """
    
    # 说话人到 MOSS 标签的映射
    SPEAKER_TO_MOSS_TAG = {
        "host": "[S1]",
        "co_host": "[S2]",
        "guest": "[S2]",  # 嘉宾默认使用 S2
    }
    
    # 情绪到 MOSS 标记的映射（MOSS 支持的情感标记）
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
            host_voice: 主持人音色（默认沉稳男声）
            co_host_voice: 协主持人音色（默认温柔女声）
        """
        self.host_voice = host_voice
        self.co_host_voice = co_host_voice
    
    def convert_script_to_moss(
        self,
        script_segments: List[Dict[str, Any]]
    ) -> str:
        """
        将脚本转换为 MOSS 格式
        
        Args:
            script_segments: 脚本段落列表
            
        Returns:
            MOSS 格式字符串
        """
        moss_input = MOSSInput.from_script_segments(script_segments)
        return moss_input.to_moss_string()
    
    def build_references(self) -> List[Dict[str, str]]:
        """
        构建 MOSS 参考音色列表
        
        Returns:
            参考音色列表，用于 TTS 请求
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
        
        # 添加主持人音色
        if self.host_voice in voice_templates:
            audio, text = voice_templates[self.host_voice]
            references.append({"audio": audio, "text": text})
        
        # 添加协主持人音色
        if self.co_host_voice in voice_templates:
            audio, text = voice_templates[self.co_host_voice]
            references.append({"audio": audio, "text": text})
        
        return references
    
    def add_emotion_marks(self, text: str, emotion: str) -> str:
        """
        为文本添加情绪标记
        
        Args:
            text: 原始文本
            emotion: 情绪类型
            
        Returns:
            带情绪标记的文本
        """
        mark = self.EMOTION_TO_MOSS_MARK.get(emotion, "")
        if mark:
            return f"{mark}{text}{mark}"
        return text
    
    def validate_script(self, script_segments: List[Dict[str, Any]]) -> List[str]:
        """
        验证脚本格式
        
        Args:
            script_segments: 脚本段落列表
            
        Returns:
            错误列表，空列表表示验证通过
        """
        errors = []
        
        # 检查说话人是否有效
        valid_speakers = {"host", "co_host", "guest"}
        for seg in script_segments:
            speaker = seg.get("speaker", "")
            if speaker not in valid_speakers:
                errors.append(f"无效的说话人：{speaker}")
            
            content = seg.get("content", "")
            if not content:
                errors.append("空内容段落")
        
        # 检查是否有至少两个段落
        if len(script_segments) < 2:
            errors.append("脚本段落太少，至少需要 2 段")
        
        return errors
    
    def estimate_duration(
        self,
        script_segments: List[Dict[str, Any]],
        chars_per_second: float = 15.0
    ) -> float:
        """
        估算语音时长（秒）
        
        Args:
            script_segments: 脚本段落列表
            chars_per_second: 每秒字符数（中文约 15 字/秒）
            
        Returns:
            估算时长（秒）
        """
        total_chars = sum(len(seg.get("content", "")) for seg in script_segments)
        return total_chars / chars_per_second


def create_moss_input(
    script_segments: List[Dict[str, Any]],
    host_voice: str = "alex",
    co_host_voice: str = "claire"
) -> Dict[str, Any]:
    """
    便捷函数：创建 MOSS 输入和参考音色
    
    Args:
        script_segments: 脚本段落列表
        host_voice: 主持人音色
        co_host_voice: 协主持人音色
        
    Returns:
        包含 moss_input 和 references 的字典
    """
    adapter = MOSSAdapter(host_voice, co_host_voice)
    
    # 验证脚本
    errors = adapter.validate_script(script_segments)
    if errors:
        return {
            "success": False,
            "errors": errors,
            "moss_input": None,
            "references": None
        }
    
    # 转换为 MOSS 格式
    moss_string = adapter.convert_script_to_moss(script_segments)
    
    # 构建参考音色
    references = adapter.build_references()
    
    return {
        "success": True,
        "moss_input": moss_string,
        "references": references,
        "duration_estimate": adapter.estimate_duration(script_segments)
    }


if __name__ == "__main__":
    # 测试 MOSS 适配器
    print("测试 MOSS 适配器...")
    
    # 测试脚本
    test_script = [
        {"speaker": "host", "content": "欢迎收听今天的播客节目。", "emotion": "happy"},
        {"speaker": "co_host", "content": "大家好，很高兴和你一起聊聊今天的新闻。", "emotion": "happy"},
        {"speaker": "host", "content": "第一条新闻，AI 技术取得新突破。", "emotion": "neutral"},
        {"speaker": "co_host", "content": "真的吗？具体是什么样的突破？", "emotion": "curious"},
    ]
    
    # 创建 MOSS 输入
    result = create_moss_input(test_script)
    
    if result["success"]:
        print(f"\nMOSS 输入:")
        print(result["moss_input"])
        
        print(f"\n参考音色:")
        for ref in result["references"]:
            print(f"  - {ref['audio']}")
        
        print(f"\n估算时长：{result['duration_estimate']:.1f}秒")
    else:
        print(f"\n验证失败:")
        for error in result["errors"]:
            print(f"  - {error}")
    
    print("\nMOSS 适配器测试完成!")