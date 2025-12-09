"""
图片检索服务
"""
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.db.models import Image, ImageTag
from app.services.openai_service import openai_service
import logging

logger = logging.getLogger(__name__)


class ImageRetrievalService:
    """图片检索服务"""
    
    async def search_images(
        self,
        db: AsyncSession,
        question: str,
        limit: int = 3
    ) -> List[Dict]:
        """
        根据问题检索相关图片
        
        Args:
            db: 数据库会话
            question: 用户问题
            limit: 返回图片数量限制
            
        Returns:
            相关图片列表
        """
        try:
            # 1. 提取关键词
            keywords, _ = openai_service.extract_keywords(question, max_keywords=5)
            
            if not keywords:
                logger.info("未提取到关键词，跳过图片检索")
                return []
            
            logger.info(f"图片检索关键词: {keywords}")
            
            # 2. 构建查询条件
            # 在描述、alt_text 或标签中匹配关键词
            conditions = []
            for keyword in keywords:
                keyword_pattern = f"%{keyword}%"
                conditions.append(
                    or_(
                        Image.description.ilike(keyword_pattern),
                        Image.alt_text.ilike(keyword_pattern)
                    )
                )
            
            # 3. 查询图片（包含标签）
            query = (
                select(Image)
                .where(or_(*conditions))
                .limit(limit)
            )
            
            result = await db.execute(query)
            images = result.scalars().all()
            
            # 4. 加载标签（手动加载关系）
            image_list = []
            for image in images:
                # 加载标签
                tag_query = (
                    select(ImageTag)
                    .join(Image.tags)
                    .where(Image.id == image.id)
                )
                tag_result = await db.execute(tag_query)
                tags = tag_result.scalars().all()
                
                image_dict = {
                    "id": image.id,
                    "file_id": image.file_id,
                    "filename": image.filename,
                    "original_filename": image.original_filename,
                    "file_size": image.file_size,
                    "mime_type": image.mime_type,
                    "storage_path": image.storage_path,
                    "thumbnail_path": image.thumbnail_path,
                    "description": image.description,
                    "alt_text": image.alt_text,
                    "user_id": image.user_id,
                    "tags": [{"id": tag.id, "name": tag.name, "created_at": tag.created_at} for tag in tags],
                    "created_at": image.created_at,
                    "updated_at": image.updated_at
                }
                image_list.append(image_dict)
            
            logger.info(f"找到 {len(image_list)} 张相关图片")
            return image_list
            
        except Exception as e:
            logger.error(f"图片检索失败: {e}", exc_info=True)
            return []
    
    async def search_images_by_tags(
        self,
        db: AsyncSession,
        tag_names: List[str],
        limit: int = 3
    ) -> List[Dict]:
        """
        根据标签检索图片
        
        Args:
            db: 数据库会话
            tag_names: 标签名称列表
            limit: 返回图片数量限制
            
        Returns:
            相关图片列表
        """
        try:
            if not tag_names:
                return []
            
            # 查询包含任一标签的图片
            query = (
                select(Image)
                .join(Image.tags)
                .where(ImageTag.name.in_(tag_names))
                .distinct()
                .limit(limit)
            )
            
            result = await db.execute(query)
            images = result.scalars().all()
            
            # 加载标签
            image_list = []
            for image in images:
                tag_query = (
                    select(ImageTag)
                    .join(Image.tags)
                    .where(Image.id == image.id)
                )
                tag_result = await db.execute(tag_query)
                tags = tag_result.scalars().all()
                
                image_dict = {
                    "id": image.id,
                    "file_id": image.file_id,
                    "filename": image.filename,
                    "original_filename": image.original_filename,
                    "file_size": image.file_size,
                    "mime_type": image.mime_type,
                    "storage_path": image.storage_path,
                    "thumbnail_path": image.thumbnail_path,
                    "description": image.description,
                    "alt_text": image.alt_text,
                    "user_id": image.user_id,
                    "tags": [{"id": tag.id, "name": tag.name, "created_at": tag.created_at} for tag in tags],
                    "created_at": image.created_at,
                    "updated_at": image.updated_at
                }
                image_list.append(image_dict)
            
            logger.info(f"通过标签找到 {len(image_list)} 张图片")
            return image_list
            
        except Exception as e:
            logger.error(f"标签图片检索失败: {e}", exc_info=True)
            return []


image_retrieval_service = ImageRetrievalService()
