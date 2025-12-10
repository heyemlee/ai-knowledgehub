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
from app.core.constants import ConversationConfig
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
    获取用户的所有对话列表（自动保留最新 10 个）
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="无法获取用户ID")
        
        # 获取所有对话，按更新时间降序
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        conversations = result.scalars().all()
        
        # 自动清理：只保留最新的对话
        if ConversationConfig.ENABLE_AUTO_CLEANUP and len(conversations) > ConversationConfig.MAX_CONVERSATIONS_PER_USER:
            # 获取需要删除的旧对话
            conversations_to_delete = conversations[ConversationConfig.MAX_CONVERSATIONS_PER_USER:]
            
            # 删除旧对话（会级联删除相关消息）
            for conv in conversations_to_delete:
                await db.delete(conv)
            
            await db.commit()
            logger.info(f"用户 {user_id} 自动清理了 {len(conversations_to_delete)} 个旧对话")
            
            # 只保留最新的对话
            conversations = conversations[:ConversationConfig.MAX_CONVERSATIONS_PER_USER]
        
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


