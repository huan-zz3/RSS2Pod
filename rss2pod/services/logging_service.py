"""
日志服务 - 封装日志相关操作
"""

import os
import sys
import logging
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult

# 导出 setup_logging 函数供外部使用


class LoggingService(BaseService):
    """
    日志服务
    
    提供日志管理相关的业务逻辑封装
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        super().__init__(config_path, db_path)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        获取 Logger 实例
        
        Args:
            name: Logger 名称
            
        Returns:
            Logger 实例
        """
        from orchestrator.logging_config import get_logger
        return get_logger(name)
    
    def get_logger_for_service(self, service_name: str) -> logging.Logger:
        """
        获取服务专用的 Logger
        
        Args:
            service_name: 服务名称
            
        Returns:
            Logger 实例
        """
        return self.get_logger(f'rss2pod.services.{service_name}')
    
    def get_logger_for_pipeline(self, group_id: str = None) -> logging.Logger:
        """
        获取管道专用的 Logger
        
        Args:
            group_id: 可选的 Group ID
            
        Returns:
            Logger 实例
        """
        if group_id:
            return self.get_logger(f'rss2pod.pipeline.{group_id}')
        return self.get_logger('rss2pod.pipeline')
    
    def set_log_level(self, level: str) -> ServiceResult:
        """
        设置全局日志级别
        
        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            
        Returns:
            ServiceResult 实例
        """
        try:
            from orchestrator.logging_config import setup_logging
            
            # 重新设置日志配置
            setup_logging(level=level)
            
            return ServiceResult(
                success=True,
                data={'level': level}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_log_level(self) -> ServiceResult:
        """
        获取当前日志级别
        
        Returns:
            ServiceResult 实例
        """
        try:
            root_logger = logging.getLogger()
            level = logging.getLevelName(root_logger.level)
            
            return ServiceResult(
                success=True,
                data={'level': level}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
