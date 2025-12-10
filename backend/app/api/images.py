"""
图片管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List, Optional
from app.db.database import get_db
from app.db.models import User, Image, ImageTag, image_tag_association
from app.models.schemas import (
    ImageUploadResponse, ImageResponse, ImageUpdate, 
    ImageTagCreate, ImageTagResponse, ImageListResponse
)
from app.api.auth import get_current_user, get_current_admin_user
from app.services.image_storage_service import storage_service

from app.middleware.rate_limit import limiter
from fastapi import Request
from app.core.constants import ImageConfig
import uuid
import logging
from datetime import datetime
import os
from PIL import Image as PILImage
import io

logger = logging.getLogger(__name__)

router = APIRouter()

# 支持的图片格式
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"],
    "image/webp": [".webp"]
}

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_image_file(file: UploadFile) -> None:
    """验证图片文件"""
    # 检查 MIME 类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的图片格式。支持的格式: {', '.join(ALLOWED_IMAGE_TYPES.keys())}"
        )
    
    # 检查文件扩展名
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = ALLOWED_IMAGE_TYPES[file.content_type]
    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件扩展名与 MIME 类型不匹配"
        )



def create_thumbnail(image_data: bytes, max_size: tuple = None) -> tuple[bytes, dict]:
    """
    创建缩略图（智能优化）
    
    返回: (thumbnail_data, info_dict)
        - thumbnail_data: 缩略图字节数据，如果不需要生成则返回 None
        - info_dict: 包含原图信息 {'width': int, 'height': int, 'needs_thumbnail': bool}
    """
    if max_size is None:
        max_size = ImageConfig.THUMBNAIL_MAX_SIZE
    
    try:
        img = PILImage.open(io.BytesIO(image_data))
        original_width, original_height = img.size
        
        # 智能判断是否需要生成缩略图
        file_size_kb = len(image_data) / 1024
        
        # 根据配置决定是否启用智能缩略图
        if ImageConfig.ENABLE_SMART_THUMBNAIL:
            # 智能模式：只为大图生成缩略图
            # 1. 如果原图尺寸小于等于缩略图尺寸，不生成
            # 2. 如果原图文件大小小于阈值，不生成
            needs_thumbnail = (
                original_width > max_size[0] or 
                original_height > max_size[1]
            ) and file_size_kb > ImageConfig.THUMBNAIL_SIZE_THRESHOLD_KB
        else:
            # 总是生成缩略图模式
            needs_thumbnail = True
        
        info = {
            'width': original_width,
            'height': original_height,
            'needs_thumbnail': needs_thumbnail,
            'original_size_kb': round(file_size_kb, 2)
        }
        
        if not needs_thumbnail:
            logger.info(f"原图尺寸 {original_width}x{original_height}, 大小 {file_size_kb:.2f}KB, 无需生成缩略图")
            return None, info
        
        # 生成缩略图
        img.thumbnail(max_size, PILImage.Resampling.LANCZOS)
        
        # 保存为 JPEG 格式
        output = io.BytesIO()
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(output, format='JPEG', quality=ImageConfig.THUMBNAIL_JPEG_QUALITY)
        
        thumbnail_size_kb = len(output.getvalue()) / 1024
        logger.info(f"缩略图生成成功: {img.size[0]}x{img.size[1]}, 大小 {thumbnail_size_kb:.2f}KB (节省 {file_size_kb - thumbnail_size_kb:.2f}KB)")
        
        return output.getvalue(), info
    except Exception as e:
        logger.warning(f"创建缩略图失败: {e}")
        return None, {'width': 0, 'height': 0, 'needs_thumbnail': False, 'original_size_kb': 0}



# ==============================
# 图片标签管理
# ==============================

@router.post("/tags", response_model=ImageTagResponse)
@limiter.limit("30/minute")
async def create_tag(
    request: Request,
    tag: ImageTagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """创建图片标签（仅管理员）"""
    try:
        # 检查标签是否已存在
        query = select(ImageTag).where(ImageTag.name == tag.name)
        result = await db.execute(query)
        existing_tag = result.scalar_one_or_none()
        
        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="标签已存在"
            )
        
        # 创建新标签
        new_tag = ImageTag(name=tag.name)
        db.add(new_tag)
        await db.commit()
        await db.refresh(new_tag)
        
        return new_tag
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"创建标签失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建标签失败"
        )


@router.get("/tags", response_model=List[ImageTagResponse])
@limiter.limit("60/minute")
async def list_tags(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有标签"""
    try:
        query = select(ImageTag).order_by(ImageTag.name)
        result = await db.execute(query)
        tags = result.scalars().all()
        return tags
    except Exception as e:
        logger.error(f"获取标签列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取标签列表失败"
        )


