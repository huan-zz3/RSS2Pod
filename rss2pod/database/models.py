#!/usr/bin/env python3
"""
数据库模型 - SQLite 数据表定义
包含核心表：Article, SourceSummary, Group, Episode
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
import json
import os


@dataclass
class Article:
    """文章表"""
    id: str
    title: str
    source: str
    source_url: str
    link: str
    published: str
    content: str
    text_content: str
    author: str = ""
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    processed_at: Optional[str] = None
    error_message: Optional[str] = None
    token_count: int = 0
    group_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceSummary:
    """源级摘要表"""
    id: str
    source: str
    summary: str
    article_ids: List[str] = field(default_factory=list)
    key_topics: List[str] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    article_count: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    group_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Group:
    """分组表 - 核心配置单位"""
    id: str
    name: str
    description: str = ""
    rss_sources: List[str] = field(default_factory=list)
    summary_preference: str = "balanced"
    podcast_structure: str = "single"
    english_learning_mode: str = "off"
    audio_speed: float = 1.0  # 音频播放速度 (0.5-2.0, 1.0为正常速度)
    trigger_type: str = "time"
    trigger_config: Dict[str, Any] = field(default_factory=dict)
    feed_url: Optional[str] = None
    retention_days: int = 30
    prompt_overrides: Dict[str, Any] = field(default_factory=dict)  # LLM prompt 覆盖配置
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Episode:
    """播客期数表"""
    id: str
    group_id: str
    title: str
    episode_number: int
    script: str
    audio_path: Optional[str] = None
    audio_duration: int = 0
    guid: str = ""
    starred: bool = False
    expire_at: Optional[str] = None
    published_at: Optional[str] = None
    feed_published: bool = False
    source_summaries: List[str] = field(default_factory=list)
    source_summary_ids: List[str] = field(default_factory=list)  # 新增：关联的 SourceSummary ID 列表
    article_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessingState:
    """Group 处理状态表"""
    id: str                              # 主键，格式：state-{group_id}
    group_id: str                        # 关联的 Group ID
    last_run_at: Optional[str] = None    # 上次运行时间（ISO 格式）
    last_fetch_cursor: Optional[str] = None  # Fever API since_id 游标
    last_episode_number: int = 0         # 上次生成的期数
    status: str = "idle"                 # idle | running | error | disabled
    error_message: Optional[str] = None  # 错误信息
    next_scheduled_run: Optional[str] = None  # 下次计划运行时间
    retry_count: int = 0                 # 当前重试次数
    locked_at: Optional[str] = None      # 锁定时间
    lock_owner: Optional[str] = None     # 锁所有者
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineRun:
    """管道运行记录表"""
    id: str                              # 主键，格式：run-{timestamp}-{group_id}
    group_id: str                        # 关联的 Group ID
    started_at: str                      # 开始时间
    completed_at: Optional[str] = None   # 完成时间
    status: str = "running"              # running | success | failed | partial
    stage: str = "init"                  # 当前阶段
    articles_fetched: int = 0            # 获取文章数
    error_message: Optional[str] = None  # 错误信息
    episode_id: Optional[str] = None     # 生成的 Episode ID
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FeverCacheItem:
    """Fever API 文章缓存项"""
    id: int                    # Fever API 文章 ID（主键）
    feed_id: int               # 订阅源 ID
    title: str                 # 标题
    author: str                # 作者
    html: str                  # 原始 HTML 内容
    url: str                   # 原文链接
    is_read: bool              # 是否已读
    is_saved: bool             # 是否已收藏
    created_on_time: int       # 创建时间戳
    fetched_at: str            # 本地获取时间（ISO 格式）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'feed_id': self.feed_id,
            'title': self.title,
            'author': self.author,
            'html': self.html,
            'url': self.url,
            'is_read': self.is_read,
            'is_saved': self.is_saved,
            'created_on_time': self.created_on_time,
            'fetched_at': self.fetched_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeverCacheItem':
        """从字典创建"""
        return cls(
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


class DatabaseManager:
    """SQLite 数据库管理器"""

    def __init__(self, db_path: str = "rss2pod.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_database()

    def _init_database(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, source TEXT NOT NULL,
            source_url TEXT, link TEXT, published TEXT, content TEXT,
            text_content TEXT, author TEXT DEFAULT '', status TEXT DEFAULT 'pending',
            created_at TEXT, updated_at TEXT, processed_at TEXT, error_message TEXT,
            token_count INTEGER DEFAULT 0, group_id TEXT, metadata TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS source_summaries (
            id TEXT PRIMARY KEY, source TEXT NOT NULL, summary TEXT NOT NULL,
            article_ids TEXT, key_topics TEXT, highlights TEXT,
            article_count INTEGER DEFAULT 0, generated_at TEXT, group_id TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS groups (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT DEFAULT '',
            rss_sources TEXT, summary_preference TEXT DEFAULT 'balanced',
            podcast_structure TEXT DEFAULT 'single', english_learning_mode TEXT DEFAULT 'off',
            audio_speed REAL DEFAULT 1.0, trigger_type TEXT DEFAULT 'time', trigger_config TEXT, feed_url TEXT,
            retention_days INTEGER DEFAULT 30, prompt_overrides TEXT DEFAULT '{}',
            created_at TEXT, updated_at TEXT, enabled INTEGER DEFAULT 1)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS episodes (
            id TEXT PRIMARY KEY, group_id TEXT NOT NULL, title TEXT NOT NULL,
            episode_number INTEGER NOT NULL, script TEXT NOT NULL, audio_path TEXT,
            audio_duration INTEGER DEFAULT 0, guid TEXT, starred INTEGER DEFAULT 0,
            expire_at TEXT, published_at TEXT, feed_published INTEGER DEFAULT 0,
            source_summaries TEXT, source_summary_ids TEXT, article_ids TEXT,
            created_at TEXT, updated_at TEXT,
            FOREIGN KEY (group_id) REFERENCES groups(id))''')
        # 新增 processing_state 表
        cursor.execute('''CREATE TABLE IF NOT EXISTS processing_state (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            last_run_at TEXT,
            last_fetch_cursor TEXT,
            last_episode_number INTEGER DEFAULT 0,
            status TEXT DEFAULT 'idle',
            error_message TEXT,
            next_scheduled_run TEXT,
            retry_count INTEGER DEFAULT 0,
            locked_at TEXT,
            lock_owner TEXT,
            created_at TEXT,
            updated_at TEXT)''')
        # 新增 pipeline_run 表
        cursor.execute('''CREATE TABLE IF NOT EXISTS pipeline_run (
            id TEXT PRIMARY KEY,
            group_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT DEFAULT 'running',
            stage TEXT DEFAULT 'init',
            articles_fetched INTEGER DEFAULT 0,
            error_message TEXT,
            episode_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (group_id) REFERENCES groups(id))''')
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_episodes_group ON episodes(group_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_state_group ON processing_state(group_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_state_status ON processing_state(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_run_group ON pipeline_run(group_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_run_status ON pipeline_run(status)')
        # 创建 fever_cache 表（Fever API 文章缓存）
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
        # 创建 fever_cache_meta 表（缓存元数据）
        cursor.execute('''CREATE TABLE IF NOT EXISTS fever_cache_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )''')
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fever_cache_feed_id ON fever_cache(feed_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fever_cache_is_read ON fever_cache(is_read)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fever_cache_is_saved ON fever_cache(is_saved)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fever_cache_created_on_time ON fever_cache(created_on_time)')
        self.conn.commit()

    def add_source_summary(self, summary: SourceSummary) -> bool:
        """添加源级摘要"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''INSERT OR REPLACE INTO source_summaries 
                (id, source, summary, article_ids, key_topics, highlights,
                 article_count, generated_at, group_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (summary.id, summary.source, summary.summary,
                 json.dumps(summary.article_ids), json.dumps(summary.key_topics),
                 json.dumps(summary.highlights), summary.article_count,
                 summary.generated_at, summary.group_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"添加源级摘要失败：{e}")
            return False

    def add_article(self, article: Article) -> bool:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''INSERT OR REPLACE INTO articles 
                (id, title, source, source_url, link, published, content, text_content,
                author, status, created_at, updated_at, processed_at, error_message,
                token_count, group_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (article.id, article.title, article.source, article.source_url,
                article.link, article.published, article.content, article.text_content,
                article.author, article.status, article.created_at, article.updated_at,
                article.processed_at, article.error_message, article.token_count,
                article.group_id, json.dumps(article.metadata)))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"添加文章失败：{e}")
            return False

    def get_article(self, article_id: str) -> Optional[Article]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
        row = cursor.fetchone()
        return self._row_to_article(row) if row else None

    def get_articles_by_status(self, status: str, limit: int = 100) -> List[Article]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM articles WHERE status = ? LIMIT ?', (status, limit))
        return [self._row_to_article(row) for row in cursor.fetchall()]

    def get_all_articles(self, limit: int = 100) -> List[Article]:
        """获取所有文章（不限制状态）"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM articles ORDER BY created_at DESC LIMIT ?', (limit,))
        return [self._row_to_article(row) for row in cursor.fetchall()]

    def get_articles_by_source(self, source: str, status: Optional[str] = None) -> List[Article]:
        cursor = self.conn.cursor()
        if status:
            cursor.execute('SELECT * FROM articles WHERE source = ? AND status = ?', (source, status))
        else:
            cursor.execute('SELECT * FROM articles WHERE source = ?', (source,))
        return [self._row_to_article(row) for row in cursor.fetchall()]

    def update_article_status(self, article_id: str, status: str, error_message: Optional[str] = None):
        cursor = self.conn.cursor()
        cursor.execute('''UPDATE articles SET status = ?, updated_at = ?, error_message = ?, 
            processed_at = ? WHERE id = ?''',
            (status, datetime.now().isoformat(), error_message, 
             datetime.now().isoformat() if status == 'processed' else None, article_id))
        self.conn.commit()

    def add_group(self, group: Group) -> bool:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''INSERT OR REPLACE INTO groups 
                (id, name, description, rss_sources, summary_preference, podcast_structure,
                english_learning_mode, audio_speed, trigger_type, trigger_config, feed_url,
                retention_days, prompt_overrides, created_at, updated_at, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (group.id, group.name, group.description, json.dumps(group.rss_sources),
                group.summary_preference, group.podcast_structure, group.english_learning_mode,
                group.audio_speed, group.trigger_type, json.dumps(group.trigger_config), group.feed_url,
                group.retention_days, json.dumps(group.prompt_overrides), group.created_at, 
                group.updated_at, 1 if group.enabled else 0))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"添加 Group 失败：{e}")
            return False

    def get_group(self, group_id: str) -> Optional[Group]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM groups WHERE id = ?', (group_id,))
        row = cursor.fetchone()
        return self._row_to_group(row) if row else None

    def get_all_groups(self, enabled_only: bool = False) -> List[Group]:
        cursor = self.conn.cursor()
        if enabled_only:
            cursor.execute('SELECT * FROM groups WHERE enabled = 1')
        else:
            cursor.execute('SELECT * FROM groups')
        return [self._row_to_group(row) for row in cursor.fetchall()]

    def update_group(self, group: Group) -> bool:
        group.updated_at = datetime.now().isoformat()
        return self.add_group(group)

    def delete_group(self, group_id: str) -> bool:
        """删除 Group 及相关联的数据文件和数据库记录"""
        import shutil
        from pathlib import Path
        
        cursor = self.conn.cursor()
        
        # 先获取 group 信息（用于删除 name 相关的文件）
        group = self.get_group(group_id)
        group_name = group.name if group else group_id
        
        # 获取 data 目录路径（使用绝对路径确保正确性）
        db_abs_path = os.path.abspath(self.db_path)
        db_dir = os.path.dirname(db_abs_path)
        data_dir = os.path.join(db_dir, 'data')
        
        # 1. 删除 media/{group_id} 目录
        media_group_dir = os.path.join(data_dir, 'media', group_id)
        if os.path.exists(media_group_dir):
            shutil.rmtree(media_group_dir)
        
        # 1b. 删除 media/{group_name} 目录（兼容使用 name 的情况）
        if group_name != group_id:
            media_name_dir = os.path.join(data_dir, 'media', group_name)
            if os.path.exists(media_name_dir):
                shutil.rmtree(media_name_dir)
        
        # 2. 删除 feeds/episodes/{group_id}.json
        episode_feed_id = os.path.join(data_dir, 'feeds', 'episodes', f'{group_id}.json')
        if os.path.exists(episode_feed_id):
            os.remove(episode_feed_id)
        
        # 2b. 删除 feeds/episodes/{group_name}.json（兼容使用 name 的情况）
        if group_name != group_id:
            episode_feed_name = os.path.join(data_dir, 'feeds', 'episodes', f'{group_name}.json')
            if os.path.exists(episode_feed_name):
                os.remove(episode_feed_name)
        
        # 3. 删除 feeds/groups/{group_id}.json
        group_feed_id = os.path.join(data_dir, 'feeds', 'groups', f'{group_id}.json')
        if os.path.exists(group_feed_id):
            os.remove(group_feed_id)
        
        # 3b. 删除 feeds/groups/{group_name}.json（兼容使用 name 的情况）
        if group_name != group_id:
            group_feed_name = os.path.join(data_dir, 'feeds', 'groups', f'{group_name}.json')
            if os.path.exists(group_feed_name):
                os.remove(group_feed_name)
        
        # 4. 删除 feeds/rss/{group_id}.xml
        rss_feed_id = os.path.join(data_dir, 'feeds', 'rss', f'{group_id}.xml')
        if os.path.exists(rss_feed_id):
            os.remove(rss_feed_id)
        
        # 4b. 删除 feeds/rss/{group_name}.xml（兼容使用 name 的情况）
        if group_name != group_id:
            rss_feed_name = os.path.join(data_dir, 'feeds', 'rss', f'{group_name}.xml')
            if os.path.exists(rss_feed_name):
                os.remove(rss_feed_name)
        
        # 5. 删除 exports/ 中包含 group_id 或 group_name 的文件
        exports_dir = os.path.join(data_dir, 'exports')
        if os.path.exists(exports_dir):
            for filename in os.listdir(exports_dir):
                # 匹配格式：articles_{group_id}_*.json, articles_{group_name}_*.json 等
                if filename.startswith(f'articles_{group_id}_') or \
                   filename.startswith(f'articles_{group_name}_') or \
                   filename.startswith(f'fever_api_{group_id}_') or \
                   filename.startswith(f'fever_api_{group_name}_') or \
                   f'_{group_id}_' in filename or \
                   f'_{group_name}_' in filename:
                    os.remove(os.path.join(exports_dir, filename))
        
        # 6. 删除数据库中的关联数据（按依赖顺序）
        # 先删除 episodes（因为 articles 通过 episode 关联）
        cursor.execute('DELETE FROM episodes WHERE group_id = ?', (group_id,))
        
        # 删除 articles
        cursor.execute('DELETE FROM articles WHERE group_id = ?', (group_id,))
        
        # 删除 source_summaries
        cursor.execute('DELETE FROM source_summaries WHERE group_id = ?', (group_id,))
        
        # 删除 processing_state
        cursor.execute('DELETE FROM processing_state WHERE group_id = ?', (group_id,))
        
        # 删除 pipeline_run
        cursor.execute('DELETE FROM pipeline_run WHERE group_id = ?', (group_id,))
        
        # 最后删除 group 记录
        cursor.execute('DELETE FROM groups WHERE id = ?', (group_id,))
        self.conn.commit()
        
        return cursor.rowcount > 0

    def add_episode(self, episode: Episode) -> bool:
        cursor = self.conn.cursor()
        try:
            cursor.execute('''INSERT OR REPLACE INTO episodes 
                (id, group_id, title, episode_number, script, audio_path, audio_duration,
                guid, starred, expire_at, published_at, feed_published, source_summaries,
                article_ids, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (episode.id, episode.group_id, episode.title, episode.episode_number,
                episode.script, episode.audio_path, episode.audio_duration, episode.guid,
                1 if episode.starred else 0, episode.expire_at, episode.published_at,
                1 if episode.feed_published else 0, json.dumps(episode.source_summaries),
                json.dumps(episode.article_ids), episode.created_at, episode.updated_at))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"添加 Episode 失败：{e}")
            return False

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM episodes WHERE id = ?', (episode_id,))
        row = cursor.fetchone()
        return self._row_to_episode(row) if row else None

    def get_episodes_by_group(self, group_id: str, limit: int = 50) -> List[Episode]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM episodes WHERE group_id = ? ORDER BY episode_number DESC LIMIT ?',
                      (group_id, limit))
        return [self._row_to_episode(row) for row in cursor.fetchall()]

    def get_starred_episodes(self) -> List[Episode]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM episodes WHERE starred = 1 ORDER BY published_at DESC')
        return [self._row_to_episode(row) for row in cursor.fetchall()]

    def update_episode(self, episode: Episode) -> bool:
        episode.updated_at = datetime.now().isoformat()
        return self.add_episode(episode)

    def delete_episode(self, episode_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM episodes WHERE id = ?', (episode_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def _row_to_article(self, row: sqlite3.Row) -> Article:
        data = dict(row)
        data['metadata'] = json.loads(data['metadata'] or '{}')
        return Article(**data)

    def _row_to_group(self, row: sqlite3.Row) -> Group:
        data = dict(row)
        data['rss_sources'] = json.loads(data['rss_sources'] or '[]')
        data['trigger_config'] = json.loads(data['trigger_config'] or '{}')
        data['prompt_overrides'] = json.loads(data.get('prompt_overrides') or '{}')
        data['enabled'] = bool(data['enabled'])
        # 处理 audio_speed 字段（兼容旧数据）
        data['audio_speed'] = float(data.get('audio_speed') or 1.0)
        return Group(**data)

    def _row_to_episode(self, row: sqlite3.Row) -> Episode:
        data = dict(row)
        data['starred'] = bool(data['starred'])
        data['feed_published'] = bool(data['feed_published'])
        return Episode(**data)

    def get_stats(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        stats = {}
        cursor.execute('SELECT COUNT(*) FROM articles')
        stats['total_articles'] = cursor.fetchone()[0]
        cursor.execute('SELECT status, COUNT(*) FROM articles GROUP BY status')
        stats['articles_by_status'] = {row[0]: row[1] for row in cursor.fetchall()}
        cursor.execute('SELECT COUNT(*) FROM groups WHERE enabled = 1')
        stats['enabled_groups'] = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM episodes')
        stats['total_episodes'] = cursor.fetchone()[0]
        return stats

    # ========== ProcessingState 方法 ==========

    def add_processing_state(self, state: ProcessingState) -> bool:
        """添加处理状态"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''INSERT OR REPLACE INTO processing_state 
                (id, group_id, last_run_at, last_fetch_cursor, last_episode_number,
                 status, error_message, next_scheduled_run, retry_count,
                 locked_at, lock_owner, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (state.id, state.group_id, state.last_run_at, state.last_fetch_cursor,
                 state.last_episode_number, state.status, state.error_message,
                 state.next_scheduled_run, state.retry_count, state.locked_at,
                 state.lock_owner, state.created_at, state.updated_at))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"添加处理状态失败：{e}")
            return False

    def get_processing_state(self, group_id: str) -> Optional[ProcessingState]:
        """获取 Group 处理状态"""
        cursor = self.conn.cursor()
        state_id = f"state-{group_id}"
        cursor.execute('SELECT * FROM processing_state WHERE id = ?', (state_id,))
        row = cursor.fetchone()
        return self._row_to_processing_state(row) if row else None

    def update_processing_state(self, state: ProcessingState) -> bool:
        """更新处理状态"""
        state.updated_at = datetime.now().isoformat()
        return self.add_processing_state(state)

    def acquire_group_lock(self, group_id: str, owner: str) -> bool:
        """获取 Group 处理锁"""
        cursor = self.conn.cursor()
        state_id = f"state-{group_id}"
        now = datetime.now().isoformat()
        # 只有 idle 或 error 状态且未锁定的记录才能被锁定
        cursor.execute('''UPDATE processing_state 
            SET status = 'running', locked_at = ?, lock_owner = ?, updated_at = ?
            WHERE id = ? AND (status = 'idle' OR status = 'error')
              AND (locked_at IS NULL OR locked_at = '')''',
            (now, owner, now, state_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def release_group_lock(self, group_id: str, owner: str) -> bool:
        """释放 Group 处理锁"""
        cursor = self.conn.cursor()
        state_id = f"state-{group_id}"
        cursor.execute('''UPDATE processing_state 
            SET locked_at = NULL, lock_owner = NULL, status = 'idle', updated_at = ?
            WHERE id = ? AND lock_owner = ?''',
            (datetime.now().isoformat(), state_id, owner))
        self.conn.commit()
        return cursor.rowcount > 0

    # ========== PipelineRun 方法 ==========

    def add_pipeline_run(self, run: PipelineRun) -> bool:
        """添加管道运行记录"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''INSERT INTO pipeline_run 
                (id, group_id, started_at, completed_at, status, stage,
                 articles_fetched, error_message, episode_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (run.id, run.group_id, run.started_at, run.completed_at,
                 run.status, run.stage, run.articles_fetched, run.error_message,
                 run.episode_id, run.created_at, run.updated_at))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"添加管道运行记录失败：{e}")
            return False

    def update_pipeline_run(self, run: PipelineRun) -> bool:
        """更新管道运行记录"""
        run.updated_at = datetime.now().isoformat()
        return self.add_pipeline_run(run)

    def get_pipeline_runs_by_group(self, group_id: str, limit: int = 50) -> List[PipelineRun]:
        """获取 Group 的运行历史"""
        cursor = self.conn.cursor()
        cursor.execute('''SELECT * FROM pipeline_run 
            WHERE group_id = ? ORDER BY started_at DESC LIMIT ?''',
            (group_id, limit))
        return [self._row_to_pipeline_run(row) for row in cursor.fetchall()]

    def get_running_pipeline_runs(self) -> List[PipelineRun]:
        """获取所有运行中的管道"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM pipeline_run WHERE status = ?', ('running',))
        return [self._row_to_pipeline_run(row) for row in cursor.fetchall()]

    # ========== 辅助方法 ==========

    def _row_to_processing_state(self, row: sqlite3.Row) -> ProcessingState:
        data = dict(row)
        return ProcessingState(**data)

    def _row_to_pipeline_run(self, row: sqlite3.Row) -> PipelineRun:
        data = dict(row)
        return PipelineRun(**data)

    # ========== FeverCache 方法 ==========

    def add_fever_cache_item(self, item: FeverCacheItem) -> bool:
        """添加/更新单个缓存项"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''INSERT OR REPLACE INTO fever_cache 
                (id, feed_id, title, author, html, url, is_read, is_saved, created_on_time, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (item.id, item.feed_id, item.title, item.author, item.html, item.url,
                 1 if item.is_read else 0, 1 if item.is_saved else 0, item.created_on_time, item.fetched_at))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"添加缓存项失败：{e}")
            return False

    def add_fever_cache_items(self, items: List[FeverCacheItem]) -> int:
        """批量添加缓存项，返回成功插入的数量"""
        cursor = self.conn.cursor()
        try:
            data = [(item.id, item.feed_id, item.title, item.author, item.html, item.url,
                     1 if item.is_read else 0, 1 if item.is_saved else 0, item.created_on_time, item.fetched_at)
                    for item in items]
            cursor.executemany('''INSERT OR REPLACE INTO fever_cache 
                (id, feed_id, title, author, html, url, is_read, is_saved, created_on_time, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
            self.conn.commit()
            return cursor.rowcount
        except Exception as e:
            print(f"批量添加缓存项失败：{e}")
            return 0

    def get_fever_cache_items(self, 
                              since_id: Optional[int] = None,
                              max_id: Optional[int] = None,
                              feed_id: Optional[int] = None,
                              limit: int = 50) -> List[FeverCacheItem]:
        """查询缓存项（支持 since_id, max_id, feed_id 过滤）"""
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
        return [self._row_to_fever_cache_item(row) for row in cursor.fetchall()]

    def get_fever_cache_item_by_id(self, item_id: int) -> Optional[FeverCacheItem]:
        """根据 ID 查询缓存项"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM fever_cache WHERE id = ?', (item_id,))
        row = cursor.fetchone()
        return self._row_to_fever_cache_item(row) if row else None

    def get_fever_cache_unread_ids(self) -> set:
        """获取所有未读文章 ID 集合"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM fever_cache WHERE is_read = 0')
        return {row[0] for row in cursor.fetchall()}

    def get_fever_cache_saved_ids(self) -> set:
        """获取所有已收藏文章 ID 集合"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM fever_cache WHERE is_saved = 1')
        return {row[0] for row in cursor.fetchall()}

    def get_fever_cache_unread_items(self, 
                                     feed_id: Optional[int] = None,
                                     limit: Optional[int] = None) -> List[FeverCacheItem]:
        """获取未读文章列表"""
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
        return [self._row_to_fever_cache_item(row) for row in cursor.fetchall()]

    def update_fever_cache_status(self, 
                                  item_ids: List[int],
                                  is_read: Optional[bool] = None,
                                  is_saved: Optional[bool] = None) -> bool:
        """更新缓存项状态"""
        if not item_ids:
            return False
        
        cursor = self.conn.cursor()
        try:
            updates = []
            if is_read is not None:
                updates.append(f'is_read = {1 if is_read else 0}')
            if is_saved is not None:
                updates.append(f'is_saved = {1 if is_saved else 0}')
            
            if not updates:
                return False
            
            placeholders = ','.join('?' * len(item_ids))
            query = f'UPDATE fever_cache SET {", ".join(updates)} WHERE id IN ({placeholders})'
            cursor.execute(query, item_ids)
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"更新缓存状态失败：{e}")
            return False

    def update_fever_cache_mark_feed_as_read(self, feed_id: int, before_id: int) -> bool:
        """标记订阅源为已读（before_id 之前的所有文章）"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''UPDATE fever_cache SET is_read = 1 
                WHERE feed_id = ? AND id < ?''', (feed_id, before_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"标记订阅源为已读失败：{e}")
            return False

    def get_fever_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
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
        
        # 获取最近获取时间
        cursor.execute('SELECT MAX(fetched_at) FROM fever_cache')
        stats['last_fetch_time'] = cursor.fetchone()[0]
        
        return stats

    def set_fever_cache_meta(self, key: str, value: str) -> bool:
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

    def get_fever_cache_meta(self, key: str) -> Optional[str]:
        """获取缓存元数据"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM fever_cache_meta WHERE key = ?', (key,))
        row = cursor.fetchone()
        return row[0] if row else None

    def _row_to_fever_cache_item(self, row: sqlite3.Row) -> FeverCacheItem:
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

    def close(self):
        if self.conn:
            self.conn.close()


def init_db(db_path: str = "rss2pod.db") -> DatabaseManager:
    return DatabaseManager(db_path)


if __name__ == '__main__':
    db = init_db("test_rss2pod.db")
    group = Group(id="test-1", name="Test Group", rss_sources=["https://example.com"])
    db.add_group(group)
    print(f"Group: {db.get_group('test-1').name if db.get_group('test-1') else 'None'}")
    db.close()
    print("Database test completed!")
