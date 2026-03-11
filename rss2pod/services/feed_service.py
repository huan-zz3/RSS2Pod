"""
RSS Feed 服务 - 封装 RSS Feed 生成相关操作

本服务作为 FeedManager 的 Facade 代理，所有操作都委托给 FeedManager 处理，
以确保与 pipeline 的兼容性。
"""

import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult


class FeedService(BaseService):
    """
    RSS Feed 服务
    
    提供 RSS Feed 生成和获取相关的业务逻辑封装。
    本服务作为 FeedManager 的 Facade 代理，统一委托处理。
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        super().__init__(config_path, db_path)
        self._config = None
        self._feed_manager = None
    
    def _get_config(self) -> Dict[str, Any]:
        """获取配置"""
        if self._config is None:
            from .config_service import load_config
            self._config = load_config()
        return self._config
    
    def _get_db(self):
        """获取数据库实例"""
        if self._db is None:
            from database.models import init_db
            config = self._get_config()
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                config.get('db_path', 'rss2pod.db')
            )
            self._db = init_db(db_path)
        return self._db
    
    def _get_feed_manager(self):
        """
        获取 FeedManager 实例
        
        Returns:
            FeedManager 实例
        """
        if self._feed_manager is None:
            from feed.feed_manager import FeedManager
            
            # 计算 feed 目录路径
            feed_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'data', 'feeds'
            )
            self._feed_manager = FeedManager(base_dir=feed_dir)
        return self._feed_manager
    
    def _get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        config = self._get_config()
        return config.get('server', {})
    
    def get_group_episodes(self, group_id: str, limit: int = 50) -> List[Any]:
        """
        获取 Group 的 Episodes
        
        Args:
            group_id: Group ID
            limit: 返回数量限制
            
        Returns:
            Episode 列表
        """
        # 优先使用 FeedManager 的数据（与 pipeline 一致）
        manager = self._get_feed_manager()
        episodes = manager.get_episodes(group_id, limit)
        if episodes:
            return episodes
        
        # 降级为数据库查询
        db = self._get_db()
        return db.get_episodes_by_group(group_id, limit)
    
    def get_group(self, group_id: str) -> Optional[Any]:
        """
        获取 Group 信息
        
        Args:
            group_id: Group ID
            
        Returns:
            Group 对象
        """
        # 优先使用 FeedManager 的数据（与 pipeline 一致）
        manager = self._get_feed_manager()
        group = manager.get_group(group_id)
        if group:
            return group
        
        # 降级为数据库查询
        db = self._get_db()
        return db.get_group(group_id)
    
    def create_group(self, group_id: str, title: str, link: str, description: str, **kwargs) -> ServiceResult:
        """
        创建 Podcast Group
        
        Args:
            group_id: Group ID
            title: 标题
            link: 链接
            description: 描述
            **kwargs: 其他参数 (language, author, category 等)
            
        Returns:
            ServiceResult
        """
        try:
            manager = self._get_feed_manager()
            
            # 使用 FeedManager 创建 group
            group = manager.create_group(
                group_id=group_id,
                title=title,
                link=link,
                description=description,
                **kwargs
            )
            
            return ServiceResult(
                success=True,
                data={
                    'group_id': group.id,
                    'title': group.title
                }
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def add_episode(self, group_id: str, episode_data: Dict[str, Any]) -> ServiceResult:
        """
        添加 Episode 到 Feed
        
        Args:
            group_id: Group ID
            episode_data: Episode 数据字典
            
        Returns:
            ServiceResult
        """
        try:
            from feed.feed_manager import Episode as FeedEpisode
            
            # 从字典创建 Episode
            episode = FeedEpisode(
                id=episode_data.get('id'),
                title=episode_data.get('title'),
                link=episode_data.get('link'),
                audio_url=episode_data.get('audio_url', ''),
                audio_length=episode_data.get('audio_length', 0),
                audio_type=episode_data.get('audio_type', 'audio/mpeg'),
                description=episode_data.get('description', ''),
                content_html=episode_data.get('content_html', ''),
                pub_date=episode_data.get('pub_date', datetime.now().isoformat()),
                duration=episode_data.get('duration', ''),
                episode_number=episode_data.get('episode_number'),
                season_number=episode_data.get('season_number'),
                explicit=episode_data.get('explicit', False),
                image=episode_data.get('image', ''),
                keywords=episode_data.get('keywords')
            )
            
            # 使用 FeedManager 添加 episode
            manager = self._get_feed_manager()
            manager.add_episode(group_id, episode)
            
            return ServiceResult(
                success=True,
                data={
                    'episode_id': episode.id,
                    'group_id': group_id
                }
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def generate_feed(self, group_id: str) -> ServiceResult:
        """
        生成 RSS Feed XML 并写入文件
        
        与 generate_feed_xml() 的区别：
        - generate_feed_xml(): 仅返回 XML 字符串
        - generate_feed(): 返回 XML 并写入文件
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult，包含 feed 路径
        """
        try:
            manager = self._get_feed_manager()
            
            # 检查 group 是否存在
            group = manager.get_group(group_id)
            if not group:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 不存在'
                )
            
            # 检查是否有 episodes
            episodes = manager.get_episodes(group_id)
            if not episodes:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 没有 Episode'
                )
            
            # 使用 FeedManager 生成 feed（会写入文件）
            rss_content = manager.generate_feed(group_id)
            feed_path = manager.get_feed_url(group_id)
            
            return ServiceResult(
                success=True,
                data={
                    'feed_path': feed_path,
                    'rss_content': rss_content
                }
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def generate_feed_xml(self, group_id: str) -> ServiceResult:
        """
        生成 RSS Feed XML
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例，包含 RSS XML 字符串
        """
        try:
            # 获取 Group 信息
            group = self.get_group(group_id)
            if not group:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 不存在'
                )
            
            # 获取 Episodes
            episodes = self.get_group_episodes(group_id)
            if not episodes:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 没有 Episode'
                )
            
            # 获取配置
            config = self._get_config()
            server_config = config.get('server', {})
            base_url = server_config.get('base_url', 'http://localhost:8080')
            
            # 生成 RSS XML
            xml = self._build_rss_xml(group, episodes, base_url)
            
            return ServiceResult(
                success=True,
                data=xml
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def _build_rss_xml(self, group: Any, episodes: List[Any], base_url: str) -> str:
        """
        构建 RSS XML
        
        使用 python-feedgen 库生成 RSS Feed
        
        Args:
            group: Group 对象
            episodes: Episode 列表
            base_url: 服务器基础 URL
            
        Returns:
            RSS XML 字符串
        """
        from rss2pod.feed.feed_generator import PodcastFeedGenerator
        
        # 计算 media 目录的绝对路径
        media_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'media'
        )
        
        # 创建 PodcastFeedGenerator（内部已加载 load_extension('podcast')）
        fg = PodcastFeedGenerator(
            title=group.name,
            link=base_url,
            description=group.description or f'{group.name} Podcast Feed',
            language='zh-cn',
            author='RSS2Pod'
        )
        
        # 添加 episodes
        for ep in episodes:
            # 计算音频 URL
            audio_url = None
            audio_length = 0
            if ep.audio_path and os.path.exists(ep.audio_path):
                audio_relative_path = ep.audio_path
                if ep.audio_path.startswith(media_dir):
                    audio_relative_path = ep.audio_path[len(media_dir):].lstrip('/')
                audio_url = f'{base_url}/media/{audio_relative_path}'
                audio_length = os.path.getsize(ep.audio_path)
            
            # 计算发布时间（需要带时区）
            pub_date = None
            if ep.published_at:
                try:
                    pub_date = datetime.fromisoformat(ep.published_at)
                    # 确保有时区信息
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                except:
                    pub_date = datetime.fromisoformat(ep.created_at)
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
            else:
                pub_date = datetime.fromisoformat(ep.created_at)
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            
            fg.add_episode(
                episode_id=ep.id,
                title=ep.title or f'Episode {ep.episode_number}',
                link=audio_url or base_url,
                audio_url=audio_url,
                audio_length=audio_length,
                description=f'Episode {ep.episode_number}',
                pub_date=pub_date,
                duration=str(ep.audio_duration) if ep.audio_duration else None,
                episode_number=ep.episode_number
            )
        
        return fg.rss_str(pretty=True)
    
    def get_feed_url(self, group_id: str) -> ServiceResult:
        """
        获取 Group 的 RSS Feed URL
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例，包含 Feed URL
        """
        try:
            config = self._get_config()
            server_config = config.get('server', {})
            base_url = server_config.get('base_url', 'http://localhost:8080')
            
            feed_url = f'{base_url}/feeds/{group_id}.xml'
            
            return ServiceResult(
                success=True,
                data=feed_url
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def list_groups(self) -> ServiceResult:
        """
        获取所有 Group 列表
        
        Returns:
            ServiceResult 实例
        """
        try:
            db = self._get_db()
            groups = db.get_all_groups()
            
            group_list = []
            for group in groups:
                group_list.append({
                    'id': group.id,
                    'name': group.name,
                    'description': group.description,
                    'enabled': group.enabled,
                    'episode_count': len(db.get_episodes_by_group(group.id))
                })
            
            return ServiceResult(
                success=True,
                data=group_list
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def trigger_group(self, group_id: str, verbose: bool = False) -> ServiceResult:
        """
        触发生成指定 Group 的播客
        
        Args:
            group_id: Group ID
            verbose: 是否显示详细日志（DEBUG 级别）
            
        Returns:
            ServiceResult 实例
        """
        try:
            from services.pipeline.group_processor import process_group_sync
            from orchestrator.logging_config import setup_logging
            
            # 设置日志级别
            log_level = "DEBUG" if verbose else "INFO"
            setup_logging(level=log_level)
            
            config = self._get_config()
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                config.get('db_path', 'rss2pod.db')
            )
            
            # 异步触发生成（不等待完成）
            import threading
            thread = threading.Thread(
                target=process_group_sync,
                args=(group_id, db_path)
            )
            thread.start()
            
            return ServiceResult(
                success=True,
                data={
                    'group_id': group_id,
                    'message': '已触发生成任务'
                }
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def close(self):
        """关闭数据库连接"""
        if self._db:
            self._db.close()
            self._db = None


def generate_feed_xml(group_id: str) -> ServiceResult:
    """
    便捷函数：生成 RSS Feed XML
    
    Args:
        group_id: Group ID
        
    Returns:
        ServiceResult 实例
    """
    service = FeedService()
    return service.generate_feed_xml(group_id)


def get_feed_url(group_id: str) -> ServiceResult:
    """
    便捷函数：获取 RSS Feed URL
    
    Args:
        group_id: Group ID
        
    Returns:
        ServiceResult 实例
    """
    service = FeedService()
    return service.get_feed_url(group_id)


def list_groups() -> ServiceResult:
    """
    便捷函数：获取 Group 列表
    
    Returns:
        ServiceResult 实例
    """
    service = FeedService()
    return service.list_groups()


def trigger_group(group_id: str, verbose: bool = False) -> ServiceResult:
    """
    便捷函数：触发生成
    
    Args:
        group_id: Group ID
        verbose: 是否
    Returns:
        ServiceResult 实例
    """
    service = FeedService()
    return service.trigger_group(group_id)
