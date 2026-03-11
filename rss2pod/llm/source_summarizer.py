#!/usr/bin/env python3
"""
Source Summarizer - Generate summaries for articles from the same RSS source
"""

import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.llm_client import LLMClient, create_llm_client


class Article:
    """Represents a single RSS article"""
    
    def __init__(self, title: str, content: str, link: str, published: Optional[datetime] = None):
        self.title = title
        self.content = content
        self.link = link
        self.published = published or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content[:500],  # Truncate for safety
            "link": self.link,
            "published": self.published.isoformat() if self.published else None
        }


class SourceSummarizer:
    """
    Generate summaries for articles from the same RSS source.
    Concatenates articles from one source and produces a unified summary.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None, source_name: str = "Unknown Source"):
        self.llm_client = llm_client or create_llm_client("mock")
        self.source_name = source_name
        self.articles: List[Article] = []
    
    def add_article(self, article: Article) -> None:
        """Add an article to the source"""
        self.articles.append(article)
    
    def add_articles(self, articles: List[Article]) -> None:
        """Add multiple articles"""
        self.articles.extend(articles)
    
    def clear_articles(self) -> None:
        """Clear all articles"""
        self.articles = []
    
    def _build_prompt(self, articles: List[Article]) -> str:
        """Build the summarization prompt"""
        articles_text = "\n\n".join([
            f"标题：{article.title}\n链接：{article.link}\n内容：{article.content}"
            for article in articles
        ])
        
        prompt = f"""你是专业的 RSS 内容摘要助手。请为以下来自同一 RSS 源（{self.source_name}）的文章生成综合摘要。

要求：
1. 提炼所有文章的核心主题和关键信息
2. 识别文章之间的关联性和共同话题
3. 用简洁清晰的中文总结，避免冗余
4. 保持客观，不添加原文没有的信息
5. 如果文章之间有矛盾或冲突的观点，请指出

文章列表（共 {len(articles)} 篇）：

{articles_text}

请按照以下 JSON 格式返回摘要：
{{
    "source_name": "源名称",
    "article_count": 文章数量，
    "summary": "综合摘要内容（200-500 字）",
    "key_topics": ["关键主题 1", "关键主题 2", ...],
    "highlights": ["重要亮点 1", "重要亮点 2", ...],
    "generated_at": "生成时间（ISO 格式）"
}}
"""
        return prompt
    
    def generate_summary(self, max_articles: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate summary for all articles from this source
        
        Args:
            max_articles: Maximum number of articles to include (uses most recent)
        
        Returns:
            Summary dictionary with source info and aggregated content
        """
        if not self.articles:
            return {
                "source_name": self.source_name,
                "article_count": 0,
                "summary": "没有文章可供摘要",
                "key_topics": [],
                "highlights": [],
                "generated_at": datetime.now().isoformat()
            }
        
        # Sort by published date (most recent first) and limit if needed
        sorted_articles = sorted(self.articles, key=lambda x: x.published or datetime.min, reverse=True)
        if max_articles:
            sorted_articles = sorted_articles[:max_articles]
        
        prompt = self._build_prompt(sorted_articles)
        
        try:
            summary = self.llm_client.generate_json(prompt)
            summary["source_name"] = self.source_name
            summary["article_count"] = len(sorted_articles)
            summary["generated_at"] = datetime.now().isoformat()
            return summary
        except Exception as e:
            # Fallback to basic summary
            return {
                "source_name": self.source_name,
                "article_count": len(sorted_articles),
                "summary": f"来自 {self.source_name} 的 {len(sorted_articles)} 篇文章。由于处理错误，无法生成详细摘要。",
                "key_topics": [article.title for article in sorted_articles[:5]],
                "highlights": [],
                "generated_at": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def get_article_text_concat(self, separator: str = "\n\n---\n\n") -> str:
        """Get concatenated text of all articles"""
        return separator.join([
            f"【{article.title}】\n{article.content}"
            for article in self.articles
        ])


def summarize_source(
    source_name: str,
    articles_data: List[Dict[str, Any]],
    llm_provider: str = "mock"
) -> Dict[str, Any]:
    """
    Convenience function to summarize a source's articles
    
    Args:
        source_name: Name of the RSS source
        articles_data: List of article dictionaries with title, content, link, published
        llm_provider: LLM provider to use
    
    Returns:
        Summary dictionary
    """
    llm_client = create_llm_client(llm_provider)
    summarizer = SourceSummarizer(llm_client, source_name)
    
    for article_data in articles_data:
        article = Article(
            title=article_data.get("title", "Untitled"),
            content=article_data.get("content", ""),
            link=article_data.get("link", ""),
            published=datetime.fromisoformat(article_data["published"]) if article_data.get("published") else None
        )
        summarizer.add_article(article)
    
    return summarizer.generate_summary()


if __name__ == "__main__":
    # Test the summarizer
    print("Testing Source Summarizer...")
    
    # Create test articles
    test_articles = [
        Article("AI 技术新突破", "人工智能领域今日宣布重大突破，新的模型架构显著提升了推理效率...", "https://example.com/1"),
        Article("机器学习应用", "机器学习在医疗领域的应用取得进展，新算法能够更早发现疾病...", "https://example.com/2"),
        Article("科技前沿", "本周科技热点：量子计算、AI 助手、自动驾驶等前沿技术动态...", "https://example.com/3")
    ]
    
    summarizer = SourceSummarizer(create_llm_client("mock"), "Tech News")
    summarizer.add_articles(test_articles)
    
    summary = summarizer.generate_summary()
    print(f"Source: {summary['source_name']}")
    print(f"Articles: {summary['article_count']}")
    print(f"Summary: {summary['summary']}")
    print(f"Topics: {summary['key_topics']}")
    
    print("\nSource Summarizer module loaded successfully!")
