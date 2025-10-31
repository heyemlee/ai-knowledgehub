"""
对话管理 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.schemas import ConversationResponse, MessageResponse
from app.utils.auth import get_current_user
from app.db.database import get_db
from app.db.models import Conversation, Message
from typing import List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户的所有对话列表
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="无法获取用户ID")
        
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        conversations = result.scalars().all()
        
        return [
            ConversationResponse(
                id=conv.id,
                conversation_id=conv.conversation_id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at
            )
            for conv in conversations
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取对话列表失败: {str(e)}")


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取对话的所有消息
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="无法获取用户ID")
        
        result = await db.execute(
            select(Conversation).where(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        messages_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
        )
        messages = messages_result.scalars().all()
        
        return [
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                sources=msg.sources,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取消息列表失败: {str(e)}")


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除对话（级联删除所有消息）
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="无法获取用户ID")
        
        result = await db.execute(
            select(Conversation).where(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        await db.delete(conversation)
        await db.commit()
        
        return {"message": "对话删除成功", "conversation_id": conversation_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除对话失败: {str(e)}")


