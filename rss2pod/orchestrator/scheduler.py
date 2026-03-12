#!/usr/bin/env python3
"""
主调度器模块

负责：
- cron 表达式解析
- 触发器检测
- 调度循环（守护进程）
- 并发控制
- Fever 缓存同步
"""

import os
import sys
import signal
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from croniter import croniter
except ImportError:
    croniter = None
    print("警告：croniter 未安装，请运行：pip install croniter")

from database.models import DatabaseManager, Group
from .state_manager import StateManager, ProcessingState
from .logging_config import setup_logging
# 延迟导入避免循环依赖
# from rss2pod.services.pipeline import PipelineOrchestrator


class TaskType(Enum):
    """任务类型枚举"""
    SYNC_ARTICLES = "sync_articles"
    SYNC_FEEDS = "sync_feeds"
    CHECK_GROUPS = "check_groups"


@dataclass
class SchedulerConfig:
    """调度器配置"""
    check_interval_seconds: int = 60           # 检查间隔（秒）
    sync_articles_interval_minutes: int = 30   # 文章同步间隔（分钟）
    sync_feeds_interval_minutes: int = 60      # 订阅源同步间隔（分钟）
    check_groups_interval_minutes: int = 1     # 组更新检查间隔（分钟）
    max_concurrent_groups: int = 3             # 最大并发 Group 数
    retry_attempts: int = 3                    # 重试次数
    retry_delay_seconds: int = 3                # 重试延迟（秒）
    dry_run: bool = False                       # 模拟运行模式


class Scheduler:
    """
    主调度器类
    
    负责：
    - 解析 cron 表达式
    - 检测需要触发的 Group
    - 启动处理管道
    - 并发控制
    - Fever 缓存同步
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        db: Optional[DatabaseManager] = None,
        db_path: str = "rss2pod.db"
    ):
        """
        初始化调度器
        
        Args:
            config: 调度器配置字典
            db: DatabaseManager 实例（可选）
            db_path: 数据库文件路径
        """
        self.config = SchedulerConfig(
            check_interval_seconds=config.get('check_interval_seconds', 60),
            sync_articles_interval_minutes=config.get('sync_articles_interval_minutes', 30),
            sync_feeds_interval_minutes=config.get('sync_feeds_interval_minutes', 60),
            check_groups_interval_minutes=config.get('check_groups_interval_minutes', 1),
            max_concurrent_groups=config.get('max_concurrent_groups', 3),
            retry_attempts=config.get('retry_attempts', 3),
            retry_delay_seconds=config.get('retry_delay_seconds', 3),
            dry_run=config.get('dry_run', False)
        )
        
        # 初始化数据库
        self.db = db or DatabaseManager(db_path)
        self.state_manager = StateManager(self.db)
        
        # 初始化日志
        log_config = config.get('logging', {})
        self.logger = setup_logging(
            level=log_config.get('level', 'INFO'),
            log_file=log_config.get('file'),
            rotation=log_config.get('rotation', 'daily'),
            retention_days=log_config.get('retention_days', 7),
        )
        
        # 运行状态
        self.running = False
        self._is_stopping = False  # 防止重复调用 stop()
        self._shutdown_event = asyncio.Event()
        self._tasks: Dict[str, asyncio.Task] = {}
        self._last_check: Optional[datetime] = None
        
        # 同步时间跟踪
        self._last_sync_articles: Optional[datetime] = None
        self._last_sync_feeds: Optional[datetime] = None
        self._last_check_groups: Optional[datetime] = None
        
        # 互斥锁：防止多种任务同时执行
        self._task_lock = asyncio.Lock()
        self._current_task_type: Optional[TaskType] = None
        
        # 注册信号处理
        self._setup_signal_handlers()
        
        self.logger.info("调度器初始化完成")
        self.logger.info(f"配置：文章同步间隔={self.config.sync_articles_interval_minutes}分钟, "
                        f"订阅源同步间隔={self.config.sync_feeds_interval_minutes}分钟, "
                        f"组检查间隔={self.config.check_groups_interval_minutes}分钟")
    
    def _setup_signal_handlers(self):
        """注册信号处理器"""
        def signal_handler(signum, frame):
            # 只在调度器运行时响应信号
            if self.running:
                self.logger.info(f"收到信号 {signum}，准备关闭调度器...")
                self.stop()
            # 如果已经在停止中或已停止，则忽略重复信号
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except ValueError:
            # 在非主线程中无法设置信号处理器
            pass
    
    def _load_cron_expression(self, cron_expr: str) -> Optional[croniter]:
        """
        解析 cron 表达式
        
        Args:
            cron_expr: cron 表达式字符串
            
        Returns:
            croniter 实例或 None
        """
        if croniter is None:
            self.logger.error("croniter 未安装")
            return None
        
        try:
            return croniter(cron_expr, datetime.now())
        except Exception as e:
            self.logger.error(f"cron 表达式解析失败：{cron_expr}, 错误：{e}")
            return None
    
    def _get_next_run_time(self, cron_expr: str, after: Optional[datetime] = None) -> Optional[datetime]:
        """
        计算下次运行时间
        
        Args:
            cron_expr: cron 表达式
            after: 基准时间，默认当前时间
            
        Returns:
            下次运行时间或 None
        """
        cron = self._load_cron_expression(cron_expr)
        if cron is None:
            return None
        
        if after is None:
            after = datetime.now()
        
        try:
            return cron.get_next(datetime)
        except Exception as e:
            self.logger.error(f"计算下次运行时间失败：{e}")
            return None
    
    def _should_trigger(self, group: Group, state: ProcessingState) -> bool:
        """
        判断 Group 是否应该触发
        
        Args:
            group: Group 实例
            state: ProcessingState 实例
            
        Returns:
            是否应该触发
        """
        # 检查 Group 是否启用
        if not group.enabled:
            return False
        
        # 检查状态是否允许触发
        if state.status in ['running', 'disabled']:
            return False
        
        # 检查 cron 触发
        trigger_config = group.trigger_config or {}
        cron_expr = trigger_config.get('cron')
        
        if cron_expr:
            next_run = self._get_next_run_time(cron_expr)
            if next_run and datetime.now() >= next_run:
                self.logger.debug(f"Group {group.id} cron 触发条件满足")
                return True
        
        # 检查数量触发
        threshold = trigger_config.get('threshold', 0)
        if threshold > 0:
            # 获取未处理文章数量
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM articles 
                WHERE source IN ({})
                AND status = 'pending'
            '''.format(','.join(['?' for _ in group.rss_sources])), group.rss_sources)
            count = cursor.fetchone()[0]
            
            if count >= threshold:
                self.logger.debug(f"Group {group.id} 数量触发条件满足 ({count} >= {threshold})")
                return True
        
        return False
    
    def _check_triggers(self) -> List[str]:
        """
        检查所有 Group，返回需要触发的 Group ID 列表
        
        Returns:
            需要触发的 Group ID 列表
        """
        triggered_groups = []
        
        # 获取所有启用的 Group
        groups = self.db.get_all_groups(enabled_only=True)
        
        for group in groups:
            try:
                state = self.state_manager.get_or_create_state(group.id)
                
                if self._should_trigger(group, state):
                    triggered_groups.append(group.id)
                    
            except Exception as e:
                self.logger.error(f"检查 Group {group.id} 触发条件失败：{e}")
        
        self._last_check = datetime.now()
        return triggered_groups
    
    async def _run_group_pipeline(self, group_id: str):
        """
        运行单个 Group 的处理管道
        
        Args:
            group_id: Group ID
        """
        # 延迟导入避免循环依赖
        from rss2pod.services.pipeline import PipelineOrchestrator
        
        # 尝试获取锁
        if not self.state_manager.acquire_lock(group_id, "scheduler"):
            self.logger.debug(f"Group {group_id} 已被锁定，跳过")
            return
        
        try:
            self.logger.info(f"开始处理 Group: {group_id}")
            
            # 创建运行记录
            run = self.state_manager.create_run(group_id)
            
            # 获取 Group 配置
            group = self.db.get_group(group_id)
            if not group:
                self.logger.error(f"Group {group_id} 不存在")
                self.state_manager.fail_run(run, "init", f"Group {group_id} 不存在")
                return
            
            # 创建管道编排器
            orchestrator = PipelineOrchestrator(
                group=group,
                state=self.state_manager.get_or_create_state(group_id),
                db=self.db,
                db_path=self.db.db_path if hasattr(self.db, 'db_path') else "rss2pod.db",
                logger=self.logger,
                config=self.config,
                state_manager=self.state_manager  # 传递 state_manager 以持久化 last_episode_number
            )
            
            # 运行管道
            result = await orchestrator.run()
            
            # 更新运行记录
            if result.success:
                self.state_manager.complete_run(run, "success", result.episode_id)
                self.state_manager.mark_idle(group_id)
                self.logger.info(f"Group {group_id} 处理完成，Episode: {result.episode_id}")
            else:
                self.state_manager.fail_run(run, result.failed_stage, result.error_message)
                self.state_manager.mark_error(group_id, result.error_message)
                self.logger.error(f"Group {group_id} 处理失败：{result.error_message}")
            
        except Exception as e:
            self.logger.error(f"处理 Group {group_id} 异常：{e}")
            self.state_manager.mark_error(group_id, str(e))
            
        finally:
            # 释放锁
            self.state_manager.release_lock(group_id, "scheduler")
    
    async def _check_and_trigger(self):
        """检查触发器并启动管道"""
        triggered_groups = self._check_triggers()
        
        if not triggered_groups:
            self.logger.info("没有需要触发的 Group")
            return
        
        # 获取当前运行中的管道数量
        running_runs = self.state_manager.get_running_runs()
        running_count = len(running_runs)
        
        # 计算可启动的管道数量
        available_slots = self.config.max_concurrent_groups - running_count
        
        if available_slots <= 0:
            self.logger.debug(f"已达到最大并发数 ({running_count})，等待中...")
            return
        
        # 启动管道（限制并发数）
        groups_to_run = triggered_groups[:available_slots]
        
        for group_id in groups_to_run:
            if group_id not in self._tasks or self._tasks[group_id].done():
                self.logger.info(f"启动 Group {group_id} 处理管道")
                task = asyncio.create_task(self._run_group_pipeline(group_id))
                self._tasks[group_id] = task
    
    def _should_sync_articles(self) -> bool:
        """
        判断是否应该同步文章
        
        Returns:
            是否应该同步文章
        """
        if self._last_sync_articles is None:
            return True
        
        elapsed = datetime.now() - self._last_sync_articles
        return elapsed >= timedelta(minutes=self.config.sync_articles_interval_minutes)
    
    def _should_sync_feeds(self) -> bool:
        """
        判断是否应该同步订阅源
        
        Returns:
            是否应该同步订阅源
        """
        if self._last_sync_feeds is None:
            return True
        
        elapsed = datetime.now() - self._last_sync_feeds
        return elapsed >= timedelta(minutes=self.config.sync_feeds_interval_minutes)
    
    def _should_check_groups(self) -> bool:
        """
        判断是否应该检查组触发
        
        Returns:
            是否应该检查组
        """
        if self._last_check_groups is None:
            return True
        
        elapsed = datetime.now() - self._last_check_groups
        return elapsed >= timedelta(minutes=self.config.check_groups_interval_minutes)
    
    async def _sync_articles_with_retry(self) -> bool:
        """
        同步文章（带重试）
        
        Returns:
            是否成功
        """
        from rss2pod.services.pipeline.group_processor import sync_fever_cache
        
        max_retries = self.config.retry_attempts
        retry_delay = self.config.retry_delay_seconds
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"[同步] 开始同步文章 (尝试 {attempt + 1}/{max_retries + 1})")
                result = sync_fever_cache(self.db.db_path, limit=1500)
                
                if result.success:
                    self._last_sync_articles = datetime.now()
                    self.logger.info(f"[同步] 文章同步成功，同步 {result.items_synced} 篇 (新增 {result.new_items}, 更新 {result.updated_items})")
                    return True
                else:
                    self.logger.warning(f"[同步] 文章同步失败：{result.error_message}")
                    
            except Exception as e:
                self.logger.warning(f"[同步] 文章同步异常 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            
            if attempt < max_retries:
                self.logger.info(f"[同步] {retry_delay}秒后重试...")
                await asyncio.sleep(retry_delay)
        
        self.logger.error("[同步] 文章同步失败，已达最大重试次数")
        return False
    
    async def _sync_feeds_with_retry(self) -> bool:
        """
        同步订阅源（带重试）
        
        Returns:
            是否成功
        """
        from fetcher.fever_client import FeverClient, FeverCredentials
        from fetcher.fever_cache import FeverCacheManager
        import hashlib
        import json
        
        max_retries = self.config.retry_attempts
        retry_delay = self.config.retry_delay_seconds
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"[同步] 开始同步订阅源 (尝试 {attempt + 1}/{max_retries + 1})")
                
                # 加载配置
                config_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'config.json'
                )
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                fever_config = config.get('fever', {})
                username = fever_config.get('username', '')
                password = fever_config.get('password', '')
                api_key = hashlib.md5(f"{username}:{password}".encode()).hexdigest()
                
                credentials = FeverCredentials(
                    api_url=fever_config.get('url', ''),
                    api_key=api_key
                )
                
                client = FeverClient(credentials, db_path=self.db.db_path)
                cache_manager = FeverCacheManager(self.db.db_path)
                
                # 同步订阅源
                feeds = client.get_feeds()
                cache_manager.sync_feeds(feeds)
                
                self._last_sync_feeds = datetime.now()
                self.logger.info(f"[同步] 订阅源同步成功，共 {len(feeds)} 个源")
                return True
                
            except Exception as e:
                self.logger.warning(f"[同步] 订阅源同步异常 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            
            if attempt < max_retries:
                self.logger.info(f"[同步] {retry_delay}秒后重试...")
                await asyncio.sleep(retry_delay)
        
        self.logger.error("[同步] 订阅源同步失败，已达最大重试次数")
        return False
    
    async def _check_and_run_tasks(self):
        """
        检查并执行任务（单一时钟驱动）
        
        任务优先级（互斥执行）：
        1. 检查组更新（优先级最高）
        2. 同步文章
        3. 同步订阅源
        """
        # 检查是否有任务正在执行
        async with self._task_lock:
            if self._current_task_type is not None:
                self.logger.debug(f"任务 {self._current_task_type.value} 正在执行，跳过本次检查")
                return
            
            now = datetime.now()
            
            # 优先级1：检查组更新
            if self._should_check_groups():
                self._current_task_type = TaskType.CHECK_GROUPS
                self._last_check_groups = now
                try:
                    await self._check_and_trigger_groups()
                finally:
                    self._current_task_type = None
                return
            
            # 优先级2：同步文章
            if self._should_sync_articles():
                self._current_task_type = TaskType.SYNC_ARTICLES
                self._last_sync_articles = now
                try:
                    await self._sync_articles_with_retry()
                finally:
                    self._current_task_type = None
                return
            
            # 优先级3：同步订阅源
            if self._should_sync_feeds():
                self._current_task_type = TaskType.SYNC_FEEDS
                self._last_sync_feeds = now
                try:
                    await self._sync_feeds_with_retry()
                finally:
                    self._current_task_type = None
                return
    
    async def _check_and_trigger_groups(self):
        """
        检查组触发并启动管道（内部并行）
        """
        triggered_groups = self._check_triggers()
        
        if not triggered_groups:
            self.logger.info("没有需要触发的 Group")
            return
        
        # 获取当前运行中的管道数量
        running_runs = self.state_manager.get_running_runs()
        running_count = len(running_runs)
        
        # 计算可启动的管道数量
        available_slots = self.config.max_concurrent_groups - running_count
        
        if available_slots <= 0:
            self.logger.debug(f"已达到最大并发数 ({running_count})，等待中...")
            return
        
        # 启动管道（限制并发数）
        groups_to_run = triggered_groups[:available_slots]
        
        for group_id in groups_to_run:
            if group_id not in self._tasks or self._tasks[group_id].done():
                self.logger.info(f"启动 Group {group_id} 处理管道")
                task = asyncio.create_task(self._run_group_pipeline(group_id))
                self._tasks[group_id] = task
    
    async def _scheduler_loop(self):
        """主调度循环（单一时钟架构）"""
        self.logger.info(f"调度器启动，检查间隔：{self.config.check_interval_seconds}秒")
        
        # 初始化首次同步时间
        self._last_sync_articles = datetime.now()
        self._last_sync_feeds = datetime.now()
        self._last_check_groups = datetime.now()
        
        while self.running:
            try:
                # 执行任务检查和触发
                await self._check_and_run_tasks()
                
                # 清理已完成的任务
                completed_tasks = [
                    group_id for group_id, task in self._tasks.items()
                    if task.done()
                ]
                for group_id in completed_tasks:
                    del self._tasks[group_id]
                
                # 等待下次检查
                await asyncio.sleep(self.config.check_interval_seconds)
                
            except asyncio.CancelledError:
                self.logger.info("调度循环被取消")
                break
            except Exception as e:
                self.logger.error(f"调度循环异常：{e}")
                await asyncio.sleep(self.config.check_interval_seconds)
    
    def start(self):
        """启动调度器（阻塞调用）"""
        self.logger.info("启动调度器...")
        self.running = True
        
        try:
            asyncio.run(self._scheduler_loop())
        except KeyboardInterrupt:
            self.logger.info("收到中断信号")
        # 注意：不再在这里调用 stop()，信号处理器会负责调用
        # 这样可以避免 stop() 被重复调用
    
    def start_background(self) -> asyncio.Task:
        """
        后台启动调度器
        
        Returns:
            调度器任务
        """
        self.running = True
        loop = asyncio.get_event_loop()
        task = loop.create_task(self._scheduler_loop())
        return task
    
    def stop(self):
        """停止调度器"""
        # 防止重复调用
        if self._is_stopping:
            return
        
        self._is_stopping = True
        self.logger.info("停止调度器...")
        self.running = False
        
        # 取消所有任务
        for group_id, task in self._tasks.items():
            if not task.done():
                task.cancel()
        
        self._shutdown_event.set()
        self.logger.info("调度器已停止")
        
        # 重置停止标志，以便下次启动
        self._is_stopping = False
    
    def run_once(self, group_id: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        单次运行（用于调试和手动触发）
        
        Args:
            group_id: 指定 Group ID，None 表示检查所有
            dry_run: 模拟运行
            
        Returns:
            运行结果字典
        """
        self.logger.info(f"单次运行 {'(模拟)' if dry_run else ''}")
        
        if group_id:
            groups_to_check = [group_id]
        else:
            groups_to_check = self._check_triggers()
        
        results = {}
        
        for gid in groups_to_check:
            if dry_run:
                self.logger.info(f"[模拟] Group {gid} 将触发")
                results[gid] = {"triggered": True, "dry_run": True}
            else:
                # 同步运行管道
                async def run_pipeline():
                    await self._run_group_pipeline(gid)
                
                try:
                    asyncio.run(run_pipeline())
                    results[gid] = {"triggered": True, "completed": True}
                except Exception as e:
                    results[gid] = {"triggered": True, "error": str(e)}
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取调度器状态
        
        Returns:
            状态字典
        """
        running_tasks = [
            group_id for group_id, task in self._tasks.items()
            if not task.done()
        ]
        
        return {
            "running": self.running,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "running_tasks": running_tasks,
            "task_count": len(running_tasks),
            "max_concurrent": self.config.max_concurrent_groups,
        }
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'db') and self.db:
            self.db.close()


def create_scheduler(
    config_path: Optional[str] = None,
    db_path: str = "rss2pod.db"
) -> Scheduler:
    """
    创建调度器实例
    
    Args:
        config_path: 配置文件路径
        db_path: 数据库文件路径
        
    Returns:
        Scheduler 实例
    """
    import json
    
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config.json'
        )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        full_config = json.load(f)
    
    orchestrator_config = full_config.get('orchestrator', {})
    log_config = full_config.get('logging', {})
    orchestrator_config['logging'] = log_config
    
    return Scheduler(orchestrator_config, db_path=db_path)


if __name__ == '__main__':
    # 测试调度器
    print("测试调度器...")
    
    # 创建测试配置
    test_config = {
        'check_interval_seconds': 5,
        'max_concurrent_groups': 2,
        'retry_attempts': 3,
        'retry_delay_seconds': 3,
        'dry_run': True,
        'logging': {
            'level': 'DEBUG',
            'file': 'logs/scheduler_test.log',
        }
    }
    
    scheduler = Scheduler(test_config)
    
    # 测试 cron 解析
    cron_expr = "0 9 * * *"
    next_run = scheduler._get_next_run_time(cron_expr)
    print(f"Cron 表达式：{cron_expr}")
    print(f"下次运行时间：{next_run}")
    
    # 测试触发器检查
    triggered = scheduler._check_triggers()
    print(f"需要触发的 Group: {triggered}")
    
    # 测试状态
    status = scheduler.get_status()
    print(f"调度器状态：{status}")
    
    print("\n调度器测试完成!")