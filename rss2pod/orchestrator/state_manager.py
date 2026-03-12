#!/usr/bin/env python3
"""
状态管理器模块

负责：
- Group 处理状态管理（ProcessingState）
- 管道运行记录（PipelineRun）
- 数据库锁机制（同一 Group 互斥）
"""

import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import DatabaseManager


@dataclass
class ProcessingState:
    """Group 处理状态"""
    id: str                          # 主键，格式：state-{group_id}
    group_id: str                    # 关联的 Group ID
    last_run_at: Optional[str] = None # 上次运行时间（ISO 格式）
    last_fetch_cursor: Optional[str] = None  # Fever API since_id 游标
    last_episode_number: int = 0     # 上次生成的期数
    status: str = "idle"             # idle | running | error | disabled
    error_message: Optional[str] = None  # 错误信息
    next_scheduled_run: Optional[str] = None  # 下次计划运行时间
    retry_count: int = 0             # 当前重试次数
    locked_at: Optional[str] = None  # 锁定时间
    lock_owner: Optional[str] = None # 锁所有者
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingState":
        """从字典创建"""
        return cls(**data)
    
    @classmethod
    def from_row(cls, row: tuple, columns: List[str]) -> "ProcessingState":
        """从数据库行创建"""
        data = dict(zip(columns, row))
        return cls(**data)


@dataclass
class PipelineRun:
    """单次管道运行记录"""
    id: str                          # 主键，格式：run-{timestamp}-{group_id}
    group_id: str                    # 关联的 Group ID
    started_at: str                  # 开始时间
    completed_at: Optional[str] = None  # 完成时间
    status: str = "running"          # running | success | failed | partial
    stage: str = "init"              # 当前阶段
    articles_fetched: int = 0        # 获取文章数
    error_message: Optional[str] = None  # 错误信息
    episode_id: Optional[str] = None   # 生成的 Episode ID
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineRun":
        """从字典创建"""
        return cls(**data)
    
    @classmethod
    def from_row(cls, row: tuple, columns: List[str]) -> "PipelineRun":
        """从数据库行创建"""
        data = dict(zip(columns, row))
        return cls(**data)


class StateManager:
    """
    状态管理器
    
    负责管理 Group 处理状态和管道运行记录，提供数据库锁机制
    """
    
    def __init__(self, db: DatabaseManager):
        """
        初始化状态管理器
        
        Args:
            db: DatabaseManager 实例
        """
        self.db = db
        self._ensure_tables()
    
    def _ensure_tables(self):
        """确保数据表存在"""
        cursor = self.db.conn.cursor()
        
        # 创建 processing_state 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_state (
                id TEXT PRIMARY KEY,
                group_id TEXT NOT NULL,
                last_run_at TEXT,
                last_fetch_cursor TEXT,
                last_episode_number INTEGER DEFAULT 0,
                status TEXT DEFAULT 'idle',
                error_message TEXT,
                next_scheduled_run TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                locked_at TEXT,
                lock_owner TEXT
            )
        ''')
        
        # 创建 pipeline_run 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pipeline_run (
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
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_state_group ON processing_state(group_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_state_status ON processing_state(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_run_group ON pipeline_run(group_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_run_status ON pipeline_run(status)')
        
        self.db.conn.commit()
    
    def _get_columns(self, cls) -> List[str]:
        """获取数据类的字段名列表"""
        import dataclasses
        return [f.name for f in dataclasses.fields(cls)]
    
    # ========== ProcessingState 操作 ==========
    
    def get_state(self, group_id: str) -> Optional[ProcessingState]:
        """
        获取 Group 处理状态
        
        Args:
            group_id: Group ID
            
        Returns:
            ProcessingState 或 None
        """
        cursor = self.db.conn.cursor()
        state_id = f"state-{group_id}"
        cursor.execute('SELECT * FROM processing_state WHERE id = ?', (state_id,))
        row = cursor.fetchone()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return ProcessingState.from_row(row, columns)
        return None
    
    def get_or_create_state(self, group_id: str) -> ProcessingState:
        """
        获取或创建 Group 处理状态
        
        Args:
            group_id: Group ID
            
        Returns:
            ProcessingState 实例
        """
        state = self.get_state(group_id)
        if state:
            return state
        
        # 创建新状态
        state = ProcessingState(
            id=f"state-{group_id}",
            group_id=group_id,
            status="idle"
        )
        self.add_state(state)
        return state
    
    def add_state(self, state: ProcessingState) -> bool:
        """
        添加处理状态
        
        Args:
            state: ProcessingState 实例
            
        Returns:
            是否成功
        """
        cursor = self.db.conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO processing_state 
                (id, group_id, last_run_at, last_fetch_cursor, last_episode_number,
                 status, error_message, next_scheduled_run, retry_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                state.id, state.group_id, state.last_run_at, state.last_fetch_cursor,
                state.last_episode_number, state.status, state.error_message,
                state.next_scheduled_run, state.retry_count, state.created_at, state.updated_at
            ))
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"添加处理状态失败：{e}")
            return False
    
    def update_state(self, state: ProcessingState) -> bool:
        """
        更新处理状态
        
        Args:
            state: ProcessingState 实例
            
        Returns:
            是否成功
        """
        state.updated_at = datetime.now().isoformat()
        return self.add_state(state)
    
    def get_all_states(self, status_filter: Optional[str] = None) -> List[ProcessingState]:
        """
        获取所有处理状态
        
        Args:
            status_filter: 可选的状态过滤
            
        Returns:
            ProcessingState 列表
        """
        cursor = self.db.conn.cursor()
        
        if status_filter:
            cursor.execute('SELECT * FROM processing_state WHERE status = ?', (status_filter,))
        else:
            cursor.execute('SELECT * FROM processing_state')
        
        columns = [desc[0] for desc in cursor.description]
        return [ProcessingState.from_row(row, columns) for row in cursor.fetchall()]
    
    def get_states_by_status(self, status: str) -> List[ProcessingState]:
        """
        根据状态获取处理状态
        
        Args:
            status: 状态值
            
        Returns:
            ProcessingState 列表
        """
        return self.get_all_states(status_filter=status)
    
    def set_status(self, group_id: str, status: str, error_message: Optional[str] = None) -> bool:
        """
        设置 Group 处理状态
        
        Args:
            group_id: Group ID
            status: 新状态
            error_message: 错误信息（可选）
            
        Returns:
            是否成功
        """
        state = self.get_or_create_state(group_id)
        state.status = status
        state.error_message = error_message
        return self.update_state(state)
    
    def mark_running(self, group_id: str) -> bool:
        """标记为运行中"""
        state = self.get_or_create_state(group_id)
        state.status = "running"
        state.last_run_at = datetime.now().isoformat()
        state.error_message = None
        return self.update_state(state)
    
    def mark_idle(self, group_id: str) -> bool:
        """标记为空闲"""
        state = self.get_or_create_state(group_id)
        state.status = "idle"
        state.error_message = None
        return self.update_state(state)
    
    def mark_error(self, group_id: str, error_message: str) -> bool:
        """标记为错误"""
        state = self.get_or_create_state(group_id)
        state.status = "error"
        state.error_message = error_message
        return self.update_state(state)
    
    def mark_disabled(self, group_id: str) -> bool:
        """标记为禁用"""
        state = self.get_or_create_state(group_id)
        state.status = "disabled"
        return self.update_state(state)
    
    def update_episode_number(self, group_id: str, episode_number: int) -> bool:
        """
        更新 Group 的最后一期期数（持久化到数据库）
        
        Args:
            group_id: Group ID
            episode_number: 期数
            
        Returns:
            是否成功
        """
        state = self.get_or_create_state(group_id)
        state.last_episode_number = episode_number
        state.updated_at = datetime.now().isoformat()
        return self.add_state(state)
    
    def get_last_episode_number(self, group_id: str) -> int:
        """
        获取 Group 的最后一期期数
        
        Args:
            group_id: Group ID
            
        Returns:
            期数，如果没有记录则返回 0
        """
        state = self.get_state(group_id)
        return state.last_episode_number if state else 0
    
    # ========== 数据库锁机制 ==========
    
    def acquire_lock(self, group_id: str, owner: str = "default") -> bool:
        """
        获取 Group 处理锁（数据库锁）
        
        Args:
            group_id: Group ID
            owner: 锁所有者标识
            
        Returns:
            是否成功获取锁
        """
        cursor = self.db.conn.cursor()
        state_id = f"state-{group_id}"
        
        # 尝试获取锁：只有 idle 或 error 状态且未被锁定的记录才能被锁定
        cursor.execute('''
            UPDATE processing_state 
            SET status = 'running', 
                locked_at = ?, 
                lock_owner = ?,
                updated_at = ?
            WHERE id = ? 
              AND (status = 'idle' OR status = 'error')
              AND (locked_at IS NULL OR locked_at = '')
        ''', (
            datetime.now().isoformat(),
            owner,
            datetime.now().isoformat(),
            state_id
        ))
        
        self.db.conn.commit()
        return cursor.rowcount > 0
    
    def release_lock(self, group_id: str, owner: str = "default") -> bool:
        """
        释放 Group 处理锁
        
        Args:
            group_id: Group ID
            owner: 锁所有者标识（用于验证）
            
        Returns:
            是否成功释放锁
        """
        cursor = self.db.conn.cursor()
        state_id = f"state-{group_id}"
        
        # 释放锁：只有锁所有者才能释放
        cursor.execute('''
            UPDATE processing_state 
            SET locked_at = NULL, 
                lock_owner = NULL,
                status = 'idle',
                updated_at = ?
            WHERE id = ? AND lock_owner = ?
        ''', (datetime.now().isoformat(), state_id, owner))
        
        self.db.conn.commit()
        return cursor.rowcount > 0
    
    def is_locked(self, group_id: str) -> bool:
        """
        检查 Group 是否被锁定
        
        Args:
            group_id: Group ID
            
        Returns:
            是否被锁定
        """
        state = self.get_state(group_id)
        if state and state.status == "running":
            return True
        return False
    
    # ========== PipelineRun 操作 ==========
    
    def create_run(self, group_id: str) -> PipelineRun:
        """
        创建管道运行记录
        
        Args:
            group_id: Group ID
            
        Returns:
            PipelineRun 实例
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        run = PipelineRun(
            id=f"run-{timestamp}-{group_id}",
            group_id=group_id,
            started_at=datetime.now().isoformat(),
            status="running"
        )
        self.add_run(run)
        return run
    
    def add_run(self, run: PipelineRun) -> bool:
        """
        添加管道运行记录
        
        Args:
            run: PipelineRun 实例
            
        Returns:
            是否成功
        """
        cursor = self.db.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO pipeline_run 
                (id, group_id, started_at, completed_at, status, stage,
                 articles_fetched, error_message, episode_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                run.id, run.group_id, run.started_at, run.completed_at,
                run.status, run.stage, run.articles_fetched, run.error_message,
                run.episode_id, run.created_at, run.updated_at
            ))
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"添加管道运行记录失败：{e}")
            return False
    
    def update_run(self, run: PipelineRun) -> bool:
        """
        更新管道运行记录
        
        Args:
            run: PipelineRun 实例
            
        Returns:
            是否成功
        """
        run.updated_at = datetime.now().isoformat()
        return self.add_run(run)
    
    def complete_run(self, run: PipelineRun, status: str, episode_id: Optional[str] = None) -> bool:
        """
        完成管道运行
        
        Args:
            run: PipelineRun 实例
            status: 最终状态 (success | failed | partial)
            episode_id: 生成的 Episode ID
            
        Returns:
            是否成功
        """
        run.completed_at = datetime.now().isoformat()
        run.status = status
        run.episode_id = episode_id
        return self.update_run(run)
    
    def fail_run(self, run: PipelineRun, stage: str, error_message: str) -> bool:
        """
        标记管道运行失败
        
        Args:
            run: PipelineRun 实例
            stage: 失败阶段
            error_message: 错误信息
            
        Returns:
            是否成功
        """
        run.completed_at = datetime.now().isoformat()
        run.status = "failed"
        run.stage = stage
        run.error_message = error_message
        return self.update_run(run)
    
    def get_runs_by_group(self, group_id: str, limit: int = 50) -> List[PipelineRun]:
        """
        获取 Group 的运行历史
        
        Args:
            group_id: Group ID
            limit: 返回数量限制
            
        Returns:
            PipelineRun 列表
        """
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT * FROM pipeline_run 
            WHERE group_id = ? 
            ORDER BY started_at DESC 
            LIMIT ?
        ''', (group_id, limit))
        
        columns = [desc[0] for desc in cursor.description]
        return [PipelineRun.from_row(row, columns) for row in cursor.fetchall()]
    
    def get_running_runs(self) -> List[PipelineRun]:
        """
        获取所有运行中的管道
        
        Returns:
            PipelineRun 列表
        """
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT * FROM pipeline_run 
            WHERE status = 'running'
        ''')
        
        columns = [desc[0] for desc in cursor.description]
        return [PipelineRun.from_row(row, columns) for row in cursor.fetchall()]
    
    # ========== 统计信息 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        cursor = self.db.conn.cursor()
        stats = {}
        
        # 按状态统计
        cursor.execute('SELECT status, COUNT(*) FROM processing_state GROUP BY status')
        stats['states_by_status'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 运行中数量
        cursor.execute('SELECT COUNT(*) FROM pipeline_run WHERE status = ?', ('running',))
        stats['running_pipelines'] = cursor.fetchone()[0]
        
        # 今日运行次数
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) FROM pipeline_run 
            WHERE started_at LIKE ?
        ''', (f'{today}%',))
        stats['runs_today'] = cursor.fetchone()[0]
        
        return stats


