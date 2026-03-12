#!/usr/bin/env python3
"""
Prompt Templates - Templates for generating podcast scripts.

This module contains prompt templates for different podcast formats:
- Single host narration
- Dual host conversation
- Interview format
- Educational content

These templates are designed to be used with LLM APIs to generate
natural-sounding podcast scripts from source content.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class TemplateType(Enum):
    """Types of podcast script templates."""
    SINGLE_HOST = "single_host"
    DUAL_HOST = "dual_host"
    INTERVIEW = "interview"
    EDUCATIONAL = "educational"
    STORYTELLING = "storytelling"


@dataclass
class PromptTemplate:
    """Represents a prompt template for script generation."""
    name: str
    template_type: TemplateType
    system_prompt: str
    user_prompt_template: str
    output_format: str
    variables: List[str]
    
    def render(self, **kwargs) -> Dict[str, str]:
        """
        Render the template with provided variables.
        
        Args:
            **kwargs: Variables to substitute in the template
            
        Returns:
            Dict with 'system' and 'user' prompts
        """
        user_prompt = self.user_prompt_template
        for key, value in kwargs.items():
            if key in self.variables:
                user_prompt = user_prompt.replace(f"{{{key}}}", str(value))
        
        return {
            "system": self.system_prompt,
            "user": user_prompt
        }


# ============================================================================
# SINGLE HOST NARRATION TEMPLATES
# ============================================================================

SINGLE_HOST_SYSTEM_PROMPT = """You are a professional podcast script writer. 
Your task is to create engaging single-host podcast scripts from provided content.

Style guidelines:
- Write in a conversational, friendly tone
- Use natural speech patterns (contractions, rhetorical questions, etc.)
- Include brief pauses and emphasis markers where appropriate
- Keep sentences relatively short for easy listening
- Add personality and warmth to the narration
- Maintain consistent energy throughout

Output format:
- Return a JSON array of speaker segments
- Each segment should have: "line", "pause_after" (seconds), "emphasis" (optional)
- Total script should match the requested duration when possible"""

SINGLE_HOST_USER_TEMPLATE = """Create a single-host podcast script from the following content:

CONTENT:
{content}

REQUIREMENTS:
- Host name: {host_name}
- Tone: {tone}
- Target duration: {duration_minutes} minutes
- Include: {include_elements}

Please generate the script in JSON format with the following structure:
{{
    "segments": [
        {{"line": "spoken text", "pause_after": 0.5, "emphasis": "word or phrase"}},
        ...
    ]
}}

Make it sound natural and engaging, as if the host is speaking directly to a friend."""

# ============================================================================
# DUAL HOST CONVERSATION TEMPLATES
# ============================================================================

DUAL_HOST_SYSTEM_PROMPT = """You are a professional podcast script writer specializing 
in conversational dual-host formats.

Style guidelines:
- Create natural back-and-forth dialogue between two hosts
- Each host should have a distinct personality and speaking style
- Include interruptions, agreements, and natural conversation flow
- Use host names consistently
- Balance speaking time between hosts (roughly 50/50 unless specified)
- Add conversational elements like "you know", "right?", "exactly!"
- Include brief laughter or reaction markers where appropriate

Output format:
- Return a JSON array of dialogue segments
- Each segment should have: "speaker", "line", "pause_after", "reaction" (optional)"""

DUAL_HOST_USER_TEMPLATE = """Create a dual-host podcast conversation from the following content:

CONTENT:
{content}

REQUIREMENTS:
- Host 1: {host1_name} (personality: {host1_personality})
- Host 2: {host2_name} (personality: {host2_personality})
- Tone: {tone}
- Target duration: {duration_minutes} minutes
- Include: {include_elements}

Please generate the script in JSON format with the following structure:
{{
    "segments": [
        {{"speaker": "host_name", "line": "spoken text", "pause_after": 0.3, "reaction": "laughs"}},
        ...
    ]
}}

Make the conversation feel natural and spontaneous, with good chemistry between hosts."""

# ============================================================================
# EDUCATIONAL CONTENT TEMPLATES
# ============================================================================

EDUCATIONAL_SYSTEM_PROMPT = """You are an educational podcast script writer.
Your task is to create clear, informative, and engaging educational content.

Style guidelines:
- Break down complex topics into digestible segments
- Use examples and analogies to explain difficult concepts
- Include recap and summary sections
- Add clear transitions between topics
- Use emphasis for key points and takeaways
- Include occasional questions to engage listeners
- Maintain an encouraging and supportive tone

Output format:
- Return a JSON array with structured segments
- Each segment should have: "section", "speaker", "content", "key_points" (optional)"""

EDUCATIONAL_USER_TEMPLATE = """Create an educational podcast script from the following content:

CONTENT:
{content}

REQUIREMENTS:
- Format: {format_type} (single_host or dual_host)
{host_info}
- Topic: {topic}
- Target audience: {audience_level}
- Target duration: {duration_minutes} minutes
- Include explanations for: {include_explanations}

Please generate the script in JSON format with the following structure:
{{
    "segments": [
        {{
            "section": "introduction|explanation|example|summary",
            "speaker": "host_name",
            "content": "spoken text",
            "key_points": ["point1", "point2"]
        }},
        ...
    ]
}}

