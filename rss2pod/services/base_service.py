"""
基础服务类 - 所有服务的基类
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Dict
import os
import logging


@dataclass
class ServiceResult:
    """服务执行结果基类"""
    success: bool
    error_message: Optional[str] = None
    data: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LoggableMixin:
    """日志混入类 - 为服务类提供统一的日志功能"""
    
    _logger: Optional[logging.Logger] = None
    
    @classmethod
    def get_logger(cls, name: str = None) -> logging.Logger:
        """
        获取 logger 实例
        
        Args:
            name: 日志名称，默认使用类名
            
        Returns:
            Logger 实例
        """
        # 使用类级别的 logger 缓存
        if cls._logger is None:
            # 动态导入，避免循环依赖
            try:
                from rss2pod.orchestrator.logging_config import get_logger
                logger_name = name or f'rss2pod.services.{cls.__module__}.{cls.__name__}'
                cls._logger = get_logger(logger_name)
            except ImportError:
                # 如果导入失败，使用标准 logging
                logger_name = name or f'rss2pod.services.{cls.__name__}'
                cls._logger = logging.getLogger(logger_name)
        
        return cls._logger


class BaseService(LoggableMixin):
    """
    基础服务类
    
    提供通用的服务方法和属性
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        """
        初始化基础服务
        
        Args:
            config_path: 配置文件路径
            db_path: 数据库文件路径
        """
        self.config_path = config_path
        self.db_path = db_path
        self._config = None
        self._db = None
        # 初始化日志记录器
        self.logger = self.get_logger()
    
    @property
    def config(self):
        """懒加载配置"""
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    @property
    def db(self):
        """懒加载数据库连接"""
        if self._db is None:
            self._db = self._init_db()
        return self._db
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        import json
        import os
        
        config_path = self.config_path
        if not config_path:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'config.json'
            )
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在：{config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _init_db(self):
        """初始化数据库连接"""
        from database.models import DatabaseManager
        
        db_path = self.db_path
        if not db_path:
            db_path = self.config.get('db_path', 'rss2pod.db')
            if not os.path.isabs(db_path):
                db_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    db_path
                )
        
        return DatabaseManager(db_path)
    
    def close(self):
        """关闭服务，释放资源"""
        if self._db:
            self._db.close()
            self._db = None