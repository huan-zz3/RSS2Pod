#!/usr/bin/env python3
"""
日志配置模块

提供结构化的日志记录功能，支持：
- 控制台输出（stdout）
- 文件输出（支持轮转）
- 自定义日志级别
- JSON 格式化（可选）
"""

import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
from typing import Optional, Dict, Any


# 日志格式
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DETAILED_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
JSON_LOG_FORMAT = '{"timestamp": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台格式化器"""
    
    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m',       # 重置
    }
    
    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        color = self.COLORS.get(levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # 格式化时间
        asctime = self.formatTime(record, self.datefmt)
        
        # 构建日志消息
        message = f"{color}{asctime} - {record.name} - {levelname}{reset} - {record.getMessage()}"
        
        if record.exc_info:
            message += '\n' + self.formatException(record.exc_info)
        
        return message


class OrchestratorLogger(logging.Logger):
    """自定义日志记录器，支持 Group 上下文"""
    
    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs):
        """设置日志上下文"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """清除日志上下文"""
        self.context.clear()
    
    def process(self, msg: str, kwargs: Any) -> tuple:
        """处理日志消息，添加上下文信息"""
        if self.context:
            context_str = ' '.join(f"[{k}={v}]" for k, v in self.context.items())
            msg = f"{context_str} {msg}"
        return msg, kwargs


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = DEFAULT_LOG_FORMAT,
    rotation: str = "daily",
    retention_days: int = 7,
    use_colors: bool = True,
) -> logging.Logger:
    """
    配置日志系统
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，None 表示仅输出到控制台
        log_format: 日志格式字符串
        rotation: 日志轮转类型 (daily, hourly, weekly, monthly)
        retention_days: 日志保留天数
        use_colors: 是否在控制台使用颜色输出
        
    Returns:
        配置好的 logger 实例
    """
    # 配置根 logger，使所有子 logger 都能继承 handler
    root_logger = logging.getLogger('rss2pod')
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # 清除根 logger 的 handlers
    root_logger.handlers.clear()
    
    # 清除所有 rss2pod 相关子 logger 的 handlers，避免重复输出
    # 这样可以确保只有根 logger 的 handler 输出日志，子 logger 通过 propagate 机制传递
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name.startswith('rss2pod') and name != 'rss2pod':
            logger = logging.getLogger(name)
            logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    if use_colors:
        console_formatter = ColoredFormatter(log_format)
    else:
        console_formatter = logging.Formatter(log_format)
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 根据轮转类型设置后缀
        when_map = {
            'hourly': 'H',
            'daily': 'D',
            'weekly': 'W0',  # 周一
            'monthly': 'M1',  # 每月 1 号
        }
        when = when_map.get(rotation.lower(), 'D')
        
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when=when,
            interval=1,
            backupCount=retention_days,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)
    
    # 返回 orchestrator logger
    logger = logging.getLogger('rss2pod.orchestrator')
    return logger


def get_logger(name: str = 'rss2pod.orchestrator') -> logging.Logger:
    """
    获取 logger 实例
    
    注意：这个函数不再给子 logger 添加 handler。
    所有日志通过 propagate 机制传递到根 logger 输出，
    这样可以避免重复输出问题。
    
    Args:
        name: logger 名称
        
    Returns:
        logger 实例
    """
    logger = logging.getLogger(name)
    
    # 不再给子 logger 添加 handler
    # 让日志通过 propagate 机制传递到根 logger 输出
    # 这样可以避免日志重复输出
    
    return logger


def log_pipeline_stage(
    logger: logging.Logger,
    stage: str,
    group_id: str,
    message: str,
    level: str = "INFO",
    **extra: Any
):
    """
    记录管道阶段日志
    
    Args:
        logger: logger 实例
        stage: 当前阶段名称
        group_id: Group ID
        message: 日志消息
        level: 日志级别
        extra: 额外字段
    """
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(f"[{stage}] [Group:{group_id}] {message}", extra=extra)


# 模块级便捷函数
_default_logger: Optional[logging.Logger] = None


def init_default_logger(config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    初始化默认 logger
    
    Args:
        config: 日志配置字典
        
    Returns:
        默认 logger 实例
    """
    global _default_logger
    
    if config is None:
        config = {
            'level': 'INFO',
            'file': 'logs/orchestrator.log',
            'format': DEFAULT_LOG_FORMAT,
            'rotation': 'daily',
            'retention_days': 7,
        }
    
    _default_logger = setup_logging(
        level=config.get('level', 'INFO'),
        log_file=config.get('file'),
        log_format=config.get('format', DEFAULT_LOG_FORMAT),
        rotation=config.get('rotation', 'daily'),
        retention_days=config.get('retention_days', 7),
    )
    
    return _default_logger


def get_default_logger() -> logging.Logger:
    """获取默认 logger 实例"""
    global _default_logger
    if _default_logger is None:
        _default_logger = logging.getLogger('rss2pod.orchestrator')
    return _default_logger


if __name__ == '__main__':
    # 测试日志系统
    logger = setup_logging(
        level='DEBUG',
        log_file='logs/test.log',
        use_colors=True
    )
    
    logger.debug("这是一条调试消息")
    logger.info("这是一条信息消息")
    logger.warning("这是一条警告消息")
    logger.error("这是一条错误消息")
    logger.critical("这是一条严重错误消息")
    
    # 测试上下文
    log_pipeline_stage(logger, 'fetch', 'test-group', '开始获取文章')
    log_pipeline_stage(logger, 'summarize', 'test-group', '开始生成摘要', extra={'article_count': 5})
    
    print("\n日志系统测试完成!")