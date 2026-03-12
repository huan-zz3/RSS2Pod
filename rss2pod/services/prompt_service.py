"""
Prompt 服务 - 封装 LLM Prompt 管理相关操作
"""

import os
import sys
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult
from llm.prompt_manager import PromptManager, PromptConfig


class PromptService(BaseService):
    """
    Prompt 服务
    
    提供 LLM Prompt 管理相关的业务逻辑封装
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        super().__init__(config_path, db_path)
        self._manager = None
    
    def _get_manager(self) -> PromptManager:
        """获取 Prompt 管理器"""
        if self._manager is None:
            self._manager = PromptManager(self.config_path)
        return self._manager
    
    def list_prompts(self) -> ServiceResult:
        """
        列出所有可用的 prompts
        
        Returns:
            ServiceResult 实例
        """
        try:
            manager = self._get_manager()
            prompts = manager.list_prompts()
            
            return ServiceResult(
                success=True,
                data=[p.to_dict() for p in prompts],
                metadata={'count': len(prompts)}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_prompt(self, name: str, group_id: Optional[str] = None) -> ServiceResult:
        """
        获取 prompt 配置
        
        Args:
            name: prompt 名称
            group_id: 可选，组别 ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            manager = self._get_manager()
            
            # 如果有 group_id，从数据库获取覆盖配置
            group_overrides = None
            if group_id and self.db:
                group = self.db.get_group(group_id)
                if group:
                    group_overrides = {'prompt_overrides': group.prompt_overrides}
            
            prompt = manager.get_prompt(name, group_id=group_id, group_overrides=group_overrides)
            
            return ServiceResult(
                success=True,
                data=prompt.to_dict()
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_prompt_template(self, name: str, group_id: Optional[str] = None) -> ServiceResult:
        """
        获取 prompt 模板
        
        Args:
            name: prompt 名称
            group_id: 可选，组别 ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            manager = self._get_manager()
            
            group_overrides = None
            if group_id and self.db:
                group = self.db.get_group(group_id)
                if group:
                    group_overrides = {'prompt_overrides': group.prompt_overrides}
            
            template = manager.get_prompt_template(name, group_id=group_id, group_overrides=group_overrides)
            
            return ServiceResult(
                success=True,
                data={'template': template}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_prompt_system(self, name: str, group_id: Optional[str] = None) -> ServiceResult:
        """
        获取 prompt system message
        
        Args:
            name: prompt 名称
            group_id: 可选，组别 ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            manager = self._get_manager()
            
            group_overrides = None
            if group_id and self.db:
                group = self.db.get_group(group_id)
                if group:
                    group_overrides = {'prompt_overrides': group.prompt_overrides}
            
            system = manager.get_prompt_system(name, group_id=group_id, group_overrides=group_overrides)
            
            return ServiceResult(
                success=True,
                data={'system': system}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def set_global_prompt(self, name: str, prompt_data: Dict[str, Any]) -> ServiceResult:
        """
        设置全局 prompt
        
        Args:
            name: prompt 名称
            prompt_data: prompt 数据字典
            
        Returns:
            ServiceResult 实例
        """
        try:
            manager = self._get_manager()
            
            prompt = PromptConfig(
                name=name,
                system=prompt_data.get('system', ''),
                template=prompt_data.get('template', ''),
                description=prompt_data.get('description', ''),
                variables=prompt_data.get('variables', [])
            )
            
            manager.set_global_prompt(name, prompt)
            
            # 保存到配置文件
            if manager.save_to_config(self.config_path):
                return ServiceResult(
                    success=True,
                    data={'name': name, 'saved': True}
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message='保存配置失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def set_group_override(self, group_id: str, name: str, prompt_data: Dict[str, Any]) -> ServiceResult:
        """
        设置组别 prompt 覆盖
        
        Args:
            group_id: 组别 ID
            name: prompt 名称
            prompt_data: prompt 数据字典
            
        Returns:
            ServiceResult 实例
        """
        try:
            if not self.db:
                return ServiceResult(
                    success=False,
                    error_message='数据库未初始化'
                )
            
            group = self.db.get_group(group_id)
            if not group:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 不存在'
                )
            
            prompt = PromptConfig(
                name=name,
                system=prompt_data.get('system', ''),
                template=prompt_data.get('template', ''),
                description=prompt_data.get('description', ''),
                variables=prompt_data.get('variables', [])
            )
            
            # 更新组别覆盖配置
            if 'prompt_overrides' not in group.prompt_overrides:
                group.prompt_overrides['prompt_overrides'] = {}
            
            group.prompt_overrides['prompt_overrides'][name] = prompt.to_dict()
            
            # 保存到数据库
            self.db.update_group(group)
            
            return ServiceResult(
                success=True,
                data={'group_id': group_id, 'name': name, 'saved': True}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def reset_group_override(self, group_id: str, name: str) -> ServiceResult:
        """
        重置组别 prompt 覆盖（恢复默认）
        
        Args:
            group_id: 组别 ID
            name: prompt 名称
            
        Returns:
            ServiceResult 实例
        """
        try:
            if not self.db:
                return ServiceResult(
                    success=False,
                    error_message='数据库未初始化'
                )
            
            group = self.db.get_group(group_id)
            if not group:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 不存在'
                )
            
            # 移除覆盖配置
            if 'prompt_overrides' in group.prompt_overrides.get('prompt_overrides', {}):
                if name in group.prompt_overrides['prompt_overrides']:
                    del group.prompt_overrides['prompt_overrides'][name]
            
            # 保存到数据库
            self.db.update_group(group)
            
            return ServiceResult(
                success=True,
                data={'group_id': group_id, 'name': name, 'reset': True}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def export_prompts(self, filepath: str) -> ServiceResult:
        """
        导出 prompts 到文件
        
        Args:
            filepath: 导出文件路径
            
        Returns:
            ServiceResult 实例
        """
        try:
            manager = self._get_manager()
            
            if manager.export_prompts(filepath):
                return ServiceResult(
                    success=True,
                    data={'filepath': filepath, 'exported': True}
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message='导出失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def import_prompts(self, filepath: str, merge: bool = True) -> ServiceResult:
        """
        从文件导入 prompts
        
        Args:
            filepath: 导入文件路径
            merge: 是否合并（True）或替换（False）
            
        Returns:
            ServiceResult 实例
        """
        try:
            manager = self._get_manager()
            
            if manager.import_prompts(filepath, merge=merge):
                # 保存到配置文件
                if manager.save_to_config(self.config_path):
                    return ServiceResult(
                        success=True,
                        data={'filepath': filepath, 'imported': True, 'merged': merge}
                    )
                else:
                    return ServiceResult(
                        success=False,
                        error_message='导入成功但保存配置失败'
                    )
            else:
                return ServiceResult(
                    success=False,
                    error_message='导入失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def render_template(self, name: str, variables: Dict[str, Any], group_id: Optional[str] = None) -> ServiceResult:
        """
        渲染 prompt 模板
        
        Args:
            name: prompt 名称
            variables: 变量字典
            group_id: 可选，组别 ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            manager = self._get_manager()
            
            group_overrides = None
            if group_id and self.db:
                group = self.db.get_group(group_id)
                if group:
                    group_overrides = {'prompt_overrides': group.prompt_overrides}
            
            template = manager.render_template(name, variables, group_id=group_id, group_overrides=group_overrides)
            
            return ServiceResult(
                success=True,
                data={'rendered_template': template}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )