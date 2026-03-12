"""
REST API 端点
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Any

router = APIRouter()


# ============== API 响应模型 ==============

class ApiResponse(BaseModel):
    """API 响应格式"""
    success: bool
    data: Any = None
    error_message: Optional[str] = None


# ============== API 端点 ==============

@router.get("/groups", response_model=ApiResponse)
async def get_groups():
    """
    获取 Group 列表
    
    Returns:
        所有 Group 的列表
    """
    try:
        from services.feed_service import FeedService
        
        service = FeedService()
        result = service.list_groups()
        service.close()
        
        if result.success:
            return ApiResponse(success=True, data=result.data)
        else:
            return ApiResponse(success=False, error_message=result.error_message)
    except Exception as e:
        return ApiResponse(success=False, error_message=str(e))


@router.get("/groups/{group_id}", response_model=ApiResponse)
async def get_group(group_id: str):
    """
    获取单个 Group 详情
    
    Args:
        group_id: Group ID
        
    Returns:
        Group 详情
    """
    try:
        from services.feed_service import FeedService
        
        service = FeedService()
        group = service.get_group(group_id)
        service.close()
        
        if not group:
            return ApiResponse(success=False, error_message=f"Group {group_id} 不存在")
        
        # 获取 Episode 数量
        episodes = service.get_group_episodes(group_id)
        
        data = {
            'id': group.id,
            'name': group.name,
            'description': group.description,
            'enabled': group.enabled,
            'podcast_structure': group.podcast_structure,
            'english_learning_mode': group.english_learning_mode,
            'audio_speed': group.audio_speed,
            'trigger_type': group.trigger_type,
            'trigger_config': group.trigger_config,
            'rss_sources': group.rss_sources,
            'episode_count': len(episodes)
        }
        
        return ApiResponse(success=True, data=data)
    except Exception as e:
        return ApiResponse(success=False, error_message=str(e))


@router.post("/groups/{group_id}/trigger", response_model=ApiResponse)
async def trigger_group(group_id: str):
    """
    触发生成指定 Group 的播客
    
   _id: Group ID Args:
        group
        
    Returns:
        触发结果
    """
    try:
        from services.feed_service import FeedService
        
        service = FeedService()
        
        # 检查 Group 是否存在
        group = service.get_group(group_id)
        if not group:
            service.close()
            return ApiResponse(success=False, error_message=f"Group {group_id} 不存在")
        
        # 触发生成
        result = service.trigger_group(group_id)
        service.close()
        
        if result.success:
            return ApiResponse(success=True, data=result.data)
        else:
            return ApiResponse(success=False, error_message=result.error_message)
    except Exception as e:
        return ApiResponse(success=False, error_message=str(e))


@router.get("/groups/{group_id}/episodes", response_model=ApiResponse)
async def get_group_episodes(group_id: str, limit: int = 50):
    """
    获取 Group 的 Episode 列表
    
    Args:
        group_id: Group ID
        limit: 返回数量限制
        
    Returns:
        Episode 列表
    """
    try:
        from services.feed_service import FeedService
        
        service = FeedService()
        
        # 检查 Group 是否存在
        group = service.get_group(group_id)
        if not group:
            service.close()
            return ApiResponse(success=False, error_message=f"Group {group_id} 不存在")
        
        episodes = service.get_group_episodes(group_id, limit)
        
        episode_list = []
        for ep in episodes:
            episode_list.append({
                'id': ep.id,
                'title': ep.title,
                'episode_number': ep.episode_number,
                'audio_path': ep.audio_path,
                'audio_duration': ep.audio_duration,
                'created_at': ep.created_at,
                'published_at': ep.published_at
            })
        
        service.close()
        
        return ApiResponse(success=True, data=episode_list)
    except Exception as e:
        return ApiResponse(success=False, error_message=str(e))


@router.get("/groups/{group_id}/feed-url", response_model=ApiResponse)
async def get_group_feed_url(group_id: str):
    """
    获取 Group 的 RSS Feed URL
    
    Args:
        group_id: Group ID
        
    Returns:
        RSS Feed URL
    """
    try:
        from services.feed_service import FeedService
        
        service = FeedService()
        
        # 检查 Group 是否存在
        group = service.get_group(group_id)
        if not group:
            service.close()
            return ApiResponse(success=False, error_message=f"Group {group_id} 不存在")
        
        result = service.get_feed_url(group_id)
        service.close()
        
        if result.success:
            return ApiResponse(success=True, data=result.data)
        else:
            return ApiResponse(success=False, error_message=result.error_message)
    except Exception as e:
        return ApiResponse(success=False, error_message=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}
