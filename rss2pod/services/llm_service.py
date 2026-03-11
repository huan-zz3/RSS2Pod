"""
LLM 服务 - 封装大语言模型相关操作
"""

import os
import sys
from typing import Optional, Dict, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult


class LLMService(BaseService):
    """
    LLM 服务
    
    提供大语言模型相关的业务逻辑封装
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        super().__init__(config_path, db_path)
        self._client = None
    
    def _get_client(self):
        """获取 LLM 客户端"""
        if self._client is None:
            from llm.llm_client import create_llm_client
            
            llm_config = self.config.get('llm', {})
            self._client = create_llm_client(
                provider="dashscope",
                api_key=llm_config.get('api_key', ''),
                base_url=llm_config.get('base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
                model=llm_config.get('model', 'qwen-plus')
            )
        
        return self._client
    
    def test_connection(self) -> ServiceResult:
        """
        测试 LLM 连接
        
        Returns:
            ServiceResult 实例
        """
        try:
            import requests
            
            llm_config = self.config.get('llm', {})
            
            headers = {
                "Authorization": f"Bearer {llm_config.get('api_key', '')}",
                "Content-Type": "application/json"
            }
            data = {
                "model": llm_config.get('model', 'qwen-plus'),
                "messages": [{"role": "user", "content": "Hi"}]
            }
            
            resp = requests.post(
                f"{llm_config.get('base_url', '')}/chat/completions",
                headers=headers, json=data, timeout=30
            )
            
            if resp.status_code == 200:
                return ServiceResult(
                    success=True,
                    data={
                        'provider': 'dashscope',
                        'model': llm_config.get('model', 'qwen-plus'),
                        'configured': True
                    }
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message=f'LLM API 错误：{resp.status_code}'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def chat(self, message: str, system_message: Optional[str] = None) -> ServiceResult:
        """
        与 LLM 对话
        
        Args:
            message: 用户消息
            system_message: 可选，系统消息
            
        Returns:
            ServiceResult 实例
        """
        try:
            client = self._get_client()
            
            # 构建消息列表
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": message})
            
            # 使用 generate 方法获取回复
            prompt = message
            if system_message:
                prompt = f"{system_message}\n\n{message}"
            
            response = client.generate(prompt)
            
            return ServiceResult(
                success=True,
                data={
                    'message': response,
                    'model': self.config.get('llm', {}).get('model', 'qwen-plus')
                }
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def generate_json(self, prompt: str, schema: Optional[Dict] = None) -> ServiceResult:
        """
        使用 LLM 生成结构化 JSON 数据
        
        Args:
            prompt: 提示文本
            schema: 可选，JSON schema
            
        Returns:
            ServiceResult 实例
        """
        try:
            client = self._get_client()
            result = client.generate_json(prompt, schema=schema)
            
            return ServiceResult(
                success=True,
                data=result
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def generate_source_summary(
        self,
        source: str,
        articles: list,
        prompt_template: str
    ) -> Dict[str, Any]:
        """
        生成源级摘要
        
        Args:
            source: 源名称/URL
            articles: 文章列表
            prompt_template: Prompt 模板
            
        Returns:
            包含 source_name, article_count, summary, key_topics, highlights 的字典
        """
        try:
            client = self._get_client()
            
            # 构建文章文本
            articles_text = "\n\n".join([
                f"标题：{art.title}\n链接：{art.link}\n内容：{art.text_content[:500]}"
                for art in articles
            ])
            
            # 渲染 prompt
            rendered_prompt = prompt_template.format(
                source_name=source,
                article_count=len(articles),
                articles_text=articles_text
            )
            
            # 调用 LLM 生成 JSON
            result = client.generate_json(rendered_prompt)
            
            # 添加 source 字段
            result['source'] = source
            
            return result
            
        except Exception as e:
            raise Exception(f"生成源级摘要失败：{e}")
    
    def generate_group_summary(
        self,
        source_summaries: list,
        group_name: str,
        prompt_template: str = None
    ) -> Dict[str, Any]:
        """
        生成组级摘要
        
        Args:
            source_summaries: 源级摘要列表
            group_name: 组名称
            prompt_template: 可选的 prompt 模板
            
        Returns:
            组级摘要字典
        """
        try:
            from llm.group_aggregator import GroupAggregator, SourceSummary as AggSourceSummary
            
            client = self._get_client()
            aggregator = GroupAggregator(client, group_name)
            
            for summary in source_summaries:
                agg_summary = AggSourceSummary(
                    source_name=summary.get('source', ''),
                    summary=summary.get('summary', ''),
                    article_count=summary.get('article_count', 0),
                    key_topics=summary.get('key_topics', []),
                    highlights=summary.get('highlights', []),
                    generated_at=summary.get('generated_at', datetime.now().isoformat())
                )
                aggregator.add_source_summary(agg_summary)
            
            group_summary = aggregator.aggregate()
            
            return group_summary
            
        except Exception as e:
            raise Exception(f"生成组级摘要失败：{e}")
    
    def get_prompt_manager(self):
        """
        获取 PromptManager 实例
        
        Returns:
            PromptManager 实例
        """
        from llm.prompt_manager import get_prompt_manager
        
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'config.json'
        )
        return get_prompt_manager(config_path)
    
    def get_prompt_template(
        self,
        template_type: str,
        group_id: str = None,
        group_overrides: Dict = None
    ) -> str:
        """
        获取 Prompt 模板
        
        Args:
            template_type: 模板类型 (source_summarizer, script_generator 等)
            group_id: Group ID（可选）
            group_overrides: Group 覆盖配置（可选）
            
        Returns:
            渲染后的模板字符串
        """
        prompt_manager = self.get_prompt_manager()
        return prompt_manager.get_prompt_template(
            template_type,
            group_id=group_id,
            group_overrides=group_overrides
        )
    
    def get_prompt_system(
        self,
        template_type: str,
        group_id: str = None,
        group_overrides: Dict = None
    ) -> str:
        """
        获取 Prompt System Message
        
        Args:
            template_type: 模板类型
            group_id: Group ID（可选）
            group_overrides: Group 覆盖配置（可选）
            
        Returns:
            System message 字符串
        """
        prompt_manager = self.get_prompt_manager()
        return prompt_manager.get_prompt_system(
            template_type,
            group_id=group_id,
            group_overrides=group_overrides
        )
    
    def _get_prompt_manager(self):
        """获取 PromptManager 实例（内部使用）"""
        return self.get_prompt_manager()
    
    def generate_script(
        self,
        group_summary: Dict[str, Any],
        prompt_template: str,
        podcast_structure: str = 'single',
        english_learning_mode: str = 'off'
    ) -> Dict[str, Any]:
        """
        生成播客脚本
        
        Args:
            group_summary: 组级摘要
            prompt_template: Prompt 模板
            podcast_structure: 播客结构 ('single' 或 'dual')
            english_learning_mode: 英语学习模式
            
        Returns:
            包含 title 和 segments 的脚本字典
        """
        try:
            client = self._get_client()
            
            # 获取 PromptManager 以读取 prompt_options 配置
            prompt_manager = self._get_prompt_manager()
            
            # 从 prompt_options 读取 structure_requirement
            structure_requirement = prompt_manager.get_prompt_option(
                "script_generator",
                f"structure_requirements.{podcast_structure}",
                "使用单人播报风格" if podcast_structure == "single" else "区分主持人 (host) 和协主持人 (co_host) 的对话，交替发言"
            )
            
            # 从 prompt_options 读取 learning_requirement
            learning_requirement = prompt_manager.get_prompt_option(
                "script_generator",
                f"learning_requirements.{english_learning_mode}",
                " "  # 默认空字符串
            )
            
            # 构建 prompt 变量
            executive_summary = group_summary.get('executive_summary', '')
            full_summary = group_summary.get('full_summary', '')
            highlights = group_summary.get('top_highlights', [])
            
            # 确定说话人数量
            speaker_count = 2 if podcast_structure == 'dual' else 1
            structure_text = "双人对话" if speaker_count == 2 else "单人播报"
            learning_text = english_learning_mode
            
            highlights_text = '\n'.join(['- ' + h for h in highlights]) if highlights else '无特定亮点'
            
            # 渲染 prompt
            prompt = prompt_template.format(
                group_name='',
                structure_text=structure_text,
                learning_text=learning_text,
                executive_summary=executive_summary,
                full_summary=full_summary,
                highlights_text=highlights_text,
                structure_requirement=structure_requirement,
                learning_requirement=learning_requirement
            )
            
            # 调用 LLM 生成 JSON
            script_json = client.generate_json(prompt)
            
            return script_json
            
        except Exception as e:
            raise Exception(f"生成播客脚本失败：{e}")
    
    def close(self):
        """关闭服务，释放资源"""
        self._client = None
        super().close()
