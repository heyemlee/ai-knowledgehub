"""
管理员 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.utils.auth import get_current_admin
from app.db.database import get_db
from app.db.models import Document, User
from app.models.schemas import DocumentMetadata, UserResponse
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