Focus on clarity and comprehension. Make complex ideas accessible."""

# ============================================================================
# INTERVIEW FORMAT TEMPLATES
# ============================================================================

INTERVIEW_SYSTEM_PROMPT = """You are a podcast script writer specializing in interview formats.

Style guidelines:
- Create natural interviewer/interviewee dialogue
- Include thoughtful questions that elicit detailed responses
- Show active listening from the interviewer (follow-ups, clarifications)
- Allow the interviewee to share expertise and stories
- Include brief introductions and context-setting
- Maintain professional yet conversational tone
- Balance question/answer ratio appropriately

Output format:
- Return a JSON array of interview segments
- Each segment should have: "speaker", "type" (question/answer/context), "content" """

INTERVIEW_USER_TEMPLATE = """Create an interview-style podcast script from the following content:

CONTENT/INTERVIEW TOPIC:
{content}

REQUIREMENTS:
- Interviewer: {interviewer_name}
- Interviewee: {interviewee_name}
- Interviewee background: {interviewee_background}
- Tone: {tone}
- Target duration: {duration_minutes} minutes
- Key topics to cover: {key_topics}

Please generate the script in JSON format with the following structure:
{{
    "segments": [
        {{"speaker": "name", "type": "question|answer|context", "content": "spoken text"}},
        ...
    ]
}}

Create a natural flow with good questions and insightful answers."""

# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

class TemplateRegistry:
    """Registry for managing and accessing prompt templates."""
    
    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self._register_default_templates()
    
    def _register_default_templates(self):
        """Register all default templates."""
        
        # Single Host
        self.register(PromptTemplate(
            name="single_host_standard",
            template_type=TemplateType.SINGLE_HOST,
            system_prompt=SINGLE_HOST_SYSTEM_PROMPT,
            user_prompt_template=SINGLE_HOST_USER_TEMPLATE,
            output_format="json",
            variables=["content", "host_name", "tone", "duration_minutes", "include_elements"]
        ))
        
        # Dual Host
        self.register(PromptTemplate(
            name="dual_host_conversation",
            template_type=TemplateType.DUAL_HOST,
            system_prompt=DUAL_HOST_SYSTEM_PROMPT,
            user_prompt_template=DUAL_HOST_USER_TEMPLATE,
            output_format="json",
            variables=["content", "host1_name", "host1_personality", "host2_name", 
                      "host2_personality", "tone", "duration_minutes", "include_elements"]
        ))
        
        # Educational
        self.register(PromptTemplate(
            name="educational_standard",
            template_type=TemplateType.EDUCATIONAL,
            system_prompt=EDUCATIONAL_SYSTEM_PROMPT,
            user_prompt_template=EDUCATIONAL_USER_TEMPLATE,
            output_format="json",
            variables=["content", "format_type", "host_info", "topic", "audience_level",
                      "duration_minutes", "include_explanations"]
        ))
        
        # Interview
        self.register(PromptTemplate(
            name="interview_standard",
            template_type=TemplateType.INTERVIEW,
            system_prompt=INTERVIEW_SYSTEM_PROMPT,
            user_prompt_template=INTERVIEW_USER_TEMPLATE,
            output_format="json",
            variables=["content", "interviewer_name", "interviewee_name",
                      "interviewee_background", "tone", "duration_minutes", "key_topics"]
        ))
    
    def register(self, template: PromptTemplate):
        """Register a new template."""
        self.templates[template.name] = template
    
    def get(self, name: str) -> Optional[PromptTemplate]:
        """Get a template by name."""
        return self.templates.get(name)
    
    def get_by_type(self, template_type: TemplateType) -> List[PromptTemplate]:
        """Get all templates of a specific type."""
        return [t for t in self.templates.values() if t.template_type == template_type]
    
    def list_all(self) -> List[str]:
        """List all registered template names."""
        return list(self.templates.keys())


# Global template registry instance
registry = TemplateRegistry()


def get_template(name: str) -> Optional[PromptTemplate]:
    """Get a template from the global registry."""
    return registry.get(name)


def create_dual_host_script_prompt(content: str, host1: str = "Host 1", host2: str = "Host 2",
                                   tone: str = "conversational", duration: int = 10) -> Dict[str, str]:
    """
    Convenience function to create a dual-host script generation prompt.
    
    Args:
        content: Source content for the script
        host1: Name of first host
        host2: Name of second host
        tone: Desired tone
        duration: Target duration in minutes
        
    Returns:
        Dict with system and user prompts
    """
    template = get_template("dual_host_conversation")
    if not template:
        raise ValueError("Template 'dual_host_conversation' not found")
    
    return template.render(
        content=content,
        host1_name=host1,
        host1_personality="friendly and knowledgeable",
        host2_name=host2,
        host2_personality="curious and engaging",
        tone=tone,
        duration_minutes=duration,
        include_elements="introduction, main content, summary, outro"
    )


def create_single_host_script_prompt(content: str, host: str = "Host",
                                     tone: str = "friendly", duration: int = 10) -> Dict[str, str]:
    """
    Convenience function to create a single-host script generation prompt.
    
    Args:
        content: Source content for the script
        host: Name of host
        tone: Desired tone
        duration: Target duration in minutes
        
    Returns:
        Dict with system and user prompts
    """
    template = get_template("single_host_standard")
    if not template:
        raise ValueError("Template 'single_host_standard' not found")
    
    return template.render(
        content=content,
        host_name=host,
        tone=tone,
        duration_minutes=duration,
        include_elements="introduction, main content, key takeaways, outro"
    )


# ============================================================================
# MOSS FORMAT SCRIPT TEMPLATES (for TTS)
# ============================================================================

MOSS_SCRIPT_SYSTEM_PROMPT = """你是专业的播客脚本撰写人，专门为 MOSS-TTSD 模型生成脚本。