@router.delete("/tags/{tag_id}")
@limiter.limit("30/minute")
async def delete_tag(
    request: Request,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除标签（仅管理员）"""
    try:
        query = select(ImageTag).where(ImageTag.id == tag_id)
        result = await db.execute(query)
        tag = result.scalar_one_or_none()
        
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="标签不存在"
            )
        
        await db.delete(tag)
        await db.commit()
        
        return {"message": "标签删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除标签失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除标签失败"
        )


# ==============================
# 图片管理
# ==============================

@router.post("/upload", response_model=ImageUploadResponse)
@limiter.limit("20/minute")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    alt_text: Optional[str] = Form(None),
    tag_ids: Optional[str] = Form(None),  # 逗号分隔的标签 ID
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """上传图片（仅管理员）"""
    try:
        logger.info(f"开始上传图片: {file.filename}, content_type: {file.content_type}")
        logger.info(f"用户信息: {current_user}")
        
        # 验证文件
        validate_image_file(file)
        logger.info("文件验证通过")
        
        # 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        logger.info(f"文件大小: {file_size} bytes")
        
        # 检查文件大小
        if file_size > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"图片大小不能超过 {MAX_IMAGE_SIZE // 1024 // 1024}MB"
            )
        
        # 生成唯一文件 ID
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1].lower()
        stored_filename = f"{file_id}{file_ext}"
        logger.info(f"生成文件ID: {file_id}, 存储文件名: {stored_filename}")
        
        # 保存原图
        storage_path = await storage_service.save_file(
            file_content,
            stored_filename,
            file.content_type
        )
        logger.info(f"原图保存成功: {storage_path}")
        
        # 创建缩略图（智能优化：只为大图生成）
        thumbnail_path = None
        thumbnail_data, image_info = create_thumbnail(file_content)
        
        if thumbnail_data:
            thumbnail_filename = f"{file_id}_thumb.jpg"
            thumbnail_path = await storage_service.save_file(
                thumbnail_data,
                thumbnail_filename,
                "image/jpeg"
            )
            logger.info(f"缩略图保存成功: {thumbnail_path}")
        else:
            logger.info(f"使用原图作为缩略图（原图: {image_info['width']}x{image_info['height']}, {image_info['original_size_kb']}KB）")
        
        # 解析标签 ID
        tag_id_list = []
        if tag_ids:
            try:
                tag_id_list = [int(tid.strip()) for tid in tag_ids.split(",") if tid.strip()]
                logger.info(f"解析标签ID: {tag_id_list}")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="标签 ID 格式错误"
                )
        
        # 创建数据库记录
        user_id = current_user.get("user_id")
        logger.info(f"创建数据库记录, user_id: {user_id}")
        
        new_image = Image(
            file_id=file_id,
            filename=stored_filename,
            original_filename=file.filename,
            file_size=file_size,
            mime_type=file.content_type,
            storage_path=storage_path,
            thumbnail_path=thumbnail_path,
            description=description,
            alt_text=alt_text,
            user_id=user_id
        )
        
        db.add(new_image)
        await db.flush()  # 获取 ID
        logger.info(f"数据库记录创建成功, image_id: {new_image.id}")
        
        # 关联标签
        if tag_id_list:
            # 验证标签存在
            tag_query = select(ImageTag).where(ImageTag.id.in_(tag_id_list))
            tag_result = await db.execute(tag_query)
            tags = tag_result.scalars().all()
            
            if len(tags) != len(tag_id_list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="部分标签不存在"
                )
            
            # 添加关联
            new_image.tags = tags
            logger.info(f"标签关联成功: {len(tags)} 个标签")
        
        await db.commit()
        await db.refresh(new_image)
        logger.info("数据库提交成功")
        
        response_data = ImageUploadResponse(
            file_id=new_image.file_id,
            filename=new_image.filename,
            original_filename=new_image.original_filename,
            file_size=new_image.file_size,
            mime_type=new_image.mime_type,
            storage_path=new_image.storage_path,
            thumbnail_path=new_image.thumbnail_path,
            upload_time=new_image.created_at
        )
        logger.info(f"响应数据构建成功: {response_data.dict()}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"上传图片失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传图片失败: {str(e)}"
        )


@router.get("", response_model=ImageListResponse)
@limiter.limit("60/minute")
async def list_images(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tag_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取图片列表"""
    try:
        # 构建查询
        query = select(Image)
        
        # 按标签筛选
        if tag_id:
            query = query.join(Image.tags).where(ImageTag.id == tag_id)
        
        # 计算总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        offset = (page - 1) * page_size
        query = query.order_by(Image.created_at.desc()).offset(offset).limit(page_size)
        
        result = await db.execute(query)
        images = result.scalars().all()
        
        # 加载标签
        image_list = []
        for image in images:
            tag_query = select(ImageTag).join(Image.tags).where(Image.id == image.id)
            tag_result = await db.execute(tag_query)
            tags = tag_result.scalars().all()
            
            image_response = ImageResponse(
                id=image.id,
                file_id=image.file_id,
                filename=image.filename,
                original_filename=image.original_filename,
                file_size=image.file_size,
                mime_type=image.mime_type,
                storage_path=image.storage_path,
                thumbnail_path=image.thumbnail_path,
                description=image.description,
                alt_text=image.alt_text,
                user_id=image.user_id,
                tags=[ImageTagResponse(id=tag.id, name=tag.name, created_at=tag.created_at) for tag in tags],
                created_at=image.created_at,
                updated_at=image.updated_at
            )
            image_list.append(image_response)
        
        return ImageListResponse(
            images=image_list,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"获取图片列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取图片列表失败"
        )


@router.get("/{image_id}", response_model=ImageResponse)
@limiter.limit("60/minute")
async def get_image(
    request: Request,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取图片详情"""
    try:
        query = select(Image).where(Image.id == image_id)
        result = await db.execute(query)
        image = result.scalar_one_or_none()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="图片不存在"
            )
        
        # 加载标签
        tag_query = select(ImageTag).join(Image.tags).where(Image.id == image.id)
        tag_result = await db.execute(tag_query)
        tags = tag_result.scalars().all()
        
        return ImageResponse(
            id=image.id,
            file_id=image.file_id,
            filename=image.filename,
            original_filename=image.original_filename,
            file_size=image.file_size,
            mime_type=image.mime_type,
            storage_path=image.storage_path,
            thumbnail_path=image.thumbnail_path,
            description=image.description,
            alt_text=image.alt_text,
            user_id=image.user_id,
            tags=[ImageTagResponse(id=tag.id, name=tag.name, created_at=tag.created_at) for tag in tags],
            created_at=image.created_at,
            updated_at=image.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图片详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取图片详情失败"
        )


@router.put("/{image_id}", response_model=ImageResponse)
@limiter.limit("30/minute")
async def update_image(
    request: Request,
    image_id: int,
    update_data: ImageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新图片信息（仅管理员）"""
    try:
        query = select(Image).where(Image.id == image_id)
        result = await db.execute(query)
        image = result.scalar_one_or_none()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="图片不存在"
            )
        
        # 更新字段
        if update_data.description is not None:
            image.description = update_data.description
        if update_data.alt_text is not None:
            image.alt_text = update_data.alt_text
        
        # 更新标签
        if update_data.tag_ids is not None:
            if update_data.tag_ids:
                # 验证标签存在
                tag_query = select(ImageTag).where(ImageTag.id.in_(update_data.tag_ids))
                tag_result = await db.execute(tag_query)
                tags = tag_result.scalars().all()
                
                if len(tags) != len(update_data.tag_ids):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="部分标签不存在"
                    )
                
                image.tags = tags
            else:
                # 清空标签
                image.tags = []
        
        await db.commit()
        await db.refresh(image)
        
        # 加载标签
        tag_query = select(ImageTag).join(Image.tags).where(Image.id == image.id)
        tag_result = await db.execute(tag_query)
        tags = tag_result.scalars().all()
        
        return ImageResponse(
            id=image.id,
            file_id=image.file_id,
            filename=image.filename,
            original_filename=image.original_filename,
            file_size=image.file_size,
            mime_type=image.mime_type,
            storage_path=image.storage_path,
            thumbnail_path=image.thumbnail_path,
            description=image.description,
            alt_text=image.alt_text,
            user_id=image.user_id,
            tags=[ImageTagResponse(id=tag.id, name=tag.name, created_at=tag.created_at) for tag in tags],
            created_at=image.created_at,
            updated_at=image.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新图片失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新图片失败"
        )


