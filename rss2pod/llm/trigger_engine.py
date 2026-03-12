#!/usr/bin/env python3
"""
Trigger Engine - Time-based (cron), count-based, and LLM-judgment triggers
"""

import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.llm_client import LLMClient, create_llm_client

# 导入 ProcessingState 用于状态检查
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database'))
    from models import ProcessingState
except ImportError:
    ProcessingState = None


class TriggerType(Enum):
    """Types of triggers"""
    CRON = "cron"  # Time-based trigger
    COUNT = "count"  # Article count trigger
    LLM_JUDGMENT = "llm_judgment"  # LLM-based importance judgment


@dataclass
class TriggerConfig:
    """Configuration for a trigger"""
    trigger_type: TriggerType
    enabled: bool = True
    
    # Cron settings
    cron_expression: Optional[str] = None  # e.g., "0 9 * * *" for 9 AM daily
    
    # Count settings
    article_threshold: int = 5  # Trigger when article count reaches this
    
    # LLM judgment settings
    llm_prompt: Optional[str] = None  # Custom prompt for LLM judgment
    importance_threshold: float = 0.7  # Threshold for LLM importance score (0-1)
    
    # Common settings
    cooldown_minutes: int = 30  # Minimum time between triggers
    name: str = "Unnamed Trigger"
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_triggered: Optional[str] = None
    trigger_count: int = 0


@dataclass
class TriggerResult:
    """Result of a trigger evaluation"""
    triggered: bool
    trigger_type: TriggerType
    reason: str
    confidence: float = 1.0  # For LLM triggers, confidence score
    metadata: Dict[str, Any] = field(default_factory=dict)


class TriggerEngine:
    """
    Engine for managing different types of triggers for RSS processing.
    Supports cron-based, count-based, and LLM-judgment triggers.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or create_llm_client("mock")
        self.triggers: List[TriggerConfig] = []
        self._last_evaluations: Dict[str, datetime] = {}
    
    def add_trigger(self, trigger: TriggerConfig) -> None:
        """Add a trigger configuration"""
        self.triggers.append(trigger)
    
    def remove_trigger(self, name: str) -> bool:
        """Remove a trigger by name"""
        for i, trigger in enumerate(self.triggers):
            if trigger.name == name:
                self.triggers.pop(i)
                return True
        return False
    
    def enable_trigger(self, name: str) -> bool:
        """Enable a trigger"""
        for trigger in self.triggers:
            if trigger.name == name:
                trigger.enabled = True
                return True
        return False
    
    def disable_trigger(self, name: str) -> bool:
        """Disable a trigger"""
        for trigger in self.triggers:
            if trigger.name == name:
                trigger.enabled = False
                return True
        return False
    
    def _check_cron_trigger(self, trigger: TriggerConfig) -> TriggerResult:
        """
        Check if cron trigger should fire
        
        Note: In production, integrate with actual cron scheduler.
        This is a simplified check.
        """
        if not trigger.cron_expression:
            return TriggerResult(
                triggered=False,
                trigger_type=TriggerType.CRON,
                reason="No cron expression configured"
            )
        
        # Simplified: Check if current time matches cron expression
        # In production, use a proper cron library like 'croniter'
        now = datetime.now()
        
        # For demo: trigger if minute matches (simplified)
        parts = trigger.cron_expression.split()
        if len(parts) >= 2:
            target_minute = parts[1] if parts[1] != "*" else str(now.minute)
            if str(now.minute) == target_minute:
                return TriggerResult(
                    triggered=True,
                    trigger_type=TriggerType.CRON,
                    reason=f"Cron schedule matched: {trigger.cron_expression}",
                    metadata={"cron": trigger.cron_expression, "current_time": now.isoformat()}
                )
        
        return TriggerResult(
            triggered=False,
            trigger_type=TriggerType.CRON,
            reason=f"Cron schedule not matched: {trigger.cron_expression}",
            metadata={"cron": trigger.cron_expression, "current_time": now.isoformat()}
        )
    
    def _check_count_trigger(self, trigger: TriggerConfig, article_count: int) -> TriggerResult:
        """Check if count trigger should fire"""
        if article_count >= trigger.article_threshold:
            return TriggerResult(
                triggered=True,
                trigger_type=TriggerType.COUNT,
                reason=f"Article count ({article_count}) reached threshold ({trigger.article_threshold})",
                metadata={"article_count": article_count, "threshold": trigger.article_threshold}
            )
        
        return TriggerResult(
            triggered=False,
            trigger_type=TriggerType.COUNT,
            reason=f"Article count ({article_count}) below threshold ({trigger.article_threshold})",
            metadata={"article_count": article_count, "threshold": trigger.article_threshold}
        )
    
    def _check_llm_judgment_trigger(
        self,
        trigger: TriggerConfig,
        articles: List[Dict[str, Any]]
    ) -> TriggerResult:
        """
        Use LLM to judge if content is important enough to trigger
        
        Args:
            trigger: Trigger configuration
            articles: List of article dictionaries
        
        Returns:
            TriggerResult with LLM judgment
        """
        if not articles:
            return TriggerResult(
                triggered=False,
                trigger_type=TriggerType.LLM_JUDGMENT,
                reason="No articles to evaluate",
                confidence=0.0
            )
        
        # Build prompt for LLM judgment
        articles_text = "\n\n".join([
            f"标题：{article.get('title', 'Untitled')}\n"
            f"摘要：{article.get('summary', article.get('content', ''))[:200]}"
            for article in articles[:10]  # Limit to 10 articles for context
        ])
        
        default_prompt = f"""请评估以下 RSS 文章集合是否足够重要，值得立即生成摘要和推送。

评估标准：
1. 是否有重大新闻或突破性进展
2. 是否有多个相关的重要主题
3. 内容时效性和紧迫性
4. 整体信息价值

文章列表（共 {len(articles)} 篇）：

{articles_text}

请按照以下 JSON 格式返回评估结果：
{{
    "should_trigger": true/false,
    "importance_score": 0.0-1.0,
    "reason": "评估理由",
    "key_topics": ["关键主题"],
    "urgency": "high/medium/low"
}}
"""
        
        prompt = trigger.llm_prompt or default_prompt
        
        try:
            result = self.llm_client.generate_json(prompt)
            
            should_trigger = result.get("should_trigger", False)
            importance_score = result.get("importance_score", 0.0)
            
            # Check if importance score meets threshold
            if should_trigger and importance_score >= trigger.importance_threshold:
                return TriggerResult(
                    triggered=True,
                    trigger_type=TriggerType.LLM_JUDGMENT,
                    reason=result.get("reason", "LLM determined content is important"),
                    confidence=importance_score,
                    metadata={
                        "importance_score": importance_score,
                        "urgency": result.get("urgency", "medium"),
                        "key_topics": result.get("key_topics", []),
                        "article_count": len(articles)
                    }
                )
            else:
                return TriggerResult(
                    triggered=False,
                    trigger_type=TriggerType.LLM_JUDGMENT,
                    reason=f"Importance score ({importance_score}) below threshold ({trigger.importance_threshold})",
                    confidence=importance_score,
                    metadata={
                        "importance_score": importance_score,
                        "urgency": result.get("urgency", "low"),
                        "article_count": len(articles)
                    }
                )
        
        except Exception as e:
            return TriggerResult(
                triggered=False,
                trigger_type=TriggerType.LLM_JUDGMENT,
                reason=f"LLM evaluation failed: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )
    
    def _check_cooldown(self, trigger: TriggerConfig) -> bool:
        """Check if trigger is in cooldown period"""
        if not trigger.last_triggered:
            return False  # Never triggered, no cooldown
        
        last_trigger = datetime.fromisoformat(trigger.last_triggered)
        cooldown_end = last_trigger + timedelta(minutes=trigger.cooldown_minutes)
        
        return datetime.now() < cooldown_end
    
    def evaluate(
        self,
        articles: List[Dict[str, Any]],
        trigger_name: Optional[str] = None
    ) -> List[TriggerResult]:
        """
        Evaluate all triggers (or specific trigger)
        
        Args:
            articles: List of article dictionaries
            trigger_name: Optional specific trigger to evaluate
        
        Returns:
            List of TriggerResults
        """
        results = []
        triggers_to_eval = self.triggers
        
        if trigger_name:
            triggers_to_eval = [t for t in self.triggers if t.name == trigger_name]
        
        for trigger in triggers_to_eval:
            if not trigger.enabled:
                results.append(TriggerResult(
                    triggered=False,
                    trigger_type=trigger.trigger_type,
                    reason="Trigger is disabled"
                ))
                continue
            
            # Check cooldown
            if self._check_cooldown(trigger):
                results.append(TriggerResult(
                    triggered=False,
                    trigger_type=trigger.trigger_type,
                    reason=f"Trigger is in cooldown period ({trigger.cooldown_minutes} minutes)"
                ))
                continue
            
            # Evaluate based on trigger type
            result = None
            if trigger.trigger_type == TriggerType.CRON:
                result = self._check_cron_trigger(trigger)
            elif trigger.trigger_type == TriggerType.COUNT:
                result = self._check_count_trigger(trigger, len(articles))
            elif trigger.trigger_type == TriggerType.LLM_JUDGMENT:
                result = self._check_llm_judgment_trigger(trigger, articles)
            
            if result:
                # Update trigger metadata if triggered
                if result.triggered:
                    trigger.last_triggered = datetime.now().isoformat()
                    trigger.trigger_count += 1
                
                results.append(result)
        
        return results
    
    def should_trigger(self, articles: List[Dict[str, Any]]) -> bool:
        """
        Quick check if any trigger should fire
        
        Args:
            articles: List of article dictionaries
        
        Returns:
            True if any enabled trigger should fire
        """
        results = self.evaluate(articles)
        return any(r.triggered for r in results)
    
    def get_trigger_stats(self) -> Dict[str, Any]:
        """Get statistics about all triggers"""
        return {
            "total_triggers": len(self.triggers),
            "enabled_triggers": sum(1 for t in self.triggers if t.enabled),
            "triggers": [
                {
                    "name": t.name,
                    "type": t.trigger_type.value,
                    "enabled": t.enabled,
                    "trigger_count": t.trigger_count,
                    "last_triggered": t.last_triggered
                }
                for t in self.triggers
            ]
        }

    def evaluate_with_state(
        self,
        group_id: str,
        state: Optional[Any],  # ProcessingState 类型
        articles: List[Dict[str, Any]],
        trigger_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        根据 Group 状态评估是否应该触发
        
        Args:
            group_id: Group ID
            state: ProcessingState 实例
            articles: 文章列表
            trigger_config: 触发器配置
            
        Returns:
            是否应该触发
        """
        if state is None:
            return False
        
        # 检查状态是否允许触发
        if state.status in ['running', 'disabled']:
            return False
        
        # 检查错误状态和重试次数
        if state.status == 'error':
            if state.retry_count >= 3:  # 最大重试次数
                return False
        
        # 如果提供了 trigger_config，使用配置进行评估
        if trigger_config:
            trigger_type = trigger_config.get('type', 'time')
            
            if trigger_type == 'time':
                # 时间触发：检查 cron 表达式
                cron_expr = trigger_config.get('cron', '')
                if cron_expr:
                    try:
                        from croniter import croniter
                        cron = croniter(cron_expr, datetime.now())
                        # 检查当前时间是否在触发窗口内（前后 1 分钟）
                        prev = cron.get_prev(datetime)
                        next_run = cron.get_next(datetime)
                        now = datetime.now()
                        if abs((now - prev).total_seconds()) < 60 or abs((next_run - now).total_seconds()) < 60:
                            return True
                    except ImportError:
                        # croniter 未安装，简化检查
                        pass
            
            elif trigger_type == 'count':
                # 数量触发：检查文章数量
                threshold = trigger_config.get('threshold', 10)
                if len(articles) >= threshold:
                    return True
            
            elif trigger_type == 'combined':
                # 组合触发：时间或数量
                cron_expr = trigger_config.get('cron', '')
                threshold = trigger_config.get('threshold', 10)
                
                # 检查数量
                if len(articles) >= threshold:
                    return True
                
                # 检查时间
                if cron_expr:
                    try:
                        from croniter import croniter
                        cron = croniter(cron_expr, datetime.now())
                        prev = cron.get_prev(datetime)
                        now = datetime.now()
                        if abs((now - prev).total_seconds()) < 60:
                            return True
                    except ImportError:
                        pass
        
        return False


# Convenience functions
def create_cron_trigger(
    name: str,
    cron_expression: str,
    cooldown_minutes: int = 30
) -> TriggerConfig:
    """Create a cron-based trigger"""
    return TriggerConfig(
        trigger_type=TriggerType.CRON,
        name=name,
        cron_expression=cron_expression,
        cooldown_minutes=cooldown_minutes
    )


def create_count_trigger(
    name: str,
    threshold: int,
    cooldown_minutes: int = 60
) -> TriggerConfig:
    """Create a count-based trigger"""
    return TriggerConfig(
        trigger_type=TriggerType.COUNT,
        name=name,
        article_threshold=threshold,
        cooldown_minutes=cooldown_minutes
    )


def create_llm_trigger(
    name: str,
    importance_threshold: float = 0.7,
    cooldown_minutes: int = 120,
    custom_prompt: Optional[str] = None
) -> TriggerConfig:
    """Create an LLM-judgment trigger"""
    return TriggerConfig(
        trigger_type=TriggerType.LLM_JUDGMENT,
        name=name,
        importance_threshold=importance_threshold,
        cooldown_minutes=cooldown_minutes,
        llm_prompt=custom_prompt
    )


if __name__ == "__main__":
    # Test the trigger engine
    print("Testing Trigger Engine...")
    
    engine = TriggerEngine(create_llm_client("mock"))
    
    # Add different types of triggers
    engine.add_trigger(create_cron_trigger("Daily Morning", "0 9 * * *"))
    engine.add_trigger(create_count_trigger("Article Batch", threshold=5))
    engine.add_trigger(create_llm_trigger("Important News", importance_threshold=0.6))
    
    # Test articles
    test_articles = [
        {"title": "AI Breakthrough", "summary": "Major AI advancement announced"},
        {"title": "Tech Update", "summary": "New technology released"},
        {"title": "Science News", "summary": "Scientific discovery made"},
        {"title": "Research Paper", "summary": "New research published"},
        {"title": "Innovation", "summary": "Innovative product launched"}
    ]
    
    # Evaluate triggers
    results = engine.evaluate(test_articles)
    
    print(f"\nEvaluated {len(results)} triggers:")
    for result in results:
        status = "✓ TRIGGERED" if result.triggered else "✗ Not triggered"
        print(f"  {status} - {result.trigger_type.value}: {result.reason}")
        if result.metadata:
            print(f"      Metadata: {result.metadata}")
    
    # Get stats
    stats = engine.get_trigger_stats()
    print("\nTrigger Stats:")
    print(f"  Total: {stats['total_triggers']}")
    print(f"  Enabled: {stats['enabled_triggers']}")
    
    print("\nTrigger Engine module loaded successfully!")
