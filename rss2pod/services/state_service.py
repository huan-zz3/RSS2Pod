"""
状态服务 - 封装状态管理相关操作
"""

import os
import sys
from typing import Optional, List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult
from orchestrator.state_manager import StateManager, ProcessingState, PipelineRun


class StateService(BaseService):
    """
    状态服务
    
    提供状态管理相关的业务逻辑封装
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        super().__init__(config_path, db_path)
        self._state_manager = None
    
    def _get_state_manager(self) -> StateManager:
        """获取状态管理器"""
        if self._state_manager is None:
            if self.db:
                self._state_manager = StateManager(self.db)
            else:
                from database.models import DatabaseManager
                db = DatabaseManager(self.db_path)
                self._state_manager = StateManager(db)
        return self._state_manager
    
    def get_state(self, group_id: str) -> ServiceResult:
        """
        获取 Group 处理状态
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
            state = state_manager.get_state(group_id)
            
            if state:
                return ServiceResult(
                    success=True,
                    data=state.to_dict()
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message=f"Group {group_id} 的状态不存在"
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_or_create_state(self, group_id: str) -> ServiceResult:
        """
        获取或创建 Group 处理状态
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
            state = state_manager.get_or_create_state(group_id)
            
            return ServiceResult(
                success=True,
                data=state.to_dict()
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def update_state(self, group_id: str, state_data: Dict[str, Any]) -> ServiceResult:
        """
        更新处理状态
        
        Args:
            group_id: Group ID
            state_data: 状态数据
            
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
            state = state_manager.get_or_create_state(group_id)
            
            # 更新字段
            for key, value in state_data.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            
            success = state_manager.update_state(state)
            
            return ServiceResult(
                success=success,
                data=state.to_dict()
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def set_status(self, group_id: str, status: str, error_message: Optional[str] = None) -> ServiceResult:
        """
        设置 Group 处理状态
        
        Args:
            group_id: Group ID
            status: 状态值 (idle | running | error | disabled)
            error_message: 错误信息
            
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
            success = state_manager.set_status(group_id, status, error_message)
            
            return ServiceResult(
                success=success,
                data={'group_id': group_id, 'status': status}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def update_episode_number(self, group_id: str, episode_number: int) -> ServiceResult:
        """
        更新 Group 的最后一期期数
        
        Args:
            group_id: Group ID
            episode_number: 期数
            
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
            success = state_manager.update_episode_number(group_id, episode_number)
            
            return ServiceResult(
                success=success,
                data={'group_id': group_id, 'episode_number': episode_number}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_last_episode_number(self, group_id: str) -> ServiceResult:
        """
        获取 Group 的最后一期期数
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
            episode_number = state_manager.get_last_episode_number(group_id)
            
            return ServiceResult(
                success=True,
                data={'group_id': group_id, 'episode_number': episode_number}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def acquire_lock(self, group_id: str, owner: str = "default") -> ServiceResult:
        """
        获取 Group 处理锁
        
        Args:
            group_id: Group ID
            owner: 锁所有者标识
            
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
            success = state_manager.acquire_lock(group_id, owner)
            
            return ServiceResult(
                success=success,
                data={'group_id': group_id, 'locked': success}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def release_lock(self, group_id: str, owner: str = "default") -> ServiceResult:
        """
        释放 Group 处理锁
        
        Args:
            group_id: Group ID
            owner: 锁所有者标识
            
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
            success = state_manager.release_lock(group_id, owner)
            
            return ServiceResult(
                success=success,
                data={'group_id': group_id, 'released': success}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def is_locked(self, group_id: str) -> ServiceResult:
        """
        检查 Group 是否被锁定
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
            locked = state_manager.is_locked(group_id)
            
            return ServiceResult(
                success=True,
                data={'group_id': group_id, 'locked': locked}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def create_run(self, group_id: str) -> ServiceResult:
        """
        创建管道运行记录
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
            run = state_manager.create_run(group_id)
            
            return ServiceResult(
                success=True,
                data=run.to_dict()
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def complete_run(self, run_id: str, status: str, episode_id: Optional[str] = None) -> ServiceResult:
        """
        完成管道运行
        
        Args:
            run_id: 运行记录 ID
            status: 最终状态
            episode_id: 生成的 Episode ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
            
            # 查找运行记录
            # 注意：这里需要从数据库获取
            # 由于 PipelineRun 没有直接获取方法，我们通过 group_id 查找最新的
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT * FROM pipeline_run WHERE id = ?', (run_id,))
            row = cursor.fetchone()
            
            if not row:
                return ServiceResult(
                    success=False,
                    error_message=f"运行记录 {run_id} 不存在"
                )
            
            columns = [desc[0] for desc in cursor.description]
            run = PipelineRun.from_row(row, columns)
            
            success = state_manager.complete_run(run, status, episode_id)
            
            return ServiceResult(
                success=success,
                data=run.to_dict()
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_runs_by_group(self, group_id: str, limit: int = 50) -> ServiceResult:
        """
        获取 Group 的运行历史
        
        Args:
            group_id: Group ID
            limit: 返回数量限制
            
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
            runs = state_manager.get_runs_by_group(group_id, limit)
            
            return ServiceResult(
                success=True,
                data=[run.to_dict() for run in runs],
                metadata={'count': len(runs)}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_stats(self) -> ServiceResult:
        """
        获取统计信息
        
        Returns:
            ServiceResult 实例
        """
        try:
            state_manager = self._get_state_manager()
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
    
    def close(self):
        """关闭服务，释放资源"""
        if self._state_manager and self._state_manager.db:
            self._state_manager.db.close()
        super().close()
