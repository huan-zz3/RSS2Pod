"""
RSS Feed 端点
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get("/{group_id}.xml", response_class=PlainTextResponse)
async def get_group_feed(group_id: str):
    """
    获取 Group 的 RSS Feed
    
    Args:
        group_id: Group ID
        
    Returns:
        RSS Feed XML
    """
    try:
        from services.feed_service import FeedService
        
        service = FeedService()
        result = service.generate_feed_xml(group_id)
        service.close()
        
        if result.success:
            return PlainTextResponse(
                content=result.data,
                media_type="application/rss+xml"
            )
        else:
            raise HTTPException(status_code=404, detail=result.error_message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