输出要求：
1. 使用 JSON 格式，包含 segments 数组
2. 每个段落必须包含：speaker（host 或 co_host）、content（台词）、emotion（情绪）
3. speaker 只能是 "host" 或 "co_host"
4. emotion 可选：neutral, happy, curious, serious, excited
5. 内容要自然流畅，适合口语表达
6. 双人对话要有互动感

MOSS 格式说明：
- [S1] 标签对应 host
- [S2] 标签对应 co_host
"""

MOSS_SCRIPT_USER_TEMPLATE = """根据以下内容生成播客脚本：

## 内容摘要
{summary}

## 详细内容
{full_content}

## 亮点
{highlights}

## 要求
- 节目名称：{program_name}
- 结构：{structure}（single 或 dual）
- 英语学习：{english_learning}（off, vocab, translation）
- 期数：{episode_number}

请生成 JSON 格式的脚本，结构如下：
{{
    "title": "节目标题",
    "segments": [
        {{"speaker": "host", "content": "欢迎收听...", "emotion": "happy"}},
        {{"speaker": "co_host", "content": "大家好...", "emotion": "happy"}},
        ...
    ]
}}
"""


def create_moss_script_prompt(
    summary: str,
    full_content: str,
    highlights: List[str],
    program_name: str = "播客节目",
    structure: str = "dual",
    english_learning: str = "off",
    episode_number: int = 1
) -> Dict[str, str]:
    """
    创建 MOSS 格式脚本生成 Prompt
    
    Args:
        summary: 内容摘要
        full_content: 详细内容
        highlights: 亮点列表
        program_name: 节目名称
        structure: 结构（single/dual）
        english_learning: 英语学习模式
        episode_number: 期数
        
    Returns:
        Dict with system and user prompts
    """
    highlights_text = "\n".join([f"- {h}" for h in highlights])
    
    user_prompt = MOSS_SCRIPT_USER_TEMPLATE.format(
        summary=summary,
        full_content=full_content,
        highlights=highlights_text,
        program_name=program_name,
        structure=structure,
        english_learning=english_learning,
        episode_number=episode_number
    )
    
    return {
        "system": MOSS_SCRIPT_SYSTEM_PROMPT,
        "user": user_prompt
    }


# ============================================================================
# ENGLISH LEARNING TEMPLATES
# ============================================================================

ENGLISH_LEARNING_VOCAB_PROMPT = """从以下英文内容中提取 3-5 个重要单词或短语，并提供中文解释。

内容：{content}

返回格式（JSON）：
{{
    "vocabulary": [
        {{"word": "单词", "pronunciation": "音标", "meaning": "中文释义", "example": "例句"}},
        ...
    ]
}}
"""

ENGLISH_LEARNING_TRANSLATION_PROMPT = """将以下英文内容翻译成自然流畅的中文。

内容：{content}

返回格式（JSON）：
{{
    "original": "原文",
    "translation": "译文",
    "notes": "翻译说明（可选）"
}}
"""


def create_english_learning_vocab_prompt(content: str) -> str:
    """创建英语学习词汇提取 Prompt"""
    return ENGLISH_LEARNING_VOCAB_PROMPT.format(content=content[:500])


def create_english_learning_translation_prompt(content: str) -> str:
    """创建英语学习翻译 Prompt"""
    return ENGLISH_LEARNING_TRANSLATION_PROMPT.format(content=content[:500])


# Example usage and testing
if __name__ == "__main__":
    # Test template rendering
    sample_content = "The future of artificial intelligence in healthcare includes improved diagnostics, personalized treatment plans, and more efficient hospital operations."
    
    print("=== Single Host Template ===")
    single_prompt = create_single_host_script_prompt(
        content=sample_content,
        host="Alex",
        tone="energetic",
        duration=5
    )
    print(f"System: {single_prompt['system'][:100]}...")
    print(f"User: {single_prompt['user'][:200]}...")
    
    print("\n=== Dual Host Template ===")
    dual_prompt = create_dual_host_script_prompt(
        content=sample_content,
        host1="Alex",
        host2="Sam",
        tone="conversational",
        duration=10
    )
    print(f"System: {dual_prompt['system'][:100]}...")
    print(f"User: {dual_prompt['user'][:200]}...")
    
    print("\n=== All Registered Templates ===")
    for name in registry.list_all():
        print(f"  - {name}")
