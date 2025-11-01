"""
Token 使用量查询 API
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.auth import get_current_user
from app.db.database import get_db
from app.services.token_usage_service import token_usage_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_token_usage_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的 token 使用统计
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="无法获取用户ID")
        
        stats = await token_usage_service.get_usage_stats(db, user_id)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 token 使用统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")









