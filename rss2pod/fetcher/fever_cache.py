#!/usr/bin/env python3
"""
Fever API 缓存管理器 - 管理 SQLite 缓存表
提供文章的增删改查和状态更新功能
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass
import sys
import os

# 添加父目录到路径以便导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import FeverCacheItem


@dataclass
class FeverCacheMeta:
    """缓存元数据"""
    key: str                   # 元数据键（如 'last_sync_time', 'total_items'）
    value: str                 # 元数据值
    updated_at: str            # 更新时间（ISO 格式）


@dataclass
class SyncResult:
    """缓存同步结果"""
    success: bool
    items_synced: int = 0      # 同步的文章数量
    new_items: int = 0         # 新增的文章数量
    updated_items: int = 0     # 更新的文章数量
    error_message: Optional[str] = None


class FeverCacheManager:
    """Fever API 缓存管理器"""
    
    def __init__(self, db_path: str):
        """
        初始化数据库连接
        
        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """创建缓存表（如果不存在）"""
        cursor = self.conn.cursor()
        
        # 创建 fever_cache 表
        cursor.execute('''CREATE TABLE IF NOT EXISTS fever_cache (
            id INTEGER PRIMARY KEY,
            feed_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            author TEXT DEFAULT '',
            html TEXT,
            url TEXT,
            is_read INTEGER DEFAULT 0,
            is_saved INTEGER DEFAULT 0,
            created_on_time INTEGER,
            fetched_at TEXT NOT NULL
        )''')
        
        # 创建 fever_cache_meta 表
        cursor.execute('''CREATE TABLE IF NOT EXISTS fever_cache_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_feed_id ON fever_cache(feed_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_read ON fever_cache(is_read)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_saved ON fever_cache(is_saved)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_on_time ON fever_cache(created_on_time)')
        
        self.conn.commit()
    
    def sync_items(self, client: 'FeverClient', limit: int = 1500) -> SyncResult:
        """
        从 Fever API 同步文章到缓存
        
        Args:
            client: FeverClient 实例
            limit: 最大同步文章数量
            
        Returns:
            SyncResult 实例
        """
        try:
            # 获取已存在的文章 ID 集合（用于判断新增还是更新）
            existing_ids = self._get_all_cached_ids()
            
            # 分批获取文章（每次最多 50 篇）
            # 注意：首次请求必须设置 max_id=2147483647（2^31-1）才能获取最新文章
            all_items = []
            collected_count = 0
            max_id = 2147483647  # 2^31 - 1，确保获取最新文章
            
            while collected_count < limit:
                batch_size = min(50, limit - collected_count)
                params = {'items': '', 'limit': batch_size}
                params['max_id'] = max_id  # 始终传递 max_id
                
                result = client._make_request(params)
                batch_items = result.get('items', [])
                
                if not batch_items:
                    break
                
                all_items.extend(batch_items)
                collected_count += len(batch_items)
                
                # 更新 max_id 用于下一批获取
                min_id = min(item.get('id', 0) for item in batch_items)
                if min_id == max_id or min_id == 0:
                    break
                max_id = min_id
            
            # 处理文章数据
            new_count = 0
            updated_count = 0
            fetched_at = datetime.now().isoformat()
            
            cursor = self.conn.cursor()
            
            for item in all_items:
                item_id = item.get('id')
                if not item_id:
                    continue
                
                # 检查是否已存在
                is_new = item_id not in existing_ids
                
                # 准备数据
                cache_item = FeverCacheItem(
                    id=item_id,
                    feed_id=item.get('feed_id', 0),
                    title=item.get('title', ''),
                    author=item.get('author', ''),
                    html=item.get('html', ''),
                    url=item.get('url', ''),
                    is_read=bool(item.get('is_read', 0)),
                    is_saved=bool(item.get('is_saved', 0)),
                    created_on_time=item.get('created_on_time', 0),
                    fetched_at=fetched_at
                )
                
                # 插入或更新
                cursor.execute('''INSERT OR REPLACE INTO fever_cache 
                    (id, feed_id, title, author, html, url, is_read, is_saved, created_on_time, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (cache_item.id, cache_item.feed_id, cache_item.title, cache_item.author,
                     cache_item.html, cache_item.url, 1 if cache_item.is_read else 0,
                     1 if cache_item.is_saved else 0, cache_item.created_on_time, cache_item.fetched_at))
                
                if is_new:
                    new_count += 1
                else:
                    updated_count += 1
            
            self.conn.commit()
            
            # 更新元数据
            self._set_meta('last_sync_time', fetched_at)
            self._set_meta('total_items', str(len(all_items)))
            
            return SyncResult(
                success=True,
                items_synced=len(all_items),
                new_items=new_count,
                updated_items=updated_count
            )
            
        except Exception as e:
            return SyncResult(
                success=False,
                error_message=str(e)
            )
    
    def _get_all_cached_ids(self) -> Set[int]:
        """获取所有已缓存的文章 ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM fever_cache')
        return {row[0] for row in cursor.fetchall()}
    
    def get_items(self, 
                  since_id: Optional[int] = None,
                  max_id: Optional[int] = None,
                  feed_id: Optional[int] = None,
                  limit: int = 50) -> List[FeverCacheItem]:
        """
        从缓存筛选文章
        
        Args:
            since_id: 获取此 ID 之后的文章
            max_id: 获取此 ID 之前的文章
            feed_id: 指定订阅源 ID
            limit: 最大返回数量
            
        Returns:
            FeverCacheItem 列表
        """
        cursor = self.conn.cursor()
        query = 'SELECT * FROM fever_cache WHERE 1=1'
        params = []
        
        if since_id:
            query += ' AND id > ?'
            params.append(since_id)
        if max_id:
            query += ' AND id < ?'
            params.append(max_id)
        if feed_id is not None:
            query += ' AND feed_id = ?'
            params.append(feed_id)
        
        query += ' ORDER BY id DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        return [self._row_to_item(row) for row in cursor.fetchall()]
    
    def get_item_by_id(self, item_id: int) -> Optional[FeverCacheItem]:
        """
        根据 ID 获取单篇文章
        
        Args:
            item_id: 文章 ID
            
        Returns:
            FeverCacheItem 或 None
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM fever_cache WHERE id = ?', (item_id,))
        row = cursor.fetchone()
        return self._row_to_item(row) if row else None
    
    def get_unread_ids(self) -> Set[int]:
        """
        获取未读文章 ID 集合
        
        Returns:
            未读文章 ID 集合
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM fever_cache WHERE is_read = 0')
        return {row[0] for row in cursor.fetchall()}
    
    def get_saved_ids(self) -> Set[int]:
        """
        获取已收藏文章 ID 集合
        
        Returns:
            已收藏文章 ID 集合
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM fever_cache WHERE is_saved = 1')
        return {row[0] for row in cursor.fetchall()}
    
    def get_unread_items(self, 
                         feed_id: Optional[int] = None,
                         limit: Optional[int] = None) -> List[FeverCacheItem]:
        """
        获取未读文章列表
        
        Args:
            feed_id: 可选，指定订阅源 ID
            limit: 可选，限制返回数量
            
        Returns:
            FeverCacheItem 列表
        """
        cursor = self.conn.cursor()
        query = 'SELECT * FROM fever_cache WHERE is_read = 0'
        params = []
        
        if feed_id is not None:
            query += ' AND feed_id = ?'
            params.append(feed_id)
        
        query += ' ORDER BY id DESC'
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        cursor.execute(query, params)
        return [self._row_to_item(row) for row in cursor.fetchall()]
    
    def mark_as_read(self, item_ids: List[int]) -> bool:
        """
        标记文章为已读（仅更新缓存）
        
        Args:
            item_ids: 文章 ID 列表
            
        Returns:
            操作是否成功
        """
        if not item_ids:
            return False
        
        cursor = self.conn.cursor()
        try:
            placeholders = ','.join('?' * len(item_ids))
            cursor.execute(f'UPDATE fever_cache SET is_read = 1 WHERE id IN ({placeholders})', item_ids)
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"标记已读失败：{e}")
            return False
    
    def mark_feed_as_read(self, feed_id: int, before_id: int) -> bool:
        """
        标记订阅源为已读（仅更新缓存）
        
        Args:
            feed_id: 订阅源 ID
            before_id: 标记此 ID 之前的所有文章
            
        Returns:
            操作是否成功
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute('UPDATE fever_cache SET is_read = 1 WHERE feed_id = ? AND id < ?',
                          (feed_id, before_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"标记订阅源为已读失败：{e}")
            return False
    
    def save_item(self, item_id: int) -> bool:
        """
        收藏文章（仅更新缓存）
        
        Args:
            item_id: 文章 ID
            
        Returns:
            操作是否成功
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute('UPDATE fever_cache SET is_saved = 1 WHERE id = ?', (item_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"收藏文章失败：{e}")
            return False
    
    def unsave_item(self, item_id: int) -> bool:
        """
        取消收藏文章（仅更新缓存）
        
        Args:
            item_id: 文章 ID
            
        Returns:
            操作是否成功
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute('UPDATE fever_cache SET is_saved = 0 WHERE id = ?', (item_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"取消收藏失败：{e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        cursor = self.conn.cursor()
        stats = {}
        
        cursor.execute('SELECT COUNT(*) FROM fever_cache')
        stats['total_items'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM fever_cache WHERE is_read = 0')
        stats['unread_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM fever_cache WHERE is_saved = 1')
        stats['saved_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT feed_id) FROM fever_cache')
        stats['feed_count'] = cursor.fetchone()[0]
        
        # 获取最近同步时间
        cursor.execute('SELECT value FROM fever_cache_meta WHERE key = ?', ('last_sync_time',))
        row = cursor.fetchone()
        stats['last_sync_time'] = row[0] if row else None
        
        return stats
    
    def _set_meta(self, key: str, value: str) -> bool:
        """设置缓存元数据"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''INSERT OR REPLACE INTO fever_cache_meta 
                (key, value, updated_at) VALUES (?, ?, ?)''',
                (key, value, datetime.now().isoformat()))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"设置缓存元数据失败：{e}")
            return False
    
    def _get_meta(self, key: str) -> Optional[str]:
        """获取缓存元数据"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM fever_cache_meta WHERE key = ?', (key,))
        row = cursor.fetchone()
        return row[0] if row else None
    
    def _row_to_item(self, row: sqlite3.Row) -> FeverCacheItem:
        """将数据库行转换为 FeverCacheItem"""
        data = dict(row)
        return FeverCacheItem(
            id=data['id'],
            feed_id=data['feed_id'],
            title=data['title'],
            author=data.get('author', ''),
            html=data.get('html', ''),
            url=data.get('url', ''),
            is_read=bool(data.get('is_read', 0)),
            is_saved=bool(data.get('is_saved', 0)),
            created_on_time=data.get('created_on_time', 0),
            fetched_at=data.get('fetched_at', '')
        )
    
    def sync_feeds(self, feeds: List[Dict[str, Any]]) -> bool:
        """
        同步订阅源到缓存
        
        Args:
            feeds: 订阅源列表
            
        Returns:
            是否成功
        """
        try:
            cursor = self.conn.cursor()
            
            # 创建 feeds 表（如果不存在）
            cursor.execute('''CREATE TABLE IF NOT EXISTS fever_feeds (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                site_url TEXT,
                description TEXT,
                last_modified TEXT,
                fetched_at TEXT NOT NULL
            )''')
            
            fetched_at = datetime.now().isoformat()
            
            for feed in feeds:
                feed_id = feed.get('id')
                if not feed_id:
                    continue
                
                cursor.execute('''INSERT OR REPLACE INTO fever_feeds 
                    (id, title, url, site_url, description, last_modified, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (feed_id, feed.get('title', ''), feed.get('url', ''),
                     feed.get('site_url', ''), feed.get('description', ''),
                     feed.get('last_modified', ''), fetched_at))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"同步订阅源失败：{e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


# 使用示例
if __name__ == '__main__':
    # 测试代码
    db_path = 'rss2pod.db'
    manager = FeverCacheManager(db_path)
    
    # 获取统计信息
    stats = manager.get_stats()
    print(f"缓存统计：{stats}")
    
    manager.close()
    print("FeverCacheManager 测试完成")