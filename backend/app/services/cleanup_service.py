"""
清理服务 - 自动删除过期的对话记录
只保留每个用户最近的 N 个对话
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.models import Conversation
import logging

logger = logging.getLogger(__name__)

# 每个用户最多保留的对话数量
MAX_CONVERSATIONS_PER_USER = 10


async def cleanup_old_conversations_for_user(db: AsyncSession, user_id: int):
    """
    删除用户超过最大数量的旧对话记录
    只保留最近的 MAX_CONVERSATIONS_PER_USER 个对话
    
    Args:
        db: 数据库会话
        user_id: 用户ID
    """
    try:
        # 获取该用户的所有对话，按更新时间倒序排列
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        conversations = result.scalars().all()
        
        # 如果对话数量不超过限制，直接返回
        if len(conversations) <= MAX_CONVERSATIONS_PER_USER:
            return 0
        
        # 获取需要删除的对话（保留最新的 MAX_CONVERSATIONS_PER_USER 个）
        conversations_to_keep = conversations[:MAX_CONVERSATIONS_PER_USER]
        conversations_to_delete = conversations[MAX_CONVERSATIONS_PER_USER:]
        
        if not conversations_to_delete:
            return 0
        
        # 获取要删除的对话ID列表
        conversation_ids_to_delete = [conv.id for conv in conversations_to_delete]
        conversation_uuid_list = [conv.conversation_id for conv in conversations_to_delete]
        
        # 删除旧对话（级联删除会自动删除相关消息）
        deleted_count = await db.execute(
            delete(Conversation).where(Conversation.id.in_(conversation_ids_to_delete))
        )
        
        await db.flush()  # 不立即提交，让调用者决定何时提交
        
        logger.info(
            f"用户 {user_id} 的对话清理完成：删除了 {deleted_count.rowcount} 个旧对话，"
            f"保留最新的 {MAX_CONVERSATIONS_PER_USER} 个对话"
        )
        
        return deleted_count.rowcount
    except Exception as e:
        logger.error(f"清理用户 {user_id} 的旧对话记录失败: {e}", exc_info=True)
        return 0

