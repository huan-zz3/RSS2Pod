#!/usr/bin/env python3
"""
LLM 脚本生成器实现

使用 LLM 生成播客脚本，支持：
- 单人播报
- 双人对话
- 英语学习模式（词汇解释、翻译）
- MOSS 格式输出
"""

import os
import sys
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from script.script_engine import ScriptEngine, PodcastScript, ScriptSegment, Speaker
from llm.llm_client import LLMClient, create_llm_client


@dataclass
class ScriptOutput:
    """播客脚本输出"""
    title: str
    episode_number: int
    group_id: str
    segments: List[Dict[str, Any]] = field(default_factory=list)
    total_duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "episode_number": self.episode_number,
            "group_id": self.group_id,
            "segments": self.segments,
            "total_duration": self.total_duration,
            "metadata": self.metadata
        }
    
    def to_moss_format(self) -> str:
        """转换为 MOSS 格式"""
        moss_parts = []
        for seg in self.segments:
            speaker = seg.get('speaker', 'host')
            content = seg.get('content', '')
            
            # 转换为 [S1] 或 [S2] 标签
            moss_tag = '[S1]' if speaker == 'host' else '[S2]'
            moss_parts.append(f"{moss_tag}{content}")
        
        return ''.join(moss_parts)


class LLMScriptEngine(ScriptEngine):
    """
    LLM 脚本生成引擎
    
    使用 LLM 生成结构化的播客脚本
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化脚本引擎
        
        Args:
            llm_client: LLM 客户端
        """
        self.llm_client = llm_client or create_llm_client("dashscope")
        self.base_engine = BaseScriptEngine()
    
    def generate_script(
        self,
        group_summary: Dict[str, Any],
        group_config: Dict[str, Any],
        episode_number: int = 1
    ) -> ScriptOutput:
        """
        生成播客脚本
        
        Args:
            group_summary: 组级摘要
            group_config: Group 配置
            episode_number: 期数
            
        Returns:
            ScriptOutput 实例
        """
        # 构建 Prompt
        prompt = self._build_prompt(group_summary, group_config)
        
        # 生成 JSON 脚本
        script_json = self.llm_client.generate_json(prompt)
        
        # 解析并返回
        return self._parse_script(script_json, group_config, episode_number)
    
    def _build_prompt(
        self,
        group_summary: Dict[str, Any],
        group_config: Dict[str, Any]
    ) -> str:
        """
        构建脚本生成 Prompt
        
        Args:
            group_summary: 组级摘要
            group_config: Group 配置
            
        Returns:
            Prompt 字符串
        """
        executive_summary = group_summary.get('executive_summary', '')
        full_summary = group_summary.get('full_summary', '')
        highlights = group_summary.get('top_highlights', [])
        sources_breakdown = group_summary.get('sources_breakdown', [])
        
        # 配置参数
        podcast_structure = group_config.get('podcast_structure', 'single')
        english_learning = group_config.get('english_learning_mode', 'off')
        group_name = group_config.get('name', '播客节目')
        
        speaker_count = 2 if podcast_structure == 'dual' else 1
        
        # 构建 highlights 文本
        highlights_text = ''
        if highlights:
            highlights_text = '\n'.join([f"- {h}" for h in highlights])
        
        # 构建源信息文本
        sources_text = ''
        if sources_breakdown:
            sources_text = '\n'.join([
                f"- {s.get('name', '未知源')}: {s.get('article_count', 0)} 篇文章"
                for s in sources_breakdown
            ])
        
        prompt = f"""你是专业的播客脚本撰写人。请根据以下内容生成一期播客脚本。

## 节目信息
节目名称：{group_name}
结构：{"双人对话" if speaker_count == 2 else "单人播报"}
英语学习：{english_learning}

## 执行摘要
{executive_summary}

## 详细内容
{full_summary}

## 亮点
{highlights_text if highlights_text else '无特定亮点'}

## 来源
{sources_text if sources_text else '无来源信息'}

## 要求
1. 生成自然流畅的播客脚本
2. {"区分主持人 (host) 和协主持人 (co_host) 的对话，交替发言" if speaker_count == 2 else "使用单人播报风格"}
3. 包含以下部分：
   - intro: 开场白（欢迎听众，介绍本期主题）
   - content: 主要内容（详细讨论新闻和话题）
   - summary: 总结（回顾要点）
   - outro: 结束语（感谢听众，预告下期）
4. {"在适当位置插入英语单词解释和翻译" if english_learning != 'off' else "不需要英语学习内容"}
5. 每个段落标注 speaker（host 或 co_host）和 emotion（neutral/happy/curious/serious）

## 输出格式
请以 JSON 格式返回，严格遵循以下结构：
{{
    "title": "节目标题（英文或中文）",
    "segments": [
        {{
            "type": "intro",
            "speaker": "host",
            "emotion": "happy",
            "content": "开场白内容..."
        }},
        {{
            "type": "content",
            "speaker": "host",
            "emotion": "neutral",
            "content": "主要内容..."
        }},
        {{
            "type": "content",
            "speaker": "co_host",
            "emotion": "curious",
            "content": "协主持人回应..."
        }},
        {{
            "type": "summary",
            "speaker": "host",
            "emotion": "neutral",
            "content": "总结内容..."
        }},
        {{
            "type": "outro",
            "speaker": "host",
            "emotion": "happy",
            "content": "结束语..."
        }}
    ]
}}

注意：
- 内容要自然流畅，像真实对话
- 避免机械式的朗读
- 适当加入过渡词和连接语
- {"双人对话要有互动感，协主持人可以适当提问或发表观点" if speaker_count == 2 else ""}
"""
        return prompt
    
    def _parse_script(
        self,
        script_json: Dict[str, Any],
        group_config: Dict[str, Any],
        episode_number: int
    ) -> ScriptOutput:
        """
        解析 LLM 返回的脚本 JSON
        
        Args:
            script_json: 脚本 JSON
            group_config: Group 配置
            episode_number: 期数
            
        Returns:
            ScriptOutput 实例
        """
        segments = script_json.get('segments', [])
        title = script_json.get('title', f"{group_config.get('name', '播客')} Episode {episode_number}")
        
        # 估算总时长
        total_duration = 0.0
        for seg in segments:
            content = seg.get('content', '')
            duration = self.base_engine.estimate_duration(content)
            seg['duration'] = duration
            total_duration += duration
        
        return ScriptOutput(
            title=title,
            episode_number=episode_number,
            group_id=group_config.get('id', ''),
            segments=segments,
            total_duration=total_duration,
            metadata={
                'podcast_structure': group_config.get('podcast_structure', 'single'),
                'english_learning': group_config.get('english_learning_mode', 'off'),
                'generated_at': datetime.now().isoformat()
            }
        )
    
    def convert_to_moss_format(self, script: ScriptOutput) -> str:
        """
        将脚本转换为 MOSS 格式
        
        Args:
            script: ScriptOutput 实例
            
        Returns:
            MOSS 格式字符串
        """
        return script.to_moss_format()
    
    def add_english_learning(
        self,
        segments: List[Dict[str, Any]],
        mode: str = 'vocab'
    ) -> List[Dict[str, Any]]:
        """
        为脚本添加英语学习内容
        
        Args:
            segments: 原始脚本段落
            mode: 模式（vocab=词汇解释，translation=翻译）
            
        Returns:
            添加英语学习内容后的段落
        """
        enhanced_segments = []
        
        for seg in segments:
            enhanced_segments.append(seg)
            
            if mode == 'vocab':
                # 提取可能的生词并添加解释
                content = seg.get('content', '')
                vocab_notes = self._extract_vocabulary_notes(content)
                if vocab_notes:
                    enhanced_segments.append({
                        'type': 'vocab_note',
                        'speaker': seg.get('speaker', 'host'),
                        'emotion': 'neutral',
                        'content': f"[词汇解释] {vocab_notes}"
                    })
            
            elif mode == 'translation':
                # 添加翻译
                content = seg.get('content', '')
                translation = self._translate_content(content)
                if translation:
                    enhanced_segments.append({
                        'type': 'translation',
                        'speaker': seg.get('speaker', 'host'),
                        'emotion': 'neutral',
                        'content': f"[翻译] {translation}"
                    })
        
        return enhanced_segments
    
    def _extract_vocabulary_notes(self, content: str) -> str:
        """提取词汇解释"""
        # 简单实现：使用 LLM 提取生词
        prompt = f"""从以下英文内容中提取可能对中国学习者来说较难的单词，并提供中文解释。
只提取 3-5 个最重要的单词。

内容：{content[:500]}

返回格式：单词 1（解释）；单词 2（解释）；...
"""
        try:
            result = self.llm_client.generate(prompt)
            return result.strip()
        except Exception:
            return ""
    
    def _translate_content(self, content: str) -> str:
        """翻译内容"""
        prompt = f"""将以下英文内容翻译成中文，要求自然流畅。

内容：{content[:500]}

翻译："""
        try:
            result = self.llm_client.generate(prompt)
            return result.strip()
        except Exception:
            return ""
    
    # 实现基类抽象方法
    def generate_segment(
        self,
        segment_type: str,
        content: str,
        speakers: List[Speaker]
    ) -> ScriptSegment:
        """生成特定段落"""
        # 简单实现：直接创建段落
        return ScriptSegment(
            segment_type=segment_type,
            speakers=speakers,
            duration_estimate=self.base_engine.estimate_duration(content)
        )


