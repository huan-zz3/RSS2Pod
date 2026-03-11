"""
Database Service - 数据库服务封装

封装数据库的 CRUD 操作，提供统一的数据库访问接口。
"""

import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult
from database.models import DatabaseManager, Group, Article, SourceSummary, Episode, ProcessingState


class DatabaseService(BaseService):
    """
    数据库服务
    
    提供数据库相关的业务逻辑封装
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        super().__init__(config_path, db_path)
    
    # ========== Group 操作 ==========
    
    def get_group(self, group_id: str) -> ServiceResult:
        """
        获取 Group
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            group = self.db.get_group(group_id)
            if group:
                return ServiceResult(success=True, data=group)
            else:
                return ServiceResult(success=False, error_message=f"Group {group_id} 不存在")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def create_group(self, group: Group) -> ServiceResult:
        """
        创建 Group
        
        Args:
            group: Group 实例
            
        Returns:
            ServiceResult 实例
        """
        try:
            success = self.db.add_group(group)
            if success:
                return ServiceResult(success=True, data=group)
            else:
                return ServiceResult(success=False, error_message="创建 Group 失败")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def update_group(self, group: Group) -> ServiceResult:
        """
        更新 Group
        
        Args:
            group: Group 实例
            
        Returns:
            ServiceResult 实例
        """
        try:
            success = self.db.update_group(group)
            if success:
                return ServiceResult(success=True, data=group)
            else:
                return ServiceResult(success=False, error_message="更新 Group 失败")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def delete_group(self, group_id: str) -> ServiceResult:
        """
        删除 Group
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            success = self.db.delete_group(group_id)
            if success:
                return ServiceResult(success=True)
            else:
                return ServiceResult(success=False, error_message=f"删除 Group {group_id} 失败")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def get_all_groups(self, enabled_only: bool = False) -> ServiceResult:
        """
        获取所有 Group
        
        Args:
            enabled_only: 是否只获取已启用的 Group
            
        Returns:
            ServiceResult 实例
        """
        try:
            groups = self.db.get_all_groups(enabled_only=enabled_only)
            return ServiceResult(success=True, data=groups)
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    # ========== Article 操作 ==========
    
    def add_article(self, article: Article) -> ServiceResult:
        """
        添加 Article
        
        Args:
            article: Article 实例
            
        Returns:
            ServiceResult 实例
        """
        try:
            success = self.db.add_article(article)
            if success:
                return ServiceResult(success=True, data=article)
            else:
                return ServiceResult(success=False, error_message="添加 Article 失败")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def add_articles(self, articles: List[Article]) -> ServiceResult:
        """
        批量添加 Article
        
        Args:
            articles: Article 列表
            
        Returns:
            ServiceResult 实例
        """
        try:
            success_count = 0
            for article in articles:
                if self.db.add_article(article):
                    success_count += 1
            
            if success_count == len(articles):
                return ServiceResult(success=True, data={"count": success_count})
            elif success_count > 0:
                return ServiceResult(
                    success=True,
                    data={"count": success_count},
                    metadata={"partial": True, "total": len(articles)}
                )
            else:
                return ServiceResult(success=False, error_message="批量添加 Article 失败")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def get_article(self, article_id: str) -> ServiceResult:
        """
        获取 Article
        
        Args:
            article_id: Article ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            article = self.db.get_article(article_id)
            if article:
                return ServiceResult(success=True, data=article)
            else:
                return ServiceResult(success=False, error_message=f"Article {article_id} 不存在")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def get_articles_by_status(self, status: str, limit: int = 100) -> ServiceResult:
        """
        根据状态获取 Article 列表
        
        Args:
            status: 文章状态
            limit: 返回数量限制
            
        Returns:
            ServiceResult 实例
        """
        try:
            articles = self.db.get_articles_by_status(status, limit)
            return ServiceResult(success=True, data=articles, metadata={"count": len(articles)})
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def get_articles_by_source(self, source: str, status: Optional[str] = None) -> ServiceResult:
        """
        根据源获取 Article 列表
        
        Args:
            source: 源 URL
            status: 可选的文章状态
            
        Returns:
            ServiceResult 实例
        """
        try:
            articles = self.db.get_articles_by_source(source, status)
            return ServiceResult(success=True, data=articles, metadata={"count": len(articles)})
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def update_article_status(
        self,
        article_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> ServiceResult:
        """
        更新 Article 状态
        
        Args:
            article_id: Article ID
            status: 新状态
            error_message: 可选的错误信息
            
        Returns:
            ServiceResult 实例
        """
        try:
            self.db.update_article_status(article_id, status, error_message)
            return ServiceResult(success=True)
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def update_articles_status(
        self,
        article_ids: List[str],
        status: str,
        error_message: Optional[str] = None
    ) -> ServiceResult:
        """
        批量更新 Article 状态
        
        Args:
            article_ids: Article ID 列表
            status: 新状态
            error_message: 可选的错误信息
            
        Returns:
            ServiceResult 实例
        """
        try:
            for article_id in article_ids:
                self.db.update_article_status(article_id, status, error_message)
            return ServiceResult(success=True, data={"count": len(article_ids)})
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    # ========== Episode 操作 ==========
    
    def add_episode(self, episode: Episode) -> ServiceResult:
        """
        添加 Episode
        
        Args:
            episode: Episode 实例
            
        Returns:
            ServiceResult 实例
        """
        try:
            success = self.db.add_episode(episode)
            if success:
                return ServiceResult(success=True, data=episode)
            else:
                return ServiceResult(success=False, error_message="添加 Episode 失败")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def get_episode(self, episode_id: str) -> ServiceResult:
        """
        获取 Episode
        
        Args:
            episode_id: Episode ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            episode = self.db.get_episode(episode_id)
            if episode:
                return ServiceResult(success=True, data=episode)
            else:
                return ServiceResult(success=False, error_message=f"Episode {episode_id} 不存在")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def get_episodes_by_group(self, group_id: str, limit: int = 50) -> ServiceResult:
        """
        获取 Group 的 Episode 列表
        
        Args:
            group_id: Group ID
            limit: 返回数量限制
            
        Returns:
            ServiceResult 实例
        """
        try:
            episodes = self.db.get_episodes_by_group(group_id, limit)
            return ServiceResult(success=True, data=episodes, metadata={"count": len(episodes)})
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def get_starred_episodes(self) -> ServiceResult:
        """
        获取已收藏的 Episode 列表
        
        Returns:
            ServiceResult 实例
        """
        try:
            episodes = self.db.get_starred_episodes()
            return ServiceResult(success=True, data=episodes, metadata={"count": len(episodes)})
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def update_episode(self, episode: Episode) -> ServiceResult:
        """
        更新 Episode
        
        Args:
            episode: Episode 实例
            
        Returns:
            ServiceResult 实例
        """
        try:
            success = self.db.update_episode(episode)
            if success:
                return ServiceResult(success=True, data=episode)
            else:
                return ServiceResult(success=False, error_message="更新 Episode 失败")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    # ========== SourceSummary 操作 ==========
    
    def add_source_summary(self, summary: SourceSummary) -> ServiceResult:
        """
        添加 SourceSummary
        
        Args:
            summary: SourceSummary 实例
            
        Returns:
            ServiceResult 实例
        """
        try:
            success = self.db.add_source_summary(summary)
            if success:
                return ServiceResult(success=True, data=summary)
            else:
                return ServiceResult(success=False, error_message="添加 SourceSummary 失败")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    # ========== ProcessingState 操作 ==========
    
    def get_processing_state(self, group_id: str) -> ServiceResult:
        """
        获取 Group 的处理状态
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            state = self.db.get_processing_state(group_id)
            if state:
                return ServiceResult(success=True, data=state)
            else:
                return ServiceResult(success=False, error_message=f"Group {group_id} 的处理状态不存在")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    def update_processing_state(self, state: ProcessingState) -> ServiceResult:
        """
        更新处理状态
        
        Args:
            state: ProcessingState 实例
            
        Returns:
            ServiceResult 实例
        """
        try:
            success = self.db.update_processing_state(state)
            if success:
                return ServiceResult(success=True, data=state)
            else:
                return ServiceResult(success=False, error_message="更新处理状态失败")
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    # ========== 统计操作 ==========
    
    def get_stats(self) -> ServiceResult:
        """
        获取数据库统计信息
        
        Returns:
            ServiceResult 实例
        """
        try:
            stats = self.db.get_stats()
            return ServiceResult(success=True, data=stats)
        except Exception as e:
            return ServiceResult(success=False, error_message=str(e))
    
    # ========== 便捷方法 ==========
    
    def get_db_manager(self) -> DatabaseManager:
        """
        获取底层 DatabaseManager 实例
        
        Returns:
            DatabaseManager 实例
        """
        return self.db


# 全局单例
_database_service: Optional[DatabaseService] = None


def get_database_service(config_path: Optional[str] = None, db_path: Optional[str] = None) -> DatabaseService:
    """
    获取数据库服务实例
    
    Args:
        config_path: 配置文件路径
        db_path: 数据库文件路径
        
    Returns:
        DatabaseService 实例
    """
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService(config_path, db_path)
    return _database_service
