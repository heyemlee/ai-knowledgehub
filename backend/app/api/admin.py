"""
管理员 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.utils.auth import get_current_admin
from app.db.database import get_db
from app.db.models import Document, User
from app.models.schemas import DocumentMetadata, UserResponse, UserQuotaUpdate
from app.middleware.rate_limit import limiter
from app.core.constants import RateLimitConfig
from typing import List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/documents", response_model=List[DocumentMetadata])
@limiter.limit(RateLimitConfig.DOCUMENT_RATE_LIMIT)
async def list_all_documents(
    request: Request,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    管理员查看所有文档
    
    返回系统中所有用户上传的文档列表
    """
    try:
        result = await db.execute(
            select(Document)
            .order_by(Document.created_at.desc())
        )
        documents = result.scalars().all()
        
        result_list = [
            DocumentMetadata(
                file_id=doc.file_id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                upload_time=doc.created_at,
                chunks_count=doc.chunks_count,
                status=doc.status,
                user_id=doc.user_id  # 管理员可以看到是哪个用户上传的
            )
            for doc in documents
        ]
        
        logger.info(f"管理员 {current_admin.get('user_id')} 查看了所有文档，共 {len(result_list)} 个")
        return result_list
        
    except Exception as e:
        logger.error(f"获取所有文档列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.get("/documents/stats")
@limiter.limit(RateLimitConfig.DOCUMENT_RATE_LIMIT)
async def get_documents_stats(
    request: Request,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    获取文档统计信息
    
    Returns:
        文档总数、总大小、按用户统计等
    """
    try:
        total_docs_result = await db.execute(select(func.count(Document.id)))
        total_docs = total_docs_result.scalar()
        
        total_size_result = await db.execute(select(func.sum(Document.file_size)))
        total_size = total_size_result.scalar() or 0
        
        user_stats_result = await db.execute(
            select(
                Document.user_id,
                func.count(Document.id).label('doc_count'),
                func.sum(Document.file_size).label('total_size')
            )
            .group_by(Document.user_id)
            .order_by(desc('doc_count'))
        )
        user_stats = [
            {
                "user_id": row.user_id,
                "document_count": row.doc_count,
                "total_size": row.total_size
            }
            for row in user_stats_result
        ]
        
        return {
            "total_documents": total_docs,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "users_stats": user_stats
        }
        
    except Exception as e:
        logger.error(f"获取文档统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/users", response_model=List[UserResponse])
@limiter.limit(RateLimitConfig.DOCUMENT_RATE_LIMIT)
async def list_all_users(
    request: Request,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    管理员查看所有用户
    
    返回系统中所有用户列表
    """
    try:
        result = await db.execute(
            select(User).order_by(User.created_at.desc())
        )
        users = result.scalars().all()
        
        user_list = [
            UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                role=user.role,
                token_quota=user.token_quota,
                created_at=user.created_at
            )
            for user in users
        ]
        
        logger.info(f"管理员 {current_admin.get('user_id')} 查看了所有用户，共 {len(user_list)} 个")
        return user_list
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


@router.get("/users/stats")
@limiter.limit(RateLimitConfig.DOCUMENT_RATE_LIMIT)
async def get_users_stats(
    request: Request,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户统计信息
    """
    try:
        total_users_result = await db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar()
        
        active_users_result = await db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active_users = active_users_result.scalar()
        
        admin_users_result = await db.execute(
            select(func.count(User.id)).where(User.role == "admin")
        )
        admin_users = admin_users_result.scalar()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "admin_users": admin_users,
            "regular_users": total_users - admin_users
        }
        
    except Exception as e:
        logger.error(f"获取用户统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.delete("/documents/{file_id}")
@limiter.limit(RateLimitConfig.DOCUMENT_RATE_LIMIT)
async def admin_delete_document(
    request: Request,
    file_id: str,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    管理员删除任意文档
    """
    try:
        from app.services.local_storage_service import storage_service
        from app.services.qdrant_service import qdrant_service
        
        # 1. 查询文档是否存在
        result = await db.execute(
            select(Document).where(Document.file_id == file_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 2. 删除物理文件
        try:
            storage_service.delete_file(file_id, document.filename)
            logger.info(f"物理文件删除成功: {file_id}")
        except Exception as e:
            logger.error(f"物理文件删除失败: {e}")
            # 继续执行，不阻断流程
        
        # 3. 删除向量数据
        try:
            qdrant_service.delete_documents(file_id)
            logger.info(f"向量数据删除成功: {file_id}")
        except Exception as e:
            logger.error(f"向量数据删除失败: {e}")
            # 继续执行，不阻断流程
        
        # 4. 删除数据库记录
        await db.delete(document)
        await db.commit()
        
        logger.info(f"管理员 {current_admin.get('user_id')} 成功删除文档 {file_id}")
        return {"message": "文档删除成功", "file_id": file_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"管理员删除文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/users/{user_id}/detail")
@limiter.limit(RateLimitConfig.DOCUMENT_RATE_LIMIT)
async def get_user_detail(
    request: Request,
    user_id: int,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    管理员查看用户详情（包含 Token 使用情况）
    """
    try:
        from app.db.models import TokenUsage
        from app.models.schemas import AdminUserDetailResponse
        
        # 查询用户
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 计算用户已使用的 tokens
        tokens_used_result = await db.execute(
            select(func.sum(TokenUsage.total_tokens))
            .where(TokenUsage.user_id == user_id)
        )
        tokens_used = tokens_used_result.scalar() or 0
        
        # 计算剩余 tokens
        tokens_remaining = max(0, user.token_quota - tokens_used)
        
        return AdminUserDetailResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            role=user.role,
            token_quota=user.token_quota,
            tokens_used=tokens_used,
            tokens_remaining=tokens_remaining,
            created_at=user.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取用户详情失败: {str(e)}")


@router.delete("/users/{user_id}")
@limiter.limit(RateLimitConfig.DOCUMENT_RATE_LIMIT)
async def delete_user(
    request: Request,
    user_id: int,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    管理员删除用户账号
    
    注意：会级联删除用户的所有文档、对话、Token 使用记录等
    """
    try:
        # 查询用户
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 不允许删除管理员自己
        if user_id == current_admin.get('user_id'):
            raise HTTPException(status_code=400, detail="不能删除自己的账号")
        
        # 删除用户（会级联删除关联数据）
        await db.delete(user)
        await db.commit()
        
        logger.info(f"管理员 {current_admin.get('user_id')} 成功删除用户 {user_id} ({user.email})")
        return {"message": "用户删除成功", "user_id": user_id, "email": user.email}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除用户失败: {str(e)}")


@router.patch("/users/{user_id}/quota")
@limiter.limit(RateLimitConfig.DOCUMENT_RATE_LIMIT)
async def update_user_quota(
    request: Request,
    user_id: int,
    quota_update: UserQuotaUpdate,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    管理员更新用户的 Token 配额
    """
    try:
        # 查询用户
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 更新配额
        old_quota = user.token_quota
        user.token_quota = quota_update.token_quota
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"管理员 {current_admin.get('user_id')} 更新用户 {user_id} 的 Token 配额: {old_quota} -> {quota_update.token_quota}")
        
        return {
            "message": "Token 配额更新成功",
            "user_id": user_id,
            "email": user.email,
            "old_quota": old_quota,
            "new_quota": user.token_quota
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户配额失败: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新配额失败: {str(e)}")


@router.get("/users/tokens/summary")
@limiter.limit(RateLimitConfig.DOCUMENT_RATE_LIMIT)
async def get_users_token_summary(
    request: Request,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有用户的 Token 使用汇总
    """
    try:
        from app.db.models import TokenUsage
        
        # 获取所有用户
        users_result = await db.execute(select(User))
        users = users_result.scalars().all()
        
        summary = []
        for user in users:
            # 计算用户已使用的 tokens
            tokens_used_result = await db.execute(
                select(func.sum(TokenUsage.total_tokens))
                .where(TokenUsage.user_id == user.id)
            )
            tokens_used = tokens_used_result.scalar() or 0
            tokens_remaining = max(0, user.token_quota - tokens_used)
            
            summary.append({
                "user_id": user.id,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "token_quota": user.token_quota,
                "tokens_used": tokens_used,
                "tokens_remaining": tokens_remaining,
                "usage_percentage": round((tokens_used / user.token_quota * 100) if user.token_quota > 0 else 0, 2)
            })
        
        return {
            "total_users": len(summary),
            "users": summary
        }
        
    except Exception as e:
        logger.error(f"获取 Token 使用汇总失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取汇总失败: {str(e)}")
