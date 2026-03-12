"""
资源服务 - 封装资源文件管理相关操作
"""

import os
import sys
from typing import Optional, List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult


class AssetService(BaseService):
    """
    资源服务
    
    提供资源文件管理相关的业务逻辑封装
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        super().__init__(config_path, db_path)
    
    def get_episode_manager(self, group_id: str, timestamp: str):
        """
        获取 Episode 资源管理器
        
        Args:
            group_id: Group ID
            timestamp: Episode 时间戳
            
        Returns:
            EpisodeAssetManager 实例
        """
        from orchestrator.asset_manager import EpisodeAssetManager
        return EpisodeAssetManager(group_id, timestamp)
    
    def list_episode_assets(self, group_id: str) -> ServiceResult:
        """
        列出 Group 下所有 Episode 的资源
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            from orchestrator.asset_manager import EpisodeAssetManager
            
            episodes = EpisodeAssetManager.list_episode_assets(group_id)
            
            return ServiceResult(
                success=True,
                data=episodes,
                metadata={'count': len(episodes)}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_episode_assets(self, group_id: str, timestamp: str) -> ServiceResult:
        """
        获取指定 Episode 的资源详情
        
        Args:
            group_id: Group ID
            timestamp: Episode 时间戳
            
        Returns:
            ServiceResult 实例
        """
        try:
            from orchestrator.asset_manager import EpisodeAssetManager
            
            manager = EpisodeAssetManager(group_id, timestamp)
            assets = manager.list_assets()
            
            if not assets:
                return ServiceResult(
                    success=False,
                    error_message=f'未找到 Episode {timestamp} 的资源'
                )
            
            return ServiceResult(
                success=True,
                data=assets
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def cleanup_episode_assets(
        self,
        group_id: str,
        timestamp: Optional[str] = None
    ) -> ServiceResult:
        """
        清理 Episode 中间文件
        
        Args:
            group_id: Group ID
            timestamp: Episode 时间戳（不填则清理所有）
            
        Returns:
            ServiceResult 实例
        """
        try:
            from orchestrator.asset_manager import EpisodeAssetManager
            
            if timestamp:
                # 清理指定 Episode
                manager = EpisodeAssetManager(group_id, timestamp)
                manager.cleanup()
                
                return ServiceResult(
                    success=True,
                    data={
                        'group_id': group_id,
                        'timestamp': timestamp,
                        'cleaned': True
                    }
                )
            else:
                # 清理所有 Episode
                episodes = EpisodeAssetManager.list_episode_assets(group_id)
                
                if not episodes:
                    return ServiceResult(
                        success=False,
                        error_message=f'没有找到 Group {group_id} 的资源'
                    )
                
                cleaned_count = 0
                for ep in episodes:
                    ts = ep.get('episode_timestamp', 'unknown')
                    manager = EpisodeAssetManager(group_id, ts)
                    manager.cleanup()
                    cleaned_count += 1
                
                return ServiceResult(
                    success=True,
                    data={
                        'group_id': group_id,
                        'cleaned_count': cleaned_count
                    }
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )


def list_episode_assets(group_id: str) -> List[Dict[str, Any]]:
    """
    便捷函数：列出 Group 下所有 Episode 的资源
    
    Args:
        group_id: Group ID
        
    Returns:
        Episode 资源列表
    """
    from orchestrator.asset_manager import EpisodeAssetManager
    return EpisodeAssetManager.list_episode_assets(group_id)


def get_episode_assets(group_id: str, timestamp: str) -> Optional[Dict[str, Any]]:
    """
    便捷函数：获取指定 Episode 的资源详情
    
    Args:
        group_id: Group ID
        timestamp: Episode 时间戳
        
    Returns:
        资源详情字典
    """
    from orchestrator.asset_manager import EpisodeAssetManager
    manager = EpisodeAssetManager(group_id, timestamp)
    return manager.list_assets()


def cleanup_episode_assets(group_id: str, timestamp: Optional[str] = None):
    """
    便捷函数：清理 Episode 中间文件
    
    Args:
        group_id: Group ID
        timestamp: Episode 时间戳（不填则清理所有）
    """
    from orchestrator.asset_manager import EpisodeAssetManager
    
    if timestamp:
        manager = EpisodeAssetManager(group_id, timestamp)
        manager.cleanup()
    else:
        episodes = EpisodeAssetManager.list_episode_assets(group_id)
        for ep in episodes:
            ts = ep.get('episode_timestamp', 'unknown')
            manager = EpisodeAssetManager(group_id, ts)
            manager.cleanup()