@router.delete("/{image_id}")
@limiter.limit("30/minute")
async def delete_image(
    request: Request,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除图片（仅管理员）"""
    try:
        query = select(Image).where(Image.id == image_id)
        result = await db.execute(query)
        image = result.scalar_one_or_none()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="图片不存在"
            )
        
        # 删除文件
        try:
            await storage_service.delete_file(image.storage_path)
            if image.thumbnail_path:
                await storage_service.delete_file(image.thumbnail_path)
        except Exception as e:
            logger.warning(f"删除文件失败: {e}")
        
        # 删除数据库记录
        await db.delete(image)
        await db.commit()
        
        return {"message": "图片删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除图片失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除图片失败"
        )


@router.get("/{image_id}/file")
@limiter.limit("100/minute")
async def get_image_file(
    request: Request,
    image_id: int,
    thumbnail: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    """获取图片文件"""
    try:
        query = select(Image).where(Image.id == image_id)
        result = await db.execute(query)
        image = result.scalar_one_or_none()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="图片不存在"
            )
        
        # 选择原图或缩略图
        file_path = image.thumbnail_path if thumbnail and image.thumbnail_path else image.storage_path
        
        # 获取文件内容
        file_content = await storage_service.get_file(file_path)
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="图片文件不存在"
            )
        
        # 返回文件
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=image.mime_type,
            headers={
                "Content-Disposition": f'inline; filename="{image.original_filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图片文件失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取图片文件失败"
        )
