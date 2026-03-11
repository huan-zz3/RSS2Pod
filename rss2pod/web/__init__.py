"""
RSS2Pod Web 模块

提供 Web 管理界面和 RSS 订阅服务。
"""

from .app import create_app, start_server

__all__ = [
    'create_app',
    'start_server',
]
