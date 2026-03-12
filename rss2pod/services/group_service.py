"""
Group 服务 - 封装 Group 管理相关操作
"""

import os
import sys
from typing import Optional, Dict, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult
from database.models import Group


class GroupService(BaseService):
    """
    Group 服务
    
    提供 Group 管理相关的业务逻辑封装
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        super().__init__(config_path, db_path)
    
    def list_groups(self, enabled_only: bool = False) -> ServiceResult:
        """
        列出所有 Group
        
        Args:
            enabled_only: 是否只列出启用的 Group
            
        Returns:
            ServiceResult 实例
        """
        try:
            groups = self.db.get_all_groups(enabled_only=enabled_only)
            
            return ServiceResult(
                success=True,
                data=[g.to_dict() for g in groups],
                metadata={'count': len(groups)}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_group(self, group_id: str) -> ServiceResult:
        """
        获取单个 Group 详情
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            group = self.db.get_group(group_id)
            
            if not group:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 不存在'
                )
            
            return ServiceResult(
                success=True,
                data=group.to_dict()
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def create_group(self, group_data: Dict[str, Any]) -> ServiceResult:
        """
        创建新 Group
        
        Args:
            group_data: Group 数据字典，包含：
                - name: 组名
                - description: 描述（可选）
                - rss_sources: RSS 源列表
                - trigger_type: 触发类型
                - trigger_config: 触发配置
                - podcast_structure: 播客结构（single/dual）
                - english_learning_mode: 英语学习模式
                - audio_speed: 音频播放速度 (0.5-2.0, 默认 1.0)
                
        Returns:
            ServiceResult 实例
        """
        try:
            # 生成 Group ID
            existing_groups = self.db.get_all_groups()
            group_id = f"group-{len(existing_groups) + 1}"
            
            # 获取 audio_speed，默认为 1.0
            audio_speed = group_data.get('audio_speed', 1.0)
            if audio_speed is None:
                audio_speed = 1.0
            
            # 创建 Group 对象
            group = Group(
                id=group_id,
                name=group_data.get('name', '未命名组'),
                description=group_data.get('description', ''),
                rss_sources=group_data.get('rss_sources', []),
                summary_preference=group_data.get('summary_preference', 'balanced'),
                podcast_structure=group_data.get('podcast_structure', 'single'),
                english_learning_mode=group_data.get('english_learning_mode', 'off'),
                audio_speed=float(audio_speed),
                trigger_type=group_data.get('trigger_type', 'time'),
                trigger_config=group_data.get('trigger_config', {}),
                prompt_overrides=group_data.get('prompt_overrides', {}),
                enabled=True
            )
            
            # 保存到数据库
            if self.db.add_group(group):
                return ServiceResult(
                    success=True,
                    data=group.to_dict()
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message='保存到数据库失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def update_group(self, group_id: str, group_data: Dict[str, Any]) -> ServiceResult:
        """
        更新 Group
        
        Args:
            group_id: Group ID
            group_data: 更新的数据字典
            
        Returns:
            ServiceResult 实例
        """
        try:
            group = self.db.get_group(group_id)
            
            if not group:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 不存在'
                )
            
            # 更新字段
            if 'name' in group_data:
                group.name = group_data['name']
            if 'description' in group_data:
                group.description = group_data['description']
            if 'rss_sources' in group_data:
                group.rss_sources = group_data['rss_sources']
            if 'summary_preference' in group_data:
                group.summary_preference = group_data['summary_preference']
            if 'podcast_structure' in group_data:
                group.podcast_structure = group_data['podcast_structure']
            if 'english_learning_mode' in group_data:
                group.english_learning_mode = group_data['english_learning_mode']
            if 'audio_speed' in group_data:
                audio_speed = group_data['audio_speed']
                if audio_speed is None:
                    audio_speed = 1.0
                group.audio_speed = float(audio_speed)
            if 'trigger_type' in group_data:
                group.trigger_type = group_data['trigger_type']
            if 'trigger_config' in group_data:
                group.trigger_config = group_data['trigger_config']
            if 'prompt_overrides' in group_data:
                group.prompt_overrides = group_data['prompt_overrides']
            
            group.updated_at = datetime.now().isoformat()
            
            # 保存到数据库
            if self.db.update_group(group):
                return ServiceResult(
                    success=True,
                    data=group.to_dict()
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message='保存到数据库失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def delete_group(self, group_id: str) -> ServiceResult:
        """
        删除 Group
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            group = self.db.get_group(group_id)
            
            if not group:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 不存在'
                )
            
            # 删除 Group（包括相关文件和数据库记录）
            if self.db.delete_group(group_id):
                return ServiceResult(
                    success=True,
                    data={'deleted_group_id': group_id}
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message='删除失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def enable_group(self, group_id: str) -> ServiceResult:
        """
        启用 Group
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            group = self.db.get_group(group_id)
            
            if not group:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 不存在'
                )
            
            group.enabled = True
            group.updated_at = datetime.now().isoformat()
            
            if self.db.update_group(group):
                return ServiceResult(
                    success=True,
                    data={'group_id': group_id, 'enabled': True}
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message='更新数据库失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def disable_group(self, group_id: str) -> ServiceResult:
        """
        禁用 Group
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            group = self.db.get_group(group_id)
            
            if not group:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 不存在'
                )
            
            group.enabled = False
            group.updated_at = datetime.now().isoformat()
            
            if self.db.update_group(group):
                return ServiceResult(
                    success=True,
                    data={'group_id': group_id, 'enabled': False}
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message='更新数据库失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_group_episodes(self, group_id: str, limit: int = 50) -> ServiceResult:
        """
        获取 Group 的期数列表
        
        Args:
            group_id: Group ID
            limit: 最大返回数量
            
        Returns:
            ServiceResult 实例
        """
        try:
            episodes = self.db.get_episodes_by_group(group_id, limit)
            
            return ServiceResult(
                success=True,
                data=[ep.to_dict() for ep in episodes],
                metadata={'count': len(episodes)}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )