"""
Pipeline Service - Pipeline 即服务

对外统一接口，提供完整的处理管道服务。
"""

import os
import sys
import asyncio
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.models import DatabaseManager
from .group_processor import GroupProcessor
from .models import PipelineResult


class PipelineService:
    """
    Pipeline 即服务 - 对外统一接口
    
    提供简化的调用接口，用于执行完整的处理管道。
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        """
        初始化 Pipeline 服务
        
        Args:
            config_path: 配置文件路径
            db_path: 数据库文件路径
        """
        self.config_path = config_path
        self.db_path = db_path or 'rss2pod.db'
        
        # 确定 db_path 的绝对路径
        if self.db_path and not os.path.isabs(self.db_path):
            self.db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                self.db_path
            )
    
    async def run(
        self,
        group_id: str,
        force: bool = False,
        export_articles: bool = False
    ) -> PipelineResult:
        """
        运行处理管道（异步）
        
        Args:
            group_id: Group ID
            force: 强制模式，忽略文章更新检查
            export_articles: 导出文章列表到 JSON 文件
            
        Returns:
            PipelineResult 实例
        """
        processor = GroupProcessor(
            group_id=group_id,
            db_path=self.db_path,
            force=force,
            export_articles=export_articles
        )
        
        return await processor.process()
    
    def run_sync(
        self,
        group_id: str,
        force: bool = False,
        export_articles: bool = False
    ) -> PipelineResult:
        """
        运行处理管道（同步）
        
        Args:
            group_id: Group ID
            force: 强制模式
            export_articles: 导出文章列表
            
        Returns:
            PipelineResult 实例
        """
        return asyncio.run(self.run(group_id, force, export_articles))
    
    async def run_all_enabled(
        self,
        only_enabled: bool = True
    ) -> List[PipelineResult]:
        """
        运行所有启用的 Group 的处理管道（异步）
        
        Args:
            only_enabled: 是否只处理启用的 Group
            
        Returns:
            PipelineResult 列表
        """
        db = DatabaseManager(self.db_path)
        
        try:
            groups = db.get_all_groups()
            
            # 过滤启用的 Group
            if only_enabled:
                groups = [g for g in groups if getattr(g, 'enabled', True)]
            
            results = []
            for group in groups:
                result = await self.run(group.id)
                results.append(result)
            
            return results
            
        finally:
            db.close()
    
    def run_all_enabled_sync(
        self,
        only_enabled: bool = True
    ) -> List[PipelineResult]:
        """
        运行所有启用的 Group 的处理管道（同步）
        
        Args:
            only_enabled: 是否只处理启用的 Group
            
        Returns:
            PipelineResult 列表
        """
        return asyncio.run(self.run_all_enabled(only_enabled))
    
    def process_group(
        self,
        group_id: str,
        force: bool = False,
        export_articles: bool = False
    ) -> PipelineResult:
        """
        处理单个 Group（同步便捷方法）
        
        Args:
            group_id: Group ID
            force: 强制模式
            export_articles: 导出文章列表
            
        Returns:
            PipelineResult 实例
        """
        return self.run_sync(group_id, force, export_articles)


# 全局默认实例
_default_service: Optional[PipelineService] = None


def get_pipeline_service(config_path: Optional[str] = None, db_path: Optional[str] = None) -> PipelineService:
    """
    获取 PipelineService 实例（支持单例）
    
    Args:
        config_path: 配置文件路径
        db_path: 数据库文件路径
        
    Returns:
        PipelineService 实例
    """
    global _default_service
    
    if _default_service is None:
        _default_service = PipelineService(config_path, db_path)
    
    return _default_service


async def run_pipeline(
    group_id: str,
    force: bool = False,
    export_articles: bool = False,
    db_path: Optional[str] = None
) -> PipelineResult:
    """
    便捷函数：运行处理管道
    
    Args:
        group_id: Group ID
        force: 强制模式
        export_articles: 导出文章列表
        db_path: 数据库路径
        
    Returns:
        PipelineResult 实例
    """
    service = get_pipeline_service(db_path=db_path)
    return await service.run(group_id, force, export_articles)


def run_pipeline_sync(
    group_id: str,
    force: bool = False,
    export_articles: bool = False,
    db_path: Optional[str] = None
) -> PipelineResult:
    """
    便捷函数：运行处理管道（同步）
    
    Args:
        group_id: Group ID
        force: 强制模式
        export_articles: 导出文章列表
        db_path: 数据库路径
        
    Returns:
        PipelineResult 实例
    """
    return asyncio.run(run_pipeline(group_id, force, export_articles, db_path))
