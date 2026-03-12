"""
Fever API 服务 - 封装 Fever API 相关操作
"""

import os
import sys
import hashlib
from typing import Optional, List, Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult


class FeverService(BaseService):
    """
    Fever API 服务
    
    提供 Fever API 相关的业务逻辑封装
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        super().__init__(config_path, db_path)
        self._client = None
    
    def _get_client(self, with_cache: bool = True):
        """获取 Fever API 客户端"""
        if self._client is None:
            from fetcher.fever_client import FeverClient, FeverCredentials
            
            fever_config = self.config.get('fever', {})
            username = fever_config.get('username', '')
            password = fever_config.get('password', '')
            api_key = hashlib.md5(f"{username}:{password}".encode()).hexdigest()
            
            credentials = FeverCredentials(
                api_url=fever_config.get('url', ''),
                api_key=api_key
            )
            
            if with_cache and self.db:
                self._client = FeverClient(credentials, db_path=self.db.db_path)
            else:
                self._client = FeverClient(credentials)
        
        return self._client
    
    def test_connection(self) -> ServiceResult:
        """
        测试 Fever API 连接
        
        Returns:
            ServiceResult 实例
        """
        try:
            client = self._get_client(with_cache=False)
            
            if client.test_auth():
                info = client._make_request({})
                return ServiceResult(
                    success=True,
                    data={
                        'last_refreshed_on_time': info.get('last_refreshed_on_time', 'unknown'),
                        'feeds_count': len(client.get_feeds())
                    }
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message='Fever API 认证失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def sync_feeds(self) -> ServiceResult:
        """
        同步订阅源列表到本地
        
        Returns:
            ServiceResult 实例
        """
        try:
            import json
            import time
            
            client = self._get_client(with_cache=False)
            feeds = client.get_feeds()
            
            # 保存订阅源到本地
            sources_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'sources.json'
            )
            sources_data = {
                "synced_at": time.time(),
                "sources": [
                    {
                        "id": str(feed.get('id', '')),
                        "title": feed.get('title', 'Unknown'),
                        "url": feed.get('url', '')
                    }
                    for feed in feeds
                ]
            }
            
            with open(sources_file, 'w', encoding='utf-8') as f:
                json.dump(sources_data, f, indent=2, ensure_ascii=False)
            
            return ServiceResult(
                success=True,
                data={
                    'feeds_synced': len(feeds),
                    'saved_to': sources_file
                }
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def sync_articles(self, limit: int = 1500) -> ServiceResult:
        """
        同步文章到本地缓存
        
        Args:
            limit: 最大同步文章数量
            
        Returns:
            ServiceResult 实例
        """
        try:
            from services.pipeline.group_processor import sync_fever_cache
            
            result = sync_fever_cache(db_path=self.db.db_path, limit=limit)
            
            if result.success:
                return ServiceResult(
                    success=True,
                    data={
                        'items_synced': result.items_synced,
                        'new_items': result.new_items,
                        'updated_items': result.updated_items
                    }
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message=result.error_message
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def mark_as_read(self, item_ids: List[int]) -> ServiceResult:
        """
        标记文章为已读
        
        Args:
            item_ids: 文章 ID 列表
            
        Returns:
            ServiceResult 实例
        """
        try:
            client = self._get_client(with_cache=True)
            result = client.mark_as_read(item_ids)
            
            if result:
                return ServiceResult(
                    success=True,
                    data={'marked_count': len(item_ids)}
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message='标记已读失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def mark_as_saved(self, item_id: int) -> ServiceResult:
        """
        收藏文章
        
        Args:
            item_id: 文章 ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            client = self._get_client(with_cache=True)
            result = client.save_item(item_id)
            
            if result:
                return ServiceResult(
                    success=True,
                    data={'saved_item_id': item_id}
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message='收藏失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def mark_as_unread(self, item_ids: List[int]) -> ServiceResult:
        """
        标记文章为未读（仅本地缓存）
        
        Args:
            item_ids: 文章 ID 列表
            
        Returns:
            ServiceResult 实例
        """
        try:
            cursor = self.db.conn.cursor()
            placeholders = ','.join('?' * len(item_ids))
            cursor.execute(f'UPDATE fever_cache SET is_read = 0 WHERE id IN ({placeholders})', item_ids)
            self.db.conn.commit()
            
            return ServiceResult(
                success=True,
                data={'marked_count': len(item_ids)}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_cache_stats(self) -> ServiceResult:
        """
        获取 Fever 缓存统计信息
        
        Returns:
            ServiceResult 实例
        """
        try:
            from services.pipeline.group_processor import get_fever_cache_stats
            
            stats = get_fever_cache_stats(self.db.db_path)
            
            if 'error' in stats:
                return ServiceResult(
                    success=False,
                    error_message=stats['error']
                )
            
            return ServiceResult(
                success=True,
                data=stats
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_cache_articles(self, limit: int = 50, unread: bool = True, feed_id: Optional[int] = None) -> ServiceResult:
        """
        从缓存获取文章列表
        
        Args:
            limit: 最大返回数量
            unread: 是否只获取未读文章
            feed_id: 可选，指定订阅源 ID
            
        Returns:
            ServiceResult 实例
        """
        try:
            if unread:
                items = self.db.get_fever_cache_unread_items(feed_id=feed_id, limit=limit)
            else:
                items = self.db.get_fever_cache_items(limit=limit)
            
            return ServiceResult(
                success=True,
                data=[item.to_dict() for item in items],
                metadata={'count': len(items)}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_cache_feeds(self) -> ServiceResult:
        """
        从缓存获取订阅源列表（有文章的订阅源）
        
        Returns:
            ServiceResult 实例
        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT DISTINCT feed_id FROM fever_cache ORDER BY feed_id')
            feed_ids = [row[0] for row in cursor.fetchall()]
            
            # 尝试从 sources.json 获取订阅源名称
            sources_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'sources.json'
            )
            sources_map = {}
            if os.path.exists(sources_file):
                import json
                with open(sources_file, 'r', encoding='utf-8') as f:
                    sources_data = json.load(f)
                    for source in sources_data.get('sources', []):
                        sources_map[str(source.get('id', ''))] = source.get('title', 'Unknown')
            
            feeds = [
                {'feed_id': fid, 'name': sources_map.get(str(fid), '(未知)')}
                for fid in feed_ids
            ]
            
            return ServiceResult(
                success=True,
                data=feeds,
                metadata={'count': len(feeds)}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def fetch_articles(
        self,
        rss_sources: List[str],
        since_id: str = None,
        force: bool = False,
        limit: int = 1500
    ) -> ServiceResult:
        """
        从 Fever API 获取文章
        
        Args:
            rss_sources: RSS 源 URL 列表
            since_id: 上次同步的 cursor
            force: 是否强制获取最新文章
            limit: 最大获取数量
            
        Returns:
            ServiceResult 实例，包含 articles, fetch_cursor
        """
        try:
            
            # 获取 Fever 客户端
            client = self._get_client(with_cache=True)
            client.get_feeds()
            
            # 构建 feed_map
            feed_map_result = self.get_feed_map(rss_sources)
            if not feed_map_result.success:
                return feed_map_result
            
            feed_map = feed_map_result.data
            target_feed_ids = set(feed_map.values())
            
            if not target_feed_ids:
                return ServiceResult(
                    success=True,
                    data={'articles': [], 'fetch_cursor': since_id}
                )
            
            # 转换 since_id 为整数
            since_id_int = int(since_id) if since_id else None
            
            if force:
                since_id_int = None
            
            # 获取文章
            fetch_limit = limit if since_id_int is None else min(limit, 100)
            all_items = client.get_items(since_id=since_id_int, limit=fetch_limit)
            
            # 按 feed_id 过滤
            filtered_items = [
                item for item in all_items 
                if item.get('feed_id') in target_feed_ids
            ]
            
            # 如果 force 模式，只取最新的3篇
            if force and len(filtered_items) > 3:
                filtered_items.sort(key=lambda x: int(x.get('created_on_time', 0)), reverse=True)
                filtered_items = filtered_items[:3]
            
            # 生成新的 cursor
            if filtered_items:
                max_item_id = max(int(item.get('id', 0)) for item in filtered_items)
                new_cursor = str(max_item_id)
            else:
                new_cursor = since_id
            
            return ServiceResult(
                success=True,
                data={
                    'articles': filtered_items,
                    'fetch_cursor': new_cursor,
                    'feed_map': feed_map
                },
                metadata={
                    'count': len(filtered_items),
                    'since_id': since_id,
                    'force': force
                }
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_feed_map(self, rss_sources: List[str]) -> ServiceResult:
        """
        获取 RSS 源 URL 到 Fever feed_id 的映射
        
        Args:
            rss_sources: RSS 源 URL 列表
            
        Returns:
            ServiceResult 实例，包含 feed_map (dict: url -> feed_id)
        """
        try:
            client = self._get_client(with_cache=False)
            feeds = client.get_feeds()
            
            if feeds is None:
                return ServiceResult(
                    success=False,
                    error_message="无法获取订阅源列表"
                )
            
            feed_map = {}
            
            # 精确匹配
            for source_url in rss_sources:
                for feed in feeds:
                    if feed.get('url') == source_url:
                        feed_map[source_url] = int(feed.get('id'))
                        break
            
            # 模糊匹配（对于未匹配的）
            import re
            for source_url in rss_sources:
                if source_url in feed_map:
                    continue
                
                # 提取域名
                domain_match = re.search(r'://([^/]+)', source_url)
                if not domain_match:
                    continue
                
                target_domain = domain_match.group(1)
                
                for feed in feeds:
                    feed_url = feed.get('url', '')
                    feed_domain = re.search(r'://([^/]+)', feed_url)
                    if feed_domain and feed_domain.group(1) == target_domain:
                        feed_map[source_url] = int(feed.get('id'))
                        break
            
            return ServiceResult(
                success=True,
                data=feed_map,
                metadata={'count': len(feed_map), 'total_sources': len(rss_sources)}
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def _convert_items_to_articles(
        self,
        items: List[Dict],
        feed_map: Dict[str, int],
        group_id: str
    ) -> List:  # noqa: F821 - Article is imported at runtime
        """
        将 Fever API 返回的 items 转换为 Article 模型实例
        
        Args:
            items: Fever API 返回的文章列表
            feed_map: source_url -> feed_id 映射
            group_id: Group ID
            
        Returns:
            Article 实例列表
        """
        import html
        import re
        import hashlib
        from datetime import datetime
        from database.models import Article
        
        all_articles = []
        
        # 构建 feed_id -> source_url 的反向映射
        fid_to_url = {fid: url for url, fid in feed_map.items()}
        
        for item in items:
            feed_id = item.get('feed_id')
            source_url = fid_to_url.get(feed_id)
            
            if not source_url:
                continue
            
            try:
                title = item.get('title', 'Untitled')
                link = item.get('url', item.get('link', ''))
                published = datetime.fromtimestamp(
                    int(item.get('created_on_time', 0))
                ).isoformat()
                content = item.get('content', '')
                
                # 提取纯文本内容
                text_content = html.unescape(content)
                text_content = re.sub(r'<[^>]+>', '', text_content)
                
                # 生成 article ID
                article_id = f"art-{hashlib.md5(f'{source_url}-{title}'.encode()).hexdigest()[:12]}"
                
                article = Article(
                    id=article_id,
                    title=title,
                    source=source_url,
                    source_url=source_url,
                    link=link,
                    published=published,
                    content=content,
                    text_content=text_content[:10000],
                    status='pending',
                    group_id=group_id
                )
                
                all_articles.append(article)
                
            except Exception as e:
                self.logger.error(f"转换文章失败 ({item.get('id')}): {e}")
                continue
        
        return all_articles
    
    def fetch_articles_for_group(
        self,
        rss_sources: List[str],
        group_id: str,
        since_id: Optional[str] = None,
        force: bool = False,
        limit: int = 1500
    ) -> ServiceResult:
        """
        获取指定 Group 的文章并转换为 Article 模型
        
        Args:
            rss_sources: RSS 源 URL 列表
            group_id: Group ID
            since_id: 上次同步的 cursor
            force: 是否强制获取最新文章
            limit: 最大获取数量
            
        Returns:
            ServiceResult 实例，包含:
            - articles: List[Article] - 转换后的 Article 实例
            - fetch_cursor: str - 下次拉取的 cursor
            - feed_map: Dict - source_url -> feed_id 映射
        """
        try:
            # 调用已有的 fetch_articles 方法获取原始 items
            fetch_result = self.fetch_articles(
                rss_sources=rss_sources,
                since_id=since_id,
                force=force,
                limit=limit
            )
            
            if not fetch_result.success:
                return fetch_result
            
            raw_items = fetch_result.data.get('articles', [])
            feed_map = fetch_result.data.get('feed_map', {})
            fetch_cursor = fetch_result.data.get('fetch_cursor', since_id)
            
            if not raw_items:
                return ServiceResult(
                    success=True,
                    data={
                        'articles': [],
                        'fetch_cursor': fetch_cursor,
                        'feed_map': feed_map
                    }
                )
            
            # 转换为 Article 模型
            articles = self._convert_items_to_articles(
                items=raw_items,
                feed_map=feed_map,
                group_id=group_id
            )
            
            return ServiceResult(
                success=True,
                data={
                    'articles': articles,
                    'fetch_cursor': fetch_cursor,
                    'feed_map': feed_map
                },
                metadata={
                    'count': len(articles),
                    'raw_items_count': len(raw_items)
                }
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def close(self):
        """关闭服务，释放资源"""
        if self._client and self._client.cache_manager:
            self._client.cache_manager.close()
        super().close()