class BaseScriptEngine(ScriptEngine):
    """基础脚本引擎实现"""
    
    # 平均每分钟单词数
    WPM_RATES = {
        "slow": 130,
        "normal": 150,
        "fast": 170
    }
    
    def estimate_duration(self, text: str, speaking_rate: str = "normal") -> float:
        """估算语音时长（秒）"""
        # 中英文混合文本的估算
        # 英文按单词数，中文按字符数（假设每个中文字约等于 1.5 个英文单词）
        import re
        
        # 分离中英文
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_text = re.sub(r'[\u4e00-\u9fff]', '', text)
        english_words = len(english_text.split())
        
        # 转换为等效英文单词数
        equivalent_words = english_words + (chinese_chars * 1.5)
        
        wpm = self.WPM_RATES.get(speaking_rate, 150)
        return (equivalent_words / wpm) * 60
    
    def generate_script(self, content: str, config: Dict[str, Any]) -> PodcastScript:
        """生成脚本（抽象方法实现）"""
        raise NotImplementedError("请使用 LLMScriptEngine")
    
    def generate_segment(self, segment_type: str, content: str, speakers: List[Speaker]) -> ScriptSegment:
        """生成段落（抽象方法实现）"""
        raise NotImplementedError("请使用 LLMScriptEngine")


