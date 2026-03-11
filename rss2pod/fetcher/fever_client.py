"""
Fever API Client - 用于与 Fever API 兼容的 RSS 阅读器交互
参考：https://feedafever.com/api

支持本地缓存模式：读取操作从 SQLite 缓存获取，写入操作同时更新缓存和远端 API
"""

import requests
import hashlib
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import json


@dataclass
class FeverCredentials:
    """Fever API 认证信息"""
    api_url: str  # Fever API 基础 URL，如 https://your-server.com/fever
    api_key: str  # API Key（MD5 哈希：email:password）
    

class FeverClient:
    """Fever API 客户端（支持本地缓存）"""
    
    def __init__(self, credentials: FeverCredentials, db_path: Optional[str] = None):
        """
        初始化 Fever 客户
        
        Args:
            credentials: Fever API 认证信息
            db_path: 可选，缓存数据库路径。不提供则不使用缓存（直接访问 API）
        """
        self.api_url = credentials.api_url.rstrip('/')
        self.api_key = credentials.api_key
        self.session = requests.Session()
        
        # 初始化缓存管理器
        self.cache_manager = None
        if db_path:
            from .fever_cache import FeverCacheManager
            self.cache_manager = FeverCacheManager(db_path)
        
    def _make_request(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        发送 API 请求
        
        Fever API 规范：
        - 读取数据时，参数（如 feeds, items, groups）放在 URL query string 中
        - api_key 必须通过 POST 方式提交
        
        Args:
            params: 请求参数（如 {'feeds': ''}, {'items': ''}）
            
        Returns:
            API 响应字典
        """
        # 构建 URL：将 API 参数放在 query string 中
        # Fever API 格式：base_url?api&feeds 或 base_url?api&items 等
        # 注意：TT-RSS Fever 插件要求 api_key 也放在 URL 中
        url = f"{self.api_url}?api&api_key={self.api_key}"
        if params:
            # 将参数转换为 URL query string 格式
            for key, value in params.items():
                if value == '' or value is None:
                    url = f"{url}&{key}"
                else:
                    url = f"{url}&{key}={value}"
        
        # 使用 GET 请求（TT-RSS Fever 插件支持 GET 方式）
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get('auth') != 1:
            raise Exception("Fever API 认证失败")
            
        return result
    
    def _post_request(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        发送 POST API 请求
        
        Args:
            params: 请求参数
            
        Returns:
            API 响应字典
        """
        default_params = {'api_key': self.api_key}
        if params:
            default_params.update(params)
            
        response = self.session.post(self.api_url, data=default_params, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        if result.get('auth') != 1:
            raise Exception("Fever API 认证失败")
            
        return result
    
    @staticmethod
    def generate_api_key(email: str, password: str) -> str:
        """
        生成 Fever API Key
        
        Args:
            email: 账户邮箱
            password: 账户密码
            
        Returns:
            MD5 哈希的 API Key
        """
        api_string = f"{email}:{password}"
        return hashlib.md5(api_string.encode('utf-8')).hexdigest()
    
    def test_auth(self) -> bool:
        """
        测试 API 认证
        
        Returns:
            认证成功返回 True
        """
        try:
            result = self._make_request()
            return result.get('auth') == 1
        except Exception:
            return False
    
    def get_feeds(self) -> List[Dict[str, Any]]:
        """
        获取所有订阅源
        
        Returns:
            订阅源列表
        """
        result = self._make_request({'feeds': ''})
        return result.get('feeds', [])
    
    def get_groups(self) -> List[Dict[str, Any]]:
        """
        获取订阅源分组
        
        Returns:
            分组列表
        """
        result = self._make_request({'groups': ''})
        return result.get('groups', [])
    
    def sync_cache(self, limit: int = 1500) -> 'SyncResult':
        """
        从远端 Fever API 同步数据到本地缓存
        
        Args:
            limit: 最大同步文章数量
            
        Returns:
            SyncResult 实例
        """
        if not self.cache_manager:
            from .fever_cache import SyncResult
            return SyncResult(success=False, error_message="缓存未初始化")
        return self.cache_manager.sync_items(self, limit)
    
    def get_items(self, 
                  with_ids: Optional[List[int]] = None,
                  since_id: Optional[int] = None,
                  max_id: Optional[int] = None,
                  limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取文章列表 - 从缓存获取
        
        参数签名保持不变，实现改为从缓存查询。
        如果缓存未初始化，则降级为直接访问 API。
        
        Args:
            with_ids: 指定文章 ID 列表
            since_id: 获取此 ID 之后的文章
            max_id: 获取此 ID 之前的文章
            limit: 最大返回数量
            
        Returns:
            文章列表
        """
        # 优先从缓存获取
        if self.cache_manager:
            # with_ids 模式：逐个获取
            if with_ids:
                items = []
                for item_id in with_ids:
                    cache_item = self.cache_manager.get_item_by_id(item_id)
                    if cache_item:
                        items.append(cache_item.to_dict())
                return items
            
            # 普通查询模式
            cache_items = self.cache_manager.get_items(
                since_id=since_id, max_id=max_id, limit=limit
            )
            return [item.to_dict() for item in cache_items]
        
        # 降级：直接调用远端 API（向后兼容）
        params = {'items': ''}
        
        if with_ids:
            params['with_ids'] = ','.join(map(str, with_ids))
        if since_id:
            params['since_id'] = since_id
        if max_id:
            params['max_id'] = max_id
            
        params['limit'] = min(limit, 50)
        
        result = self._make_request(params)
        return result.get('items', [])
    
    def get_feed_items(self, 
                       feed_id: int, 
                       limit: int = 50,
                       since_id: Optional[int] = None,
                       max_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取指定订阅源的文章（支持增量获取）- 从缓存获取
        
        Args:
            feed_id: 订阅源 ID
            limit: 最大返回数量
            since_id: 获取此 ID 之后的文章（增量获取用）
            max_id: 获取此 ID 之前的文章
            
        Returns:
            文章列表
        """
        # 优先从缓存获取
        if self.cache_manager:
            cache_items = self.cache_manager.get_items(
                since_id=since_id, max_id=max_id, feed_id=feed_id, limit=limit
            )
            return [item.to_dict() for item in cache_items]
        
        # 降级：直接调用远端 API（向后兼容）
        # Fever API 的 items 接口可能不支持 feed_id 参数
        # 先获取所有 items（或使用 since_id/max_id 过滤），然后在客户端过滤
        params = {'items': ''}
        
        if since_id:
            params['since_id'] = since_id
        if max_id:
            params['max_id'] = max_id
            
        params['limit'] = min(limit, 50)
        
        result = self._make_request(params)
        all_items = result.get('items', [])
        
        # 在客户端过滤指定 feed_id 的文章
        return [item for item in all_items if item.get('feed_id') == feed_id]
    
    def get_unread_items(self, with_feed_id: Optional[int] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取所有未读文章 - 从缓存获取
        
        Args:
            with_feed_id: 可选，只获取指定 feed 的未读文章
            limit: 可选，限制返回文章数量
            
        Returns:
            未读文章列表
        """
        # 优先从缓存获取
        if self.cache_manager:
            cache_items = self.cache_manager.get_unread_items(
                feed_id=with_feed_id, limit=limit
            )
            return [item.to_dict() for item in cache_items]
        
        # 降级：直接调用远端 API（向后兼容）
        # 1. 获取未读文章 ID 列表
        result = self._make_request({'unread_item_ids': ''})
        unread_ids_str = result.get('unread_item_ids', '')
        
        if not unread_ids_str:
            return []
        
        # 转换为 ID 列表
        if isinstance(unread_ids_str, str):
            unread_ids = [int(x) for x in unread_ids_str.split(',') if x.strip()]
        else:
            unread_ids = unread_ids_str
        
        if not unread_ids:
            return []
        
        # 如果指定了 limit，只取前 limit 个 ID
        if limit:
            unread_ids = unread_ids[:limit]
        
        # 2. 分批获取文章详情（每次最多 50 个）
        all_items = []
        for i in range(0, len(unread_ids), 50):
            batch_ids = unread_ids[i:i+50]
            try:
                items = self.get_items(with_ids=batch_ids)
                
                # 如果指定了 feed_id，在客户端过滤
                if with_feed_id:
                    items = [item for item in items if item.get('feed_id') == with_feed_id]
                
                all_items.extend(items)
            except Exception as e:
                # 如果某一批次失败，记录错误但继续处理
                print(f"警告：获取批次 {batch_ids} 失败：{e}")
                continue
        
        return all_items
    
    def get_feed_items_by_iteration(self, 
                                    feed_id: int, 
                                    limit: int = 50,
                                    since_id: Optional[int] = None,
                                    unread_only: bool = False) -> List[Dict[str, Any]]:
        """
        通过迭代方式获取指定订阅源的文章 - 仅从缓存获取
        
        注意：此方法不会访问远端 API。如果缓存未初始化，将抛出异常。
        请先运行 `rss2pod fever sync` 同步数据到本地缓存。
        
        Args:
            feed_id: 订阅源 ID
            limit: 最大返回数量
            since_id: 从指定 ID 之后开始获取（用于增量同步）
            unread_only: 只获取未读文章
            
        Returns:
            文章列表（已按时间倒序排列）
            
        Raises:
            RuntimeError: 当缓存未初始化时抛出
        """
        if not self.cache_manager:
            raise RuntimeError(
                "缓存未初始化，无法获取文章。"
                "请先运行：rss2pod fever sync --articles\n"
                "该命令会从 Fever API 同步文章到本地缓存，之后才能查看和操作文章。"
            )
        
        # 从缓存获取
        if unread_only:
            cache_items = self.cache_manager.get_unread_items(
                feed_id=feed_id, limit=limit
            )
        else:
            cache_items = self.cache_manager.get_items(
                since_id=since_id, feed_id=feed_id, limit=limit
            )
        items = [item.to_dict() for item in cache_items]
        items.sort(key=lambda x: x.get('created_on_time', 0) or 0, reverse=True)
        return items[:limit]
    
    def mark_as_read(self, item_ids: List[int]) -> bool:
        """
        标记文章为已读 - 同时更新缓存和远端 API
        
        Args:
            item_ids: 文章 ID 列表
            
        Returns:
            操作是否成功
        """
        # 先更新缓存
        if self.cache_manager:
            self.cache_manager.mark_as_read(item_ids)
        
        # 再发送到远端 API
        params = {
            'mark': 'items',
            'as': 'read',
            'ids': ','.join(map(str, item_ids))
        }
        
        result = self._post_request(params)
        return result.get('saved') == 1
    
    def mark_feed_as_read(self, feed_id: int, before_id: Optional[int] = None) -> bool:
        """
        标记整个订阅源为已读 - 同时更新缓存和远端 API
        
        Args:
            feed_id: 订阅源 ID
            before_id: 标记此 ID 之前的所有文章
            
        Returns:
            操作是否成功
        """
        # 先更新缓存
        if self.cache_manager and before_id:
            self.cache_manager.mark_feed_as_read(feed_id, before_id)
        
        # 再发送到远端 API
        params = {
            'mark': 'feed',
            'as': 'read',
            'id': feed_id
        }
        
        if before_id:
            params['before'] = before_id
            
        result = self._post_request(params)
        return result.get('saved') == 1
    
    def save_item(self, item_id: int) -> bool:
        """
        收藏文章 - 同时更新缓存和远端 API
        
        Args:
            item_id: 文章 ID
            
        Returns:
            操作是否成功
        """
        # 先更新缓存
        if self.cache_manager:
            self.cache_manager.save_item(item_id)
        
        # 再发送到远端 API
        params = {
            'save': 'item',
            'id': item_id
        }
        
        result = self._post_request(params)
        return result.get('saved') == 1
    
    def get_unread_count(self) -> Dict[str, int]:
        """
        获取未读文章数量 - 从缓存获取
        
        Returns:
            包含未读数量的字典
        """
        # 优先从缓存获取
        if self.cache_manager:
            unread_ids = self.cache_manager.get_unread_ids()
            return {'unread_count': len(unread_ids)}
        
        # 降级：直接调用远端 API
        result = self._make_request({'unread_item_ids': ''})
        unread_ids = result.get('unread_item_ids', [])
        
        if isinstance(unread_ids, str):
            unread_list = [int(x) for x in unread_ids.split(',') if x.strip()]
        else:
            unread_list = unread_ids
            
        return {'unread_count': len(unread_list)}


# 使用示例
if __name__ == '__main__':
    # 示例：如何生成 API Key 并使用客户端
    # api_key = FeverClient.generate_api_key('your@email.com', 'your_password')
    # credentials = FeverCredentials(
    #     api_url='https://your-server.com/fever',
    #     api_key=api_key
    # )
    # client = FeverClient(credentials)
    # 
    # # 获取所有订阅源
    # feeds = client.get_feeds()
    # print(f"找到 {len(feeds)} 个订阅源")
    # 
    # # 获取最新文章
    # items = client.get_items(limit=10)
    # for item in items:
    #     print(f"- {item.get('title')}")
    pass
