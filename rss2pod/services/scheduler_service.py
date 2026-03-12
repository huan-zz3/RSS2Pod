"""
调度器服务 - 封装调度器相关操作
"""

import os
import sys
import asyncio
from typing import Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult


class SchedulerService(BaseService):
    """
    调度器服务
    
    提供调度器相关的业务逻辑封装
    """
    
    # 全局运行状态
    _running = False
    _scheduler_task = None
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        super().__init__(config_path, db_path)
    
    def start(self) -> ServiceResult:
        """
        启动调度器（后台运行）
        
        Returns:
            ServiceResult 实例
        """
        try:
            if SchedulerService._running:
                return ServiceResult(
                    success=False,
                    error_message='调度器已在运行中'
                )
            
            SchedulerService._running = True
            
            # 在后台启动调度器
            async def run_scheduler():
                from orchestrator.scheduler import Scheduler
                
                orchestrator_config = self.config.get('orchestrator', {})
                log_config = self.config.get('logging', {})
                orchestrator_config['logging'] = log_config
                
                scheduler = Scheduler(
                    orchestrator_config,
                    db_path=self.db.db_path if self.db else 'rss2pod.db'
                )
                
                try:
                    await scheduler.start_async()
                except asyncio.CancelledError:
                    pass
                finally:
                    await scheduler.stop()
            
            # 创建后台任务
            SchedulerService._scheduler_task = asyncio.create_task(run_scheduler())
            
            return ServiceResult(
                success=True,
                data={
                    'started': True,
                    'check_interval': self.config.get('orchestrator', {}).get('check_interval_seconds', 60),
                    'max_concurrent': self.config.get('orchestrator', {}).get('max_concurrent_groups', 3)
                }
            )
        except Exception as e:
            SchedulerService._running = False
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def stop(self) -> ServiceResult:
        """
        停止调度器
        
        Returns:
            ServiceResult 实例
        """
        try:
            if not SchedulerService._running:
                return ServiceResult(
                    success=False,
                    error_message='调度器未运行'
                )
            
            SchedulerService._running = False
            
            # 取消后台任务
            if SchedulerService._scheduler_task:
                SchedulerService._scheduler_task.cancel()
                try:
                    asyncio.get_event_loop().run_until_complete(SchedulerService._scheduler_task)
                except asyncio.CancelledError:
                    pass
                SchedulerService._scheduler_task = None
            
            return ServiceResult(
                success=True,
                data={'stopped': True}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_status(self) -> ServiceResult:
        """
        获取调度器状态
        
        Returns:
            ServiceResult 实例
        """
        try:
            from orchestrator.state_manager import StateManager
            
            state_manager = StateManager(self.db)
            stats = state_manager.get_stats()
            
            # 获取启用的 Group
            groups = self.db.get_all_groups(enabled_only=True)
            enabled_groups = []
            for group in groups[:10]:  # 只显示前 10 个
                trigger_config = group.trigger_config or {}
                enabled_groups.append({
                    'id': group.id,
                    'name': group.name,
                    'cron': trigger_config.get('cron', 'N/A')
                })
            
            return ServiceResult(
                success=True,
                data={
                    'running': SchedulerService._running,
                    'states_by_status': stats.get('states_by_status', {}),
                    'running_pipelines': stats.get('running_pipelines', 0),
                    'runs_today': stats.get('runs_today', 0),
                    'enabled_groups_count': len(groups),
                    'enabled_groups': enabled_groups
                }
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def run_once(self, group_id: Optional[str] = None, verbose: bool = False) -> ServiceResult:
        """
        手动触发一次调度
        
        Args:
            group_id: 可选，指定 Group ID（不指定则触发所有启用的组）
            verbose: 是否显示详细日志（DEBUG 级别）
            
        Returns:
            ServiceResult 实例
        """
        try:
            from rss2pod.services.pipeline.group_processor import process_group_sync
            from orchestrator.logging_config import setup_logging
            
            # 设置日志级别
            log_level = "DEBUG" if verbose else "INFO"
            setup_logging(level=log_level)
            
            results = []
            
            if group_id:
                # 处理指定 Group
                group = self.db.get_group(group_id)
                if not group:
                    return ServiceResult(
                        success=False,
                        error_message=f'Group {group_id} 不存在'
                    )
                
                result = process_group_sync(group_id, self.db.db_path)
                results.append({
                    'group_id': group_id,
                    'success': result.success,
                    'episode_id': result.episode_id,
                    'error_message': result.error_message
                })
            else:
                # 处理所有启用的 Group
                groups = self.db.get_all_groups(enabled_only=True)
                
                if not groups:
                    return ServiceResult(
                        success=False,
                        error_message='没有启用的 Group'
                    )
                
                for group in groups:
                    result = process_group_sync(group.id, self.db.db_path)
                    results.append({
                        'group_id': group.id,
                        'success': result.success,
                        'episode_id': result.episode_id,
                        'error_message': result.error_message
                    })
            
            success_count = sum(1 for r in results if r['success'])
            fail_count = len(results) - success_count
            
            return ServiceResult(
                success=True,
                data={
                    'results': results,
                    'success_count': success_count,
                    'fail_count': fail_count
                }
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def trigger_generation(self, group_id: str, force: bool = False, export_articles: bool = False, verbose: bool = False) -> ServiceResult:
        """
        触发生成播客期数
        
        Args:
            group_id: Group ID
            force: 强制模式，忽略文章更新检查
            export_articles: 导出文章列表到 JSON 文件
            verbose: 是否显示详细日志（DEBUG 级别）
            
        Returns:
            ServiceResult 实例
        """
        try:
            from rss2pod.services.pipeline.group_processor import process_group_sync
            from orchestrator.logging_config import setup_logging
            
            # 设置日志级别
            log_level = "DEBUG" if verbose else "INFO"
            setup_logging(level=log_level)
            
            group = self.db.get_group(group_id)
            if not group:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 不存在'
                )
            
            result = process_group_sync(
                group_id,
                self.db.db_path,
                force=force,
                export_articles=export_articles
            )
            
            if result.success:
                return ServiceResult(
                    success=True,
                    data={
                        'episode_id': result.episode_id,
                        'stages_completed': result.stages_completed,
                        'articles_fetched': result.articles_fetched
                    }
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message=result.error_message,
                    data={
                        'failed_stage': result.failed_stage
                    }
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_generation_history(self, group_id: Optional[str] = None, limit: int = 50) -> ServiceResult:
        """
        获取生成历史
        
        Args:
            group_id: 可选，指定 Group ID
            limit: 最大返回数量
            
        Returns:
            ServiceResult 实例
        """
        try:
            if group_id:
                episodes = self.db.get_episodes_by_group(group_id, limit)
            else:
                cursor = self.db.conn.cursor()
                cursor.execute('SELECT * FROM episodes ORDER BY created_at DESC LIMIT ?', (limit,))
                episodes = [self.db._row_to_episode(row) for row in cursor.fetchall()]
            
            return ServiceResult(
                success=True,
                data=[ep.to_dict() for ep in episodes],
                metadata={'count': len(episodes)}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def test_trigger(self, group_id: str) -> ServiceResult:
        """
        测试触发条件（不实际执行）
        
        Args:
            group_id: Group ID
            
        Returns:
            ServiceResult 实例，包含触发条件诊断信息
        """
        try:
            # 获取 Group 信息
            group = self.db.get_group(group_id)
            if not group:
                return ServiceResult(
                    success=False,
                    error_message=f'Group {group_id} 不存在'
                )
            
            trigger_config = group.trigger_config or {}
            trigger_type = group.trigger_type
            
            result_data = {
                'group_id': group.id,
                'group_name': group.name,
                'enabled': group.enabled,
                'trigger_type': trigger_type,
                'trigger_config': trigger_config,
            }
            
            # 如果 Group 未启用
            if not group.enabled:
                result_data['will_trigger'] = False
                result_data['reason'] = 'Group 已禁用'
                return ServiceResult(success=True, data=result_data)
            
            # 检查 cron 触发条件
            cron_expr = trigger_config.get('cron')
            cron_will_trigger = False
            cron_next_run = None
            cron_remaining = None
            
            if cron_expr and trigger_type in ['time', 'combined']:
                try:
                    from croniter import croniter
                    cron = croniter(cron_expr, datetime.now())
                    cron_next_run = cron.get_next(datetime)
                    now = datetime.now()
                    
                    if cron_next_run and cron_next_run <= now:
                        cron_will_trigger = True
                    else:
                        # 计算剩余时间
                        if cron_next_run:
                            delta = cron_next_run - now
                            hours, remainder = divmod(int(delta.total_seconds()), 3600)
                            minutes = remainder // 60
                            cron_remaining = f'{hours}小时{minutes}分钟'
                except Exception:
                    pass
            
            result_data['cron'] = {
                'expression': cron_expr,
                'will_trigger': cron_will_trigger,
                'next_run': cron_next_run.isoformat() if cron_next_run else None,
                'remaining': cron_remaining,
            }
            
            # 检查数量触发条件
            threshold = trigger_config.get('threshold', 0)
            count_will_trigger = False
            current_count = 0
            
            if threshold > 0 and trigger_type in ['count', 'combined']:
                # 查询未处理文章数量
                if group.rss_sources:
                    placeholders = ','.join(['?' for _ in group.rss_sources])
                    cursor = self.db.conn.cursor()
                    cursor.execute(f'''
                        SELECT COUNT(*) FROM articles 
                        WHERE source IN ({placeholders})
                        AND status = 'pending'
                    ''', group.rss_sources)
                    current_count = cursor.fetchone()[0]
                    
                    if current_count >= threshold:
                        count_will_trigger = True
            
            result_data['count'] = {
                'threshold': threshold,
                'current': current_count,
                'will_trigger': count_will_trigger,
                'remaining': threshold - current_count if current_count < threshold else 0,
            }
            
            # 综合判断
            will_trigger = False
            reasons = []
            
            if trigger_type == 'time':
                will_trigger = cron_will_trigger
                if not cron_expr:
                    reasons.append('未配置 Cron 表达式')
                elif cron_will_trigger:
                    reasons.append('Cron 触发时间已到')
                else:
                    reasons.append(f'Cron 触发时间未到 (还差 {cron_remaining})')
            elif trigger_type == 'count':
                will_trigger = count_will_trigger
                if threshold <= 0:
                    reasons.append('未配置数量阈值')
                elif count_will_trigger:
                    reasons.append(f'文章数量已达到阈值 ({current_count} >= {threshold})')
                else:
                    reasons.append(f'文章数量未达阈值 ({current_count} < {threshold})')
            elif trigger_type == 'combined':
                will_trigger = cron_will_trigger or count_will_trigger
                if cron_will_trigger:
                    reasons.append('Cron 触发时间已到')
                elif count_will_trigger:
                    reasons.append(f'文章数量已达到阈值 ({current_count} >= {threshold})')
                else:
                    if cron_remaining:
                        reasons.append(f'Cron 触发时间未到 (还差 {cron_remaining})')
                    reasons.append(f'文章数量未达阈值 ({current_count} < {threshold})')
            
            result_data['will_trigger'] = will_trigger
            result_data['reasons'] = reasons
            
            return ServiceResult(success=True, data=result_data)
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
