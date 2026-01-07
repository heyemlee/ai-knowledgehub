"""
图片检索服务 - 智能语义匹配版本
使用 OpenAI Embeddings 进行语义相似度检索
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Image
from app.services.openai_service import openai_service
from typing import List, Dict
import logging
import numpy as np

logger = logging.getLogger(__name__)


class ImageRetrievalService:
    """图片检索服务 - 基于 Embedding 的语义检索"""
    
    async def search_images(
        self,
        db: AsyncSession,
        question: str,
        limit: int = 4
    ) -> List[Dict]:
        """
        根据问题检索相关图片（使用 Embedding 语义匹配）
        
        策略：
        1. 使用 OpenAI 生成问题的 embedding
        2. 使用 OpenAI 生成所有图片 description 的 embedding
        3. 计算余弦相似度
        4. 返回最相关的图片
        
        Args:
            db: 数据库会话
            question: 用户问题
            limit: 返回图片数量限制
            
        Returns:
            图片列表，每个图片包含 id, url, description 等信息
        """
        try:
            logger.info(f"开始智能图片检索，问题: {question}")
            
            # 查询所有有 description 的图片
            query = select(Image).where(Image.description.isnot(None))
            result = await db.execute(query)
            images = result.scalars().all()
            
            if not images:
                logger.info("数据库中没有图片")
                return []
            
            logger.info(f"数据库中共有 {len(images)} 张图片")
            
            # 生成问题的 embedding
            try:
                question_embeddings, _ = openai_service.generate_embeddings([question])
                question_embedding = question_embeddings[0]
                logger.info("问题 embedding 生成成功")
            except Exception as e:
                logger.error(f"生成问题 embedding 失败: {e}")
                # 降级到简单关键词匹配
                return await self._fallback_keyword_search(db, question, limit)
            
            # 生成所有图片 description 的 embeddings
            descriptions = [img.description for img in images]
            try:
                description_embeddings, _ = openai_service.generate_embeddings(descriptions)
                logger.info(f"生成了 {len(description_embeddings)} 个图片 description embeddings")
            except Exception as e:
                logger.error(f"生成图片 embeddings 失败: {e}")
                return await self._fallback_keyword_search(db, question, limit)
            
            # 计算相似度
            similarities = []
            for i, (image, desc_embedding) in enumerate(zip(images, description_embeddings)):
                similarity = self._cosine_similarity(question_embedding, desc_embedding)
                similarities.append((image, similarity))
                logger.debug(f"图片 {image.id} ({image.original_filename}): 相似度 {similarity:.4f}")
            
            # 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # 过滤低相似度的结果（精准匹配：阈值提高到 0.7）
            threshold = 0.7
            filtered_similarities = [(img, sim) for img, sim in similarities if sim >= threshold]
            
            if not filtered_similarities:
                logger.info(f"没有找到相似度 >= {threshold} 的图片，最高相似度: {similarities[0][1]:.4f}")
                # 精准匹配：不再降级到更低的阈值，没有就是没有
                return []
            
            # 构建返回结果
            result_images = []
            for image, similarity in filtered_similarities[:limit]:
                result_images.append({
                    'id': image.id,
                    'file_id': image.file_id,
                    'url': f'/api/v1/images/{image.id}/file',
                    'thumbnail_url': f'/api/v1/images/{image.id}/file?thumbnail=true',
                    'original_filename': image.original_filename,
                    'description': image.description,
                    'relevance_score': round(similarity, 4)
                })
            
            logger.info(f"找到 {len(result_images)} 张相关图片（相似度 >= {threshold}）")
            return result_images
            
        except Exception as e:
            logger.error(f"智能图片检索失败: {e}", exc_info=True)
            # 降级到简单关键词匹配
            return await self._fallback_keyword_search(db, question, limit)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            余弦相似度 (0-1)
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    async def _fallback_keyword_search(
        self,
        db: AsyncSession,
        question: str,
        limit: int
    ) -> List[Dict]:
        """
        降级方案：简单关键词匹配
        当 embedding 生成失败时使用
        """
        logger.info("使用降级方案：关键词匹配")
        
        try:
            from sqlalchemy import or_
            import re
            
            # 简单的关键词提取
            stop_words = {
                'the', 'a', 'an', 'is', 'are', 'of', 'for', 'with', 'on', 'at',
                'picture', 'image', 'photo', 'show', 'give', 'me', 'get', 'find'
            }
            
            words = re.findall(r'\w+', question.lower())
            keywords = [w for w in words if w not in stop_words and len(w) > 2]
            
            if not keywords:
                return []
            
            logger.info(f"关键词: {keywords}")
            
            # 构建查询
            conditions = []
            for keyword in keywords[:3]:
                conditions.append(Image.description.ilike(f'%{keyword}%'))
            
            query = (
                select(Image)
                .where(Image.description.isnot(None))
                .where(or_(*conditions))
                .limit(limit)
            )
            
            result = await db.execute(query)
            images = result.scalars().all()
            
            return [{
                'id': img.id,
                'file_id': img.file_id,
                'url': f'/api/v1/images/{img.id}/file',
                'thumbnail_url': f'/api/v1/images/{img.id}/file?thumbnail=true',
                'original_filename': img.original_filename,
                'description': img.description,
                'relevance_score': 0.5  # 降级方案给固定分数
            } for img in images]
            
        except Exception as e:
            logger.error(f"降级方案也失败: {e}", exc_info=True)
            return []


# 全局实例
image_retrieval_service = ImageRetrievalService()
