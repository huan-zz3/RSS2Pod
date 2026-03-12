"""
Article Manager - 文章存储与管理
负责文章的存储、检索、状态管理和拼接策略
"""

import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import hashlib
from pathlib import Path


class ArticleStatus(Enum):
    """文章处理状态"""
    PENDING = "pending"  # 待处理
    FETCHED = "fetched"  # 已获取
    PROCESSING = "processing"  # 处理中
    PROCESSED = "processed"  # 已处理
    FAILED = "failed"  # 处理失败
    SKIPPED = "skipped"  # 已跳过


@dataclass
class Article:
    """文章数据结构"""
    id: str  # 唯一标识（hash）
    title: str
    source: str  # 归属源
    source_url: str  # 源 URL
    link: str  # 原文链接
    published: str  # 发布时间（ISO 格式）
    content: str  # 正文内容
    text_content: str  # 纯文本内容
    author: str = ""
    summary: str = ""
    status: str = ArticleStatus.PENDING.value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    processed_at: Optional[str] = None
    error_message: Optional[str] = None
    token_count: int = 0  # token 数量（估算）
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Article':
        """从字典创建"""
        return cls(**data)
    
    @classmethod
    def generate_id(cls, title: str, link: str, source: str) -> str:
        """
        生成文章唯一 ID
        
        Args:
            title: 标题
            link: 链接
            source: 源
            
        Returns:
            MD5 哈希 ID
        """
        key = f"{title}:{link}:{source}"
        return hashlib.md5(key.encode('utf-8')).hexdigest()
    
    def estimate_tokens(self) -> int:
        """
        估算 token 数量（简单估算：中文字符数 + 英文字符数/4）
        
        Returns:
            估算的 token 数量
        """
        text = self.text_content or self.content
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len([c for c in text if c not in '\n\r\t '])
        
        # 粗略估算：1 个中文字符≈1.5 tokens, 4 个英文字符≈1 token
        self.token_count = int(chinese_chars * 1.5 + other_chars * 0.25)
        return self.token_count
    
    def mark_processed(self):
        """标记为已处理"""
        self.status = ArticleStatus.PROCESSED.value
        self.processed_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def mark_failed(self, error: str):
        """标记为失败"""
        self.status = ArticleStatus.FAILED.value
        self.error_message = error
        self.updated_at = datetime.now().isoformat()


class ArticleManager:
    """文章管理器"""
    
    def __init__(self, storage_dir: str = "articles"):
        """
        初始化文章管理器
        
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 文章索引文件
        self.index_file = self.storage_dir / "index.json"
        self.articles: Dict[str, Article] = {}
        
        # 按源分组
        self.articles_by_source: Dict[str, List[str]] = {}  # source -> [article_ids]
        
        # 加载现有索引
        self._load_index()
    
    def _load_index(self):
        """加载文章索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.articles_by_source = data.get('by_source', {})
                    
                    # 加载每篇文章
                    for article_id in data.get('articles', []):
                        article_file = self.storage_dir / f"{article_id}.json"
                        if article_file.exists():
                            with open(article_file, 'r', encoding='utf-8') as af:
                                article_data = json.load(af)
                                self.articles[article_id] = Article.from_dict(article_data)
            except Exception as e:
                print(f"加载索引失败：{e}")
                self.articles = {}
                self.articles_by_source = {}
    
    def _save_index(self):
        """保存文章索引"""
        try:
            data = {
                'articles': list(self.articles.keys()),
                'by_source': self.articles_by_source,
                'updated_at': datetime.now().isoformat()
            }
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存索引失败：{e}")
    
    def _save_article(self, article: Article):
        """保存单篇文章"""
        article_file = self.storage_dir / f"{article.id}.json"
        with open(article_file, 'w', encoding='utf-8') as f:
            json.dump(article.to_dict(), f, ensure_ascii=False, indent=2)
    
    def add_article(self, article: Article) -> str:
        """
        添加文章
        
        Args:
            article: 文章对象
            
        Returns:
            文章 ID
        """
        self.articles[article.id] = article
        
        # 添加到源的索引
        if article.source not in self.articles_by_source:
            self.articles_by_source[article.source] = []
        
        if article.id not in self.articles_by_source[article.source]:
            self.articles_by_source[article.source].append(article.id)
        
        # 保存
        self._save_article(article)
        self._save_index()
        
        return article.id
    
    def add_articles(self, articles: List[Article]) -> List[str]:
        """
        批量添加文章
        
        Args:
            articles: 文章列表
            
        Returns:
            文章 ID 列表
        """
        ids = []
        for article in articles:
            article_id = self.add_article(article)
            ids.append(article_id)
        return ids
    
    def get_article(self, article_id: str) -> Optional[Article]:
        """
        获取文章
        
        Args:
            article_id: 文章 ID
            
        Returns:
            文章对象，不存在返回 None
        """
        return self.articles.get(article_id)
    
    def get_articles_by_source(self, source: str, 
                                status: Optional[ArticleStatus] = None,
                                limit: Optional[int] = None) -> List[Article]:
        """
        按源获取文章
        
        Args:
            source: 源名称
            status: 状态过滤（可选）
            limit: 数量限制（可选）
            
        Returns:
            文章列表
        """
        article_ids = self.articles_by_source.get(source, [])
        articles = []
        
        for article_id in article_ids:
            article = self.articles.get(article_id)
            if article:
                if status is None or article.status == status.value:
                    articles.append(article)
        
        # 按发布时间排序（最新的在前）
        articles.sort(key=lambda a: a.published, reverse=True)
        
        if limit:
            articles = articles[:limit]
        
        return articles
    
    def get_pending_articles(self, limit: Optional[int] = None) -> List[Article]:
        """
        获取待处理的文章
        
        Args:
            limit: 数量限制
            
        Returns:
            文章列表
        """
        return self.get_articles_by_status(ArticleStatus.PENDING, limit)
    
    def get_articles_by_status(self, status: ArticleStatus,
                                limit: Optional[int] = None) -> List[Article]:
        """
        按状态获取文章
        
        Args:
            status: 状态
            limit: 数量限制
            
        Returns:
            文章列表
        """
        articles = []
        for article in self.articles.values():
            if article.status == status.value:
                articles.append(article)
        
        # 按创建时间排序
        articles.sort(key=lambda a: a.created_at, reverse=True)
        
        if limit:
            articles = articles[:limit]
        
        return articles
    
    def update_article(self, article: Article):
        """
        更新文章
        
        Args:
            article: 文章对象
        """
        article.updated_at = datetime.now().isoformat()
        self.articles[article.id] = article
        self._save_article(article)
        self._save_index()
    
    def delete_article(self, article_id: str) -> bool:
        """
        删除文章
        
        Args:
            article_id: 文章 ID
            
        Returns:
            是否删除成功
        """
        if article_id not in self.articles:
            return False
        
        article = self.articles[article_id]
        
        # 从源的索引中移除
        if article.source in self.articles_by_source:
            if article_id in self.articles_by_source[article.source]:
                self.articles_by_source[article.source].remove(article_id)
        
        # 删除文件
        article_file = self.storage_dir / f"{article_id}.json"
        if article_file.exists():
            article_file.unlink()
        
        # 从内存中移除
        del self.articles[article_id]
        self._save_index()
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计字典
        """
        stats = {
            'total': len(self.articles),
            'by_source': {},
            'by_status': {},
            'total_tokens': 0
        }
        
        for source, ids in self.articles_by_source.items():
            stats['by_source'][source] = len(ids)
        
        for article in self.articles.values():
            status = article.status
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            stats['total_tokens'] += article.token_count
        
        return stats
    
    def clear_old_articles(self, days: int = 30):
        """
        清理旧文章
        
        Args:
            days: 保留最近多少天的文章
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        to_delete = []
        for article_id, article in self.articles.items():
            created = datetime.fromisoformat(article.created_at).timestamp()
            if created < cutoff:
                to_delete.append(article_id)
        
        for article_id in to_delete:
            self.delete_article(article_id)
        
        return len(to_delete)


class ArticleConcatenator:
    """文章拼接器 - 实现文章拼接策略"""
    
    def __init__(self, max_tokens: int = 4000):
        """
        初始化拼接器
        
        Args:
            max_tokens: 最大 token 数量限制
        """
        self.max_tokens = max_tokens
    
    def concatenate_articles(self, articles: List[Article], 
                             source: str,
                             include_metadata: bool = True) -> str:
        """
        拼接同一源的多篇文章
        
        Args:
            articles: 文章列表（按时间正序排列）
            source: 源名称
            include_metadata: 是否包含元数据
            
        Returns:
            拼接后的文本
        """
        if not articles:
            return ""
        
        parts = []
        current_tokens = 0
        
        # 添加标题
        if include_metadata:
            header = f"# {source} 文章合集\n"
            header += f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            header += f"文章数量：{len(articles)}\n\n"
            header_tokens = int(len(header) * 0.5)  # 粗略估算
            current_tokens += header_tokens
            parts.append(header)
        
        # 逐篇添加文章
        for i, article in enumerate(articles):
            # 估算文章 token 数
            article_tokens = article.estimate_tokens()
            
            # 检查是否超出限制
            if current_tokens + article_tokens > self.max_tokens:
                print(f"达到 token 上限 ({self.max_tokens})，已包含 {i} 篇文章")
                break
            
            # 添加文章分隔符
            if i > 0:
                separator = "\n" + "=" * 50 + "\n\n"
                parts.append(separator)
            
            # 添加文章元数据
            if include_metadata:
                meta = f"## {article.title}\n"
                meta += f"发布时间：{article.published}\n"
                if article.author:
                    meta += f"作者：{article.author}\n"
                meta += f"链接：{article.link}\n\n"
                parts.append(meta)
            
            # 添加文章内容
            content = article.text_content or article.content
            parts.append(content)
            parts.append("\n\n")
            
            current_tokens += article_tokens
        
        return "".join(parts)
    
    def concatenate_with_strategy(self, 
                                   articles: List[Article],
                                   source: str,
                                   strategy: str = 'chronological',
                                   max_articles: Optional[int] = None) -> str:
        """
        使用不同策略拼接文章
        
        Args:
            articles: 文章列表
            source: 源名称
            strategy: 策略 ('chronological', 'reverse_chronological', 'by_length')
            max_articles: 最大文章数量
            
        Returns:
            拼接后的文本
        """
        # 应用排序策略
        if strategy == 'chronological':
            sorted_articles = sorted(articles, key=lambda a: a.published)
        elif strategy == 'reverse_chronological':
            sorted_articles = sorted(articles, key=lambda a: a.published, reverse=True)
        elif strategy == 'by_length':
            sorted_articles = sorted(articles, key=lambda a: len(a.text_content))
        else:
            sorted_articles = articles
        
        # 应用数量限制
        if max_articles:
            sorted_articles = sorted_articles[:max_articles]
        
        return self.concatenate_articles(sorted_articles, source)


# 使用示例
if __name__ == '__main__':
    # 示例：管理文章
    # manager = ArticleManager(storage_dir="my_articles")
    # 
    # # 添加文章
    # article = Article(
    #     id=Article.generate_id("标题", "链接", "源"),
    #     title="示例文章",
    #     source="测试源",
    #     source_url="https://example.com",
    #     link="https://example.com/article",
    #     published=datetime.now().isoformat(),
    #     content="<p>内容</p>",
    #     text_content="纯文本内容"
    # )
    # manager.add_article(article)
    # 
    # # 获取文章
    # articles = manager.get_articles_by_source("测试源")
    # 
    # # 拼接文章
    # concatenator = ArticleConcatenator(max_tokens=4000)
    # combined = concatenator.concatenate_articles(articles, "测试源")
    # print(combined)
    pass