def init_state_manager(db_path: str = "rss2pod.db") -> StateManager:
    """
    初始化状态管理器
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        StateManager 实例
    """
    db = DatabaseManager(db_path)
    return StateManager(db)


if __name__ == '__main__':
    # 测试状态管理器
    print("测试状态管理器...")
    
    state_manager = init_state_manager("test_state.db")
    
    # 测试状态操作
    test_group = "test-group-1"
    
    # 获取或创建状态
    state = state_manager.get_or_create_state(test_group)
    print(f"初始状态：{state.status}")
    
    # 测试锁
    if state_manager.acquire_lock(test_group, "test-owner"):
        print("成功获取锁")
        
        # 尝试再次获取（应该失败）
        if not state_manager.acquire_lock(test_group, "other-owner"):
            print("第二次获取锁失败（预期）")
        
        # 释放锁
        state_manager.release_lock(test_group, "test-owner")
        print("锁已释放")
    
    # 测试管道运行记录
    run = state_manager.create_run(test_group)
    print(f"创建运行记录：{run.id}")
    
    state_manager.complete_run(run, "success", "episode-1")
    print("运行记录已完成")
    
    # 获取历史
    runs = state_manager.get_runs_by_group(test_group)
    print(f"运行历史：{len(runs)} 条")
    
    # 统计信息
    stats = state_manager.get_stats()
    print(f"统计信息：{stats}")
    
    print("\n状态管理器测试完成!")