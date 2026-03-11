"""
统计服务 - 封装系统统计信息相关操作
"""

import os
import sys
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult


class StatsService(BaseService):
    """
    统计服务
    
    提供系统统计信息相关的业务逻辑封装
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        super().__init__(config_path, db_path)
    
    def get_system_stats(self) -> ServiceResult:
        """
        获取系统整体统计信息
        
        Returns:
            ServiceResult 实例
        """
        try:
            stats = {}
            
            # 数据库统计
            db_stats = self.db.get_stats()
            stats['database'] = db_stats
            
            # Fever 缓存统计
            from orchestrator.group_processor import get_fever_cache_stats
            fever_stats = get_fever_cache_stats(self.db.db_path)
            stats['fever_cache'] = fever_stats
            
            # 处理状态统计
            from orchestrator.state_manager import StateManager
            state_manager = StateManager(self.db)
            state_stats = state_manager.get_stats()
            stats['processing_state'] = state_stats
            
            # 配置信息
            stats['config'] = {
                'db_path': self.config.get('db_path', 'rss2pod.db'),
                'llm_provider': self.config.get('llm', {}).get('provider', 'dashscope'),
                'llm_model': self.config.get('llm', {}).get('model', 'qwen-plus'),
                'tts_provider': self.config.get('tts', {}).get('provider', 'siliconflow'),
                'tts_model': self.config.get('tts', {}).get('model', 'fnlp/MOSS-TTSD-v0.5'),
                'orchestrator_check_interval': self.config.get('orchestrator', {}).get('check_interval_seconds', 60),
                'orchestrator_max_concurrent': self.config.get('orchestrator', {}).get('max_concurrent_groups', 3)
            }
            
            return ServiceResult(
                success=True,
                data=stats
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_database_stats(self) -> ServiceResult:
        """
        获取数据库统计信息
        
        Returns:
            ServiceResult 实例
        """
        try:
            stats = self.db.get_stats()
            
            return ServiceResult(
                success=True,
                data=stats
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_fever_cache_stats(self) -> ServiceResult:
        """
        获取 Fever 缓存统计信息
        
        Returns:
            ServiceResult 实例
        """
        try:
            from orchestrator.group_processor import get_fever_cache_stats
            
            stats = get_fever_cache_stats(self.db.db_path)
            
            return ServiceResult(
                success=True,
                data=stats
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_processing_stats(self) -> ServiceResult:
        """
        获取处理状态统计信息
        
        Returns:
            ServiceResult 实例
        """
        try:
            from orchestrator.state_manager import StateManager
            
            state_manager = StateManager(self.db)
            stats = state_manager.get_stats()
            
            return ServiceResult(
                success=True,
                data=stats
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_group_stats(self, group_id: str) -> ServiceResult:
        """
        获取指定 Group 的统计信息
        
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
            
            # 获取 Group 的期数统计
            episodes = self.db.get_episodes_by_group(group_id, limit=1000)
            
            # 获取处理状态
            from orchestrator.state_manager import StateManager
            state_manager = StateManager(self.db)
            state = state_manager.get_processing_state(group_id)
            
            stats = {
                'group': group.to_dict(),
                'total_episodes': len(episodes),
                'last_episode_number': state.last_episode_number if state else 0,
                'last_run_at': state.last_run_at if state else None,
                'status': state.status if state else 'unknown',
                'episodes': [ep.to_dict() for ep in episodes[:10]]  # 最近 10 期
            }
            
            return ServiceResult(
                success=True,
                data=stats
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_recent_activity(self, days: int = 7) -> ServiceResult:
        """
        获取最近活动记录
        
        Args:
            days: 天数
            
        Returns:
            ServiceResult 实例
        """
        try:
            from orchestrator.state_manager import StateManager
            
            state_manager = StateManager(self.db)
            stats = state_manager.get_stats()
            
            # 获取最近的 pipeline 运行记录
            cursor = self.db.conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute('''
                SELECT * FROM pipeline_run 
                WHERE started_at >= ? 
                ORDER BY started_at DESC 
                LIMIT 100
            ''', (cutoff_date,))
            
            recent_runs = []
            for row in cursor.fetchall():
                run_data = dict(row)
                recent_runs.append(run_data)
            
            activity = {
                'days': days,
                'runs_today': stats.get('runs_today', 0),
                'recent_runs': recent_runs,
                'states_by_status': stats.get('states_by_status', {})
            }
            
            return ServiceResult(
                success=True,
                data=activity
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )