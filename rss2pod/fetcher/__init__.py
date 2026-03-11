"""
RSS2Pod Fetcher Module
RSS 采集模块 - 用于从 Fever API 获取文章
"""

from .fever_client import FeverClient, FeverCredentials
from .article_manager import (
    ArticleManager, 
    Article, 
    ArticleStatus,
    ArticleConcatenator
)

__version__ = '0.1.0'
__all__ = [
    'FeverClient',
    'FeverCredentials',
    'ArticleManager',
    'Article',
    'ArticleStatus',
    'ArticleConcatenator',
]
