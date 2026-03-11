"""
Group Processor - Group 处理器

封装 PipelineOrchestrator，提供简化的调用接口。
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.models import DatabaseManager
from ..database_service import DatabaseService
from services.pipeline.pipeline_orchestrator import PipelineOrchestrator
from services.pipeline.models import PipelineResult
from orchestrator.state_manager import StateManager, ProcessingState
from orchestrator.logging_config import get_logger


class GroupProcessor:
    """
    Group 处理器
    
    封装 PipelineOrchestrator，提供简化的调用接口
    """
    
    def __init__(
        self,
        group_id: str,
        db_path: str = "rss2pod.db",
        config: Optional[Dict[str, Any]] = None,
        force: bool = False,
        export_articles: bool = False
    ):
        """
        初始化 Group 处理器
        
        Args:
            group_id: Group ID
            db_path: 数据库文件路径
            config: 配置字典
            force: 强制模式，忽略文章更新检查，使用最新三篇文章
            export_articles: 导出文章列表到 JSON 文件
        """
        self.group_id = group_id
        self.db_path = db_path
        self.config = config or {}
        self.force = force
        self.export_articles = export_articles
        
        # 使用 DatabaseManager 供 PipelineOrchestrator 使用（保持兼容性）
        self.db = DatabaseManager(db_path)
        # 同时创建 DatabaseService 供后续使用
        self.database_service = DatabaseService(db_path=db_path)
        self.logger = get_logger('rss2pod.services.pipeline.group_processor')
        
        # 默认配置
        self.default_config = {
            'retry_attempts': 3,
            'retry_delay_seconds': 3,
        }
        if config:
            self.default_config.update(config)
    
    async def process(self) -> PipelineResult:
        """
        执行完整处理流程
        
        Returns:
            PipelineResult 实例
        """
        # 获取 Group
        group = self.db.get_group(self.group_id)
        if not group:
            return PipelineResult(
                success=False,
                group_id=self.group_id,
                error_message=f"Group {self.group_id} 不存在"
            )
        
        # 获取或创建状态
        state_manager = StateManager(self.db)
        state = state_manager.get_or_create_state(self.group_id)
        
        # 创建管道编排器
        orchestrator = PipelineOrchestrator(
            group=group,
            state=state,
            db=self.db,
            db_path=self.db_path,
            logger=self.logger,
            config=type('Config', (), self.default_config)(),
            force=self.force,
            export_articles=self.export_articles,
            state_manager=state_manager
        )
        
        # 运行管道
        result = await orchestrator.run()
        
        # 持久化状态到数据库
        state_manager.update_state(state)
        self.logger.info(f"[state] 状态已持久化到数据库")
        
        orchestrator.close()
        
        return result
    
    def process_sync(self) -> PipelineResult:
        """
        同步执行处理流程
        
        Returns:
            PipelineResult 实例
        """
        return asyncio.run(self.process())
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'db') and self.db:
            self.db.close()


async def process_group(
    group_id: str,
    db_path: str = "rss2pod.db",
    config: Optional[Dict[str, Any]] = None,
    force: bool = False,
    export_articles: bool = False
) -> PipelineResult:
    """
    便捷函数：处理单个 Group
    
    Args:
        group_id: Group ID
        db_path: 数据库文件路径
        config: 配置字典
        force: 强制模式
        export_articles: 导出文章列表
        
    Returns:
        PipelineResult 实例
    """
    processor = GroupProcessor(group_id, db_path, config, force=force, export_articles=export_articles)
    return await processor.process()


def process_group_sync(
    group_id: str,
    db_path: str = "rss2pod.db",
    config: Optional[Dict[str, Any]] = None,
    force: bool = False,
    export_articles: bool = False
) -> PipelineResult:
    """
    便捷函数：同步处理单个 Group
    
    Args:
        group_id: Group ID
        db_path: 数据库文件路径
        config: 配置字典
        force: 强制模式
        export_articles: 导出文章列表
        
    Returns:
        PipelineResult 实例
    """
    processor = GroupProcessor(group_id, db_path, config, force=force, export_articles=export_articles)
    return processor.process_sync()


def sync_fever_cache(db_path: str, limit: int = 1500):
    """
    同步 Fever 缓存
    
    Args:
        db_path: 数据库路径
        limit: 最大同步文章数量
        
    Returns:
        SyncResult 实例
    """
    from fetcher.fever_cache import FeverCacheManager
    from fetcher.fever_client import FeverClient, FeverCredentials
    from database.models import DatabaseManager
    import hashlib
    
    db = DatabaseManager(db_path)
    
    try:
        # 获取 Fever 配置
        from services.config_service import load_config
        config = load_config()
        fever_config = config.get('fever', {})
        
        username = fever_config.get('username', '')
        password = fever_config.get('password', '')
        api_key = hashlib.md5(f"{username}:{password}".encode()).hexdigest()
        
        credentials = FeverCredentials(
            api_url=fever_config.get('url', ''),
            api_key=api_key
        )
        
        client = FeverClient(credentials, db_path=db_path)
        cache_manager = FeverCacheManager(db_path)
        
        result = cache_manager.sync_items(client, limit=limit)
        
        # 关闭缓存管理器
        cache_manager.close()
        
        return result
    finally:
        db.close()


def get_fever_cache_stats(db_path: str) -> dict:
    """
    获取 Fever 缓存统计信息
    
    Args:
        db_path: 数据库路径
        
    Returns:
        统计信息字典
    """
    from fetcher.fever_cache import FeverCacheManager
    
    try:
        cache_manager = FeverCacheManager(db_path)
        stats = cache_manager.get_stats()
        cache_manager.close()
        return stats
    except Exception as e:
        return {'error': str(e)}
