#!/usr/bin/env python3
"""
Group Aggregator - Merge all source-level summaries into a group summary
"""

import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.llm_client import LLMClient, create_llm_client


class SourceSummary:
    """Represents a summary from one RSS source"""
    
    def __init__(
        self,
        source_name: str,
        summary: str,
        article_count: int,
        key_topics: List[str],
        highlights: List[str],
        generated_at: str
    ):
        self.source_name = source_name
        self.summary = summary
        self.article_count = article_count
        self.key_topics = key_topics
        self.highlights = highlights
        self.generated_at = generated_at
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceSummary":
        return cls(
            source_name=data.get("source_name", "Unknown"),
            summary=data.get("summary", ""),
            article_count=data.get("article_count", 0),
            key_topics=data.get("key_topics", []),
            highlights=data.get("highlights", []),
            generated_at=data.get("generated_at", datetime.now().isoformat())
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "summary": self.summary,
            "article_count": self.article_count,
            "key_topics": self.key_topics,
            "highlights": self.highlights,
            "generated_at": self.generated_at
        }


class GroupAggregator:
    """
    Aggregate summaries from multiple RSS sources into a unified group summary.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None, group_name: str = "RSS Group"):
        self.llm_client = llm_client or create_llm_client("mock")
        self.group_name = group_name
        self.source_summaries: List[SourceSummary] = []
    
    def add_source_summary(self, summary: SourceSummary) -> None:
        """Add a source summary to the group"""
        self.source_summaries.append(summary)
    
    def add_source_summaries(self, summaries: List[SourceSummary]) -> None:
        """Add multiple source summaries"""
        self.source_summaries.extend(summaries)
    
    def clear_summaries(self) -> None:
        """Clear all source summaries"""
        self.source_summaries = []
    
    def _build_prompt(self, summaries: List[SourceSummary]) -> str:
        """Build the aggregation prompt"""
        sources_text = "\n\n".join([
            f"### {summary.source_name} ({summary.article_count} 篇文章)\n"
            f"关键主题：{', '.join(summary.key_topics) if summary.key_topics else '无'}\n"
            f"摘要：{summary.summary}\n"
            f"亮点：{', '.join(summary.highlights) if summary.highlights else '无'}"
            for summary in summaries
        ])
        
        total_articles = sum(s.article_count for s in summaries)
        
        prompt = f"""你是专业的 RSS 内容聚合助手。请将以下多个 RSS 源的摘要整合成一份综合报告。

群组名称：{self.group_name}
源数量：{len(summaries)}
文章总数：{total_articles}

各源摘要：

{sources_text}

要求：
1. 整合所有源的信息，形成连贯的综合摘要
2. 识别跨源的共同主题和趋势
3. 突出最重要的新闻和洞察
4. 保持结构清晰，便于快速浏览
5. 指出不同源之间的观点差异或互补信息

请按照以下 JSON 格式返回聚合结果：
{{
    "group_name": "群组名称",
    "source_count": 源数量，
    "total_articles": 文章总数，
    "executive_summary": "执行摘要（100-200 字，概述整体内容）",
    "full_summary": "完整摘要（500-1000 字，详细内容）",
    "cross_source_themes": ["跨源主题 1", "跨源主题 2", ...],
    "top_highlights": ["最重要亮点 1", "最重要亮点 2", ...],
    "sources_breakdown": [
        {{"name": "源名称", "article_count": 数量，"key_topics": ["主题"]}}
    ],
    "generated_at": "生成时间（ISO 格式）"
}}
"""
        return prompt
    
    def aggregate(self, top_n: Optional[int] = None) -> Dict[str, Any]:
        """
        Aggregate all source summaries into a group summary
        
        Args:
            top_n: Only include top N sources by article count (if specified)
        
        Returns:
            Aggregated group summary dictionary
        """
        if not self.source_summaries:
            return {
                "group_name": self.group_name,
                "source_count": 0,
                "total_articles": 0,
                "executive_summary": "没有源摘要可供聚合",
                "full_summary": "",
                "cross_source_themes": [],
                "top_highlights": [],
                "sources_breakdown": [],
                "generated_at": datetime.now().isoformat()
            }
        
        # Sort by article count and limit if needed
        sorted_summaries = sorted(
            self.source_summaries,
            key=lambda x: x.article_count,
            reverse=True
        )
        if top_n:
            sorted_summaries = sorted_summaries[:top_n]
        
        prompt = self._build_prompt(sorted_summaries)
        
        try:
            result = self.llm_client.generate_json(prompt)
            result["group_name"] = self.group_name
            result["source_count"] = len(sorted_summaries)
            result["total_articles"] = sum(s.article_count for s in sorted_summaries)
            result["generated_at"] = datetime.now().isoformat()
            
            # Ensure sources_breakdown is populated
            if "sources_breakdown" not in result:
                result["sources_breakdown"] = [
                    {"name": s.source_name, "article_count": s.article_count, "key_topics": s.key_topics}
                    for s in sorted_summaries
                ]
            
            return result
        except Exception as e:
            # Fallback to basic aggregation
            return {
                "group_name": self.group_name,
                "source_count": len(sorted_summaries),
                "total_articles": sum(s.article_count for s in sorted_summaries),
                "executive_summary": f"聚合了 {len(sorted_summaries)} 个源，共 {sum(s.article_count for s in sorted_summaries)} 篇文章。",
                "full_summary": "\n\n".join([f"## {s.source_name}\n{s.summary}" for s in sorted_summaries]),
                "cross_source_themes": [],
                "top_highlights": [],
                "sources_breakdown": [s.to_dict() for s in sorted_summaries],
                "generated_at": datetime.now().isoformat(),
                "error": str(e)
            }


def aggregate_group(
    group_name: str,
    source_summaries_data: List[Dict[str, Any]],
    llm_provider: str = "mock"
) -> Dict[str, Any]:
    """
    Convenience function to aggregate multiple source summaries
    
    Args:
        group_name: Name of the RSS group
        source_summaries_data: List of source summary dictionaries
        llm_provider: LLM provider to use
    
    Returns:
        Aggregated group summary dictionary
    """
    llm_client = create_llm_client(llm_provider)
    aggregator = GroupAggregator(llm_client, group_name)
    
    for summary_data in source_summaries_data:
        summary = SourceSummary.from_dict(summary_data)
        aggregator.add_source_summary(summary)
    
    return aggregator.aggregate()


if __name__ == "__main__":
    # Test the aggregator
    print("Testing Group Aggregator...")
    
    # Create test source summaries
    test_summaries = [
        SourceSummary(
            source_name="Tech News",
            summary="AI 技术取得重大突破，新模型架构提升推理效率。机器学习在医疗领域应用取得进展。",
            article_count=5,
            key_topics=["AI", "机器学习", "医疗科技"],
            highlights=["新 AI 模型发布", "医疗 AI 突破"],
            generated_at=datetime.now().isoformat()
        ),
        SourceSummary(
            source_name="Science Daily",
            summary="量子计算研究新进展，科学家实现新里程碑。太空探索任务更新。",
            article_count=3,
            key_topics=["量子计算", "太空探索"],
            highlights=["量子计算突破", "火星任务更新"],
            generated_at=datetime.now().isoformat()
        )
    ]
    
    aggregator = GroupAggregator(create_llm_client("mock"), "Tech & Science")
    aggregator.add_source_summaries(test_summaries)
    
    result = aggregator.aggregate()
    print(f"Group: {result['group_name']}")
    print(f"Sources: {result['source_count']}")
    print(f"Total Articles: {result['total_articles']}")
    print(f"Executive Summary: {result['executive_summary']}")
    print(f"Themes: {result['cross_source_themes']}")
    
    print("\nGroup Aggregator module loaded successfully!")