def generate_podcast_script(
    group_summary: Dict[str, Any],
    group_config: Dict[str, Any],
    episode_number: int = 1,
    llm_provider: str = "dashscope"
) -> ScriptOutput:
    """
    便捷函数：生成播客脚本
    
    Args:
        group_summary: 组级摘要
        group_config: Group 配置
        episode_number: 期数
        llm_provider: LLM 提供商
        
    Returns:
        ScriptOutput 实例
    """
    llm_client = create_llm_client(llm_provider)
    engine = LLMScriptEngine(llm_client)
    return engine.generate_script(group_summary, group_config, episode_number)


if __name__ == '__main__':
    # 测试脚本生成器
    print("测试 LLM 脚本生成器...")
    
    # 测试数据
    test_group_summary = {
        "executive_summary": "今日科技新闻摘要：AI 技术取得新突破，多款新产品发布。",
        "full_summary": "详细内容包含多个科技公司的最新动态...",
        "top_highlights": ["AI 新模型发布", "科技公司财报", "产品发布会"],
        "sources_breakdown": [
            {"name": "TechCrunch", "article_count": 5},
            {"name": "The Verge", "article_count": 3}
        ]
    }
    
    test_group_config = {
        "id": "test-group-1",
        "name": "科技日报",
        "podcast_structure": "dual",
        "english_learning_mode": "off"
    }
    
    # 使用 mock LLM 客户端测试（不实际调用 API）
    from llm.llm_client import MockLLMClient
    
    llm_client = MockLLMClient()
    engine = LLMScriptEngine(llm_client)
    
    # 生成测试脚本
    script = engine.generate_script(test_group_summary, test_group_config, episode_number=1)
    
    print("\n生成结果:")
    print(f"  标题：{script.title}")
    print(f"  期数：{script.episode_number}")
    print(f"  段落数：{len(script.segments)}")
    print(f"  总时长：{script.total_duration:.1f}秒")
    
    # 转换为 MOSS 格式
    moss_input = script.to_moss_format()
    print("\nMOSS 格式预览:")
    print(f"  {moss_input[:200]}...")
    
    print("\n脚本生成器测试完成!")