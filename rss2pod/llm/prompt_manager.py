#!/usr/bin/env python3
"""
Prompt Manager - LLM Prompt 配置管理模块

负责：
- 加载和管理 prompt 配置
- 支持全局默认配置和组别单独配置
- 提供 prompt 的获取、设置、导出、导入功能
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class PromptConfig:
    """Prompt 配置"""
    name: str
    system: str = ""
    template: str = ""
    description: str = ""
    variables: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "system": self.system,
            "template": self.template,
            "description": self.description,
            "variables": self.variables
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptConfig':
        return cls(
            name=data.get("name", ""),
            system=data.get("system", ""),
            template=data.get("template", ""),
            description=data.get("description", ""),
            variables=data.get("variables", [])
        )


class PromptManager:
    """
    Prompt 管理器
    
    负责加载、管理和提供 LLM prompts
    支持全局默认配置和组别单独配置（覆盖）
    """
    
    # 默认 prompts 定义
    DEFAULT_PROMPTS = {
        "source_summarizer": PromptConfig(
            name="source_summarizer",
            description="源级摘要 - 为来自同一 RSS 源的文章生成综合摘要",
            system="你是专业的 RSS 内容摘要助手。请为以下来自同一 RSS 源的文章生成综合摘要。",
            template="""请为以下来自同一 RSS 源（{source_name}）的文章生成综合摘要。

要求：
1. 提炼所有文章的核心主题和关键信息
2. 识别文章之间的关联性和共同话题
3. 用简洁清晰的中文总结，避免冗余
4. 保持客观，不添加原文没有的信息
5. 如果文章之间有矛盾或冲突的观点，请指出

文章列表（共 {article_count} 篇）：

{articles_text}

请按照以下 JSON 格式返回摘要：
{{
    "source_name": "源名称",
    "article_count": 文章数量，
    "summary": "综合摘要内容（200-500 字）",
    "key_topics": ["关键主题 1", "关键主题 2", ...],
    "highlights": ["重要亮点 1", "重要亮点 2", ...],
    "generated_at": "生成时间（ISO 格式）"
}}
""",
            variables=["source_name", "article_count", "articles_text"]
        ),
        "group_aggregator": PromptConfig(
            name="group_aggregator",
            description="组级摘要 - 为多个 RSS 源的摘要生成播客大纲",
            system="你是专业的播客内容策划人。请为以下多个 RSS 源的摘要生成一期播客的大纲。",
            template="""你是专业的播客内容策划人。请为以下多个 RSS 源的摘要生成一期播客的大纲。

群组：{group_name}

## 各源摘要
{source_summaries_text}

要求：
1. 整合各源的核心内容，形成统一的主题
2. 识别不同源之间的关联和互补
3. 提炼出最重要的 3-5 个关键话题
4. 按照逻辑顺序组织内容结构

请按照以下 JSON 格式返回：
{{
    "title": "节目标题",
    "executive_summary": "执行摘要（100-200 字）",
    "full_summary": "完整摘要（300-500 字）",
    "top_highlights": ["亮点 1", "亮点 2", "亮点 3"],
    "topics": [
        {{"name": "话题 1", "priority": 1, "sources": ["源 1", "源 2"]}},
        {{"name": "话题 2", "priority": 2, "sources": ["源 3"]}}
    ],
    "generated_at": "生成时间（ISO 格式）"
}}
""",
            variables=["group_name", "source_summaries_text"]
        ),
        "script_generator": PromptConfig(
            name="script_generator",
            description="脚本生成 - 根据组级摘要生成播客脚本",
            system="你是专业的播客脚本撰写人。请根据以下内容生成一期播客脚本。",
            template="""你是专业的播客脚本撰写人。请根据以下内容生成一期播客脚本。

群组：{group_name}
结构：{structure_text}
英语学习：{learning_text}

## 执行摘要
{executive_summary}

## 详细内容
{full_summary}

## 亮点
{highlights_text}

要求：
1. 生成自然流畅的播客脚本
2. {structure_requirement}
3. 包含开场 (intro)、主要内容 (content)、结尾 (outro)
4. {learning_requirement}

请以 JSON 格式返回，包含以下结构：
{{
    "title": "节目标题",
    "segments": [
        {{"type": "intro", "speaker": "host", "content": "开场白"}},
        {{"type": "content", "speaker": "host", "content": "主要内容"}},
        {{"type": "outro", "speaker": "host", "content": "结束语"}}
    ]
}}
""",
            variables=["group_name", "structure_text", "learning_text", "executive_summary", 
                      "full_summary", "highlights_text", "structure_requirement", "learning_requirement"]
        )
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化 Prompt 管理器
        
        Args:
            config_path: 配置文件路径（默认从 config.json 读取）
        """
        self.config_path = config_path
        self.global_prompts: Dict[str, PromptConfig] = {}
        self.group_overrides: Dict[str, Dict[str, PromptConfig]] = {}
        self._load_global_prompts()
    
    def _load_global_prompts(self):
        """从配置文件加载全局 prompts"""
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                llm_config = config.get('llm', {})
                prompts_config = llm_config.get('prompts', {})
                
                # 加载每个 prompt
                for name, prompt_data in prompts_config.items():
                    if isinstance(prompt_data, dict):
                        self.global_prompts[name] = PromptConfig.from_dict({
                            **prompt_data,
                            "name": name
                        })
                
                # 确保所有默认 prompts 都存在
                for name, default_prompt in self.DEFAULT_PROMPTS.items():
                    if name not in self.global_prompts:
                        self.global_prompts[name] = default_prompt
                        
            except (json.JSONDecodeError, IOError) as e:
                print(f"[Warning] 加载 prompts 配置失败：{e}，使用默认配置")
                self.global_prompts = self.DEFAULT_PROMPTS.copy()
        else:
            self.global_prompts = self.DEFAULT_PROMPTS.copy()
    
    def get_prompt(self, name: str, group_id: Optional[str] = None, 
                   group_overrides: Optional[Dict[str, Any]] = None) -> PromptConfig:
        """
        获取 prompt 配置
        
        Args:
            name: prompt 名称
            group_id: 组别 ID（可选）
            group_overrides: 组别覆盖配置（可选，从数据库读取）
            
        Returns:
            PromptConfig 实例
        """
        # 优先使用组别覆盖
        if group_id and group_overrides:
            overrides = group_overrides.get('prompt_overrides', {})
            if name in overrides:
                override_data = overrides[name]
                if isinstance(override_data, dict):
                    return PromptConfig.from_dict({**override_data, "name": name})
        
        # 使用全局配置
        if name in self.global_prompts:
            return self.global_prompts[name]
        
        # 回退到默认配置
        if name in self.DEFAULT_PROMPTS:
            return self.DEFAULT_PROMPTS[name]
        
        # 返回空配置
        return PromptConfig(name=name)
    
    def get_prompt_template(self, name: str, group_id: Optional[str] = None,
                            group_overrides: Optional[Dict[str, Any]] = None) -> str:
        """
        获取 prompt 模板
        
        Args:
            name: prompt 名称
            group_id: 组别 ID（可选）
            group_overrides: 组别覆盖配置（可选）
            
        Returns:
            prompt 模板字符串
        """
        prompt = self.get_prompt(name, group_id, group_overrides)
        return prompt.template
    
    def get_prompt_system(self, name: str, group_id: Optional[str] = None,
                          group_overrides: Optional[Dict[str, Any]] = None) -> str:
        """
        获取 prompt system message
        
        Args:
            name: prompt 名称
            group_id: 组别 ID（可选）
            group_overrides: 组别覆盖配置（可选）
            
        Returns:
            system message 字符串
        """
        prompt = self.get_prompt(name, group_id, group_overrides)
        return prompt.system
    
    def set_global_prompt(self, name: str, prompt: PromptConfig):
        """
        设置全局 prompt
        
        Args:
            name: prompt 名称
            prompt: PromptConfig 实例
        """
        self.global_prompts[name] = prompt
    
    def set_group_override(self, group_id: str, name: str, prompt: PromptConfig):
        """
        设置组别 prompt 覆盖
        
        Args:
            group_id: 组别 ID
            name: prompt 名称
            prompt: PromptConfig 实例
        """
        if group_id not in self.group_overrides:
            self.group_overrides[group_id] = {}
        self.group_overrides[group_id][name] = prompt
    
    def list_prompts(self) -> List[PromptConfig]:
        """列出所有可用的 prompts"""
        return list(self.global_prompts.values())
    
    def get_available_variables(self, name: str) -> List[str]:
        """获取 prompt 可用的变量列表"""
        prompt = self.get_prompt(name)
        return prompt.variables
    
    def render_template(self, name: str, variables: Dict[str, Any],
                        group_id: Optional[str] = None,
                        group_overrides: Optional[Dict[str, Any]] = None) -> str:
        """
        渲染 prompt 模板
        
        Args:
            name: prompt 名称
            variables: 变量字典
            group_id: 组别 ID（可选）
            group_overrides: 组别覆盖配置（可选）
            
        Returns:
            渲染后的模板字符串
        """
        template = self.get_prompt_template(name, group_id, group_overrides)
        return template.format(**variables)
    
    def export_prompts(self, filepath: str, include_defaults: bool = True) -> bool:
        """
        导出 prompts 到文件
        
        Args:
            filepath: 导出文件路径
            include_defaults: 是否包含默认 prompts
            
        Returns:
            是否成功
        """
        try:
            export_data = {
                "prompts": {}
            }
            
            for name, prompt in self.global_prompts.items():
                export_data["prompts"][name] = prompt.to_dict()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
        except IOError as e:
            print(f"[Error] 导出 prompts 失败：{e}")
            return False
    
    def import_prompts(self, filepath: str, merge: bool = True) -> bool:
        """
        从文件导入 prompts
        
        Args:
            filepath: 导入文件路径
            merge: 是否合并（True）或替换（False）
            
        Returns:
            是否成功
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            prompts_data = import_data.get('prompts', {})
            
            if not merge:
                self.global_prompts.clear()
            
            for name, prompt_data in prompts_data.items():
                if isinstance(prompt_data, dict):
                    self.global_prompts[name] = PromptConfig.from_dict({
                        **prompt_data,
                        "name": name
                    })
            
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Error] 导入 prompts 失败：{e}")
            return False
    
    def save_to_config(self, config_path: Optional[str] = None) -> bool:
        """
        保存 prompts 到配置文件
        
        Args:
            config_path: 配置文件路径（默认使用初始化时的路径）
            
        Returns:
            是否成功
        """
        path = config_path or self.config_path
        if not path:
            print("[Error] 未指定配置文件路径")
            return False
        
        try:
            # 读取现有配置
            config = {}
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # 更新 prompts 配置
            if 'llm' not in config:
                config['llm'] = {}
            
            config['llm']['prompts'] = {
                name: prompt.to_dict() 
                for name, prompt in self.global_prompts.items()
            }
            
            # 保存配置
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return True
        except IOError as e:
            print(f"[Error] 保存配置失败：{e}")
            return False

    def get_prompt_option(self, category: str, option_key: str, default: str = "") -> str:
        """
        获取 prompt 选项配置
        
        Args:
            category: 类别（如 "script_generator"）
            option_key: 选项键（如 "structure_requirements.single"）
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        if not self.config_path or not os.path.exists(self.config_path):
            return default
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 解析嵌套键（如 "structure_requirements.single"）
            keys = option_key.split('.')
            value = config.get('llm', {}).get('prompt_options', {}).get(category, {})
            
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return default
            
            return value if value else default
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Warning] 读取 prompt_options 失败：{e}")
            return default


# 全局单例
_default_manager: Optional[PromptManager] = None


def get_prompt_manager(config_path: Optional[str] = None) -> PromptManager:
    """
    获取全局 PromptManager 单例
    
    Args:
        config_path: 配置文件路径（可选）
        
    Returns:
        PromptManager 实例
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = PromptManager(config_path)
    return _default_manager


def render_prompt(name: str, variables: Dict[str, Any], 
                  group_id: Optional[str] = None,
                  group_overrides: Optional[Dict[str, Any]] = None) -> str:
    """
    便捷函数：渲染 prompt 模板
    
    Args:
        name: prompt 名称
        variables: 变量字典
        group_id: 组别 ID（可选）
        group_overrides: 组别覆盖配置（可选）
        
    Returns:
        渲染后的模板字符串
    """
    manager = get_prompt_manager()
    return manager.render_template(name, variables, group_id, group_overrides)


if __name__ == "__main__":
    # 测试 PromptManager
    print("Testing PromptManager...")
    
    manager = PromptManager()
    
    # 列出所有 prompts
    print("\n可用 Prompts:")
    for prompt in manager.list_prompts():
        print(f"  - {prompt.name}: {prompt.description}")
    
    # 获取并渲染 source_summarizer prompt
    print("\n渲染 source_summarizer prompt:")
    template = manager.render_template("source_summarizer", {
        "source_name": "Test Source",
        "article_count": 3,
        "articles_text": "测试文章内容"
    })
    print(template[:500] + "...")
    
    print("\nPromptManager 测试完成!")