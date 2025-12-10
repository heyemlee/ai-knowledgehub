"""
图片检索服务
基于图片描述、alt_text 和标签进行文本匹配检索
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from app.db.models import Image, ImageTag
from typing import List, Dict
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
        
        策略：
        1. 提取问题中的关键词
        2. 在图片的 description、alt_text 和 tags 中搜索匹配
        3. 返回最相关的图片
        
        Args:
            db: 数据库会话
            question: 用户问题
            limit: 返回图片数量限制
            
        Returns:
            图片列表，每个图片包含 id, url, description, alt_text, tags
        """
        try:
            # 简单的关键词提取（去除常见停用词）
            stop_words = {
                '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
                '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
                'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                'should', 'may', 'might', 'can', 'what', 'how', 'when', 'where', 'why'
            }
            
            # 分词（简单按空格和标点分割）
            import re
            words = re.findall(r'\w+', question.lower())
            keywords = [w for w in words if w not in stop_words and len(w) > 1]
            
            if not keywords:
                logger.info("未提取到有效关键词，跳过图片检索")
                return []
            
            logger.info(f"提取的关键词: {keywords}")
            
            # 构建查询条件
            # 在 description、alt_text 中搜索关键词
            conditions = []
            for keyword in keywords[:5]:  # 最多使用前5个关键词
                conditions.append(Image.description.ilike(f'%{keyword}%'))
                conditions.append(Image.alt_text.ilike(f'%{keyword}%'))
            
            # 查询图片
            query = select(Image).where(or_(*conditions)).limit(limit * 2)  # 多查询一些以便过滤
            result = await db.execute(query)
            images = result.scalars().all()
            
            # 如果没有找到，尝试通过标签搜索
            if not images:
                logger.info("通过描述未找到图片，尝试标签搜索")
                tag_conditions = []
                for keyword in keywords[:5]:
                    tag_conditions.append(ImageTag.name.ilike(f'%{keyword}%'))
                
                tag_query = select(Image).join(Image.tags).where(or_(*tag_conditions)).limit(limit * 2)
                tag_result = await db.execute(tag_query)
                images = tag_result.scalars().all()
            
            if not images:
                logger.info("未找到相关图片")
                return []
            
            # 计算相关性分数并排序
            scored_images = []
            for image in images:
                score = self._calculate_relevance_score(image, keywords)
                scored_images.append((image, score))
            
            # 按分数排序
            scored_images.sort(key=lambda x: x[1], reverse=True)
            
            # 构建返回结果
            result_images = []
            for image, score in scored_images[:limit]:
                # 加载标签
                tag_query = select(ImageTag).join(Image.tags).where(Image.id == image.id)
                tag_result = await db.execute(tag_query)
                tags = tag_result.scalars().all()
                
                result_images.append({
                    'id': image.id,
                    'file_id': image.file_id,
                    'url': f'/api/v1/images/{image.id}/file',
                    'thumbnail_url': f'/api/v1/images/{image.id}/file?thumbnail=true',
                    'original_filename': image.original_filename,
                    'description': image.description,
                    'alt_text': image.alt_text,
                    'tags': [tag.name for tag in tags],
                    'relevance_score': round(score, 2)
                })
            
            logger.info(f"找到 {len(result_images)} 张相关图片")
            return result_images
            
        except Exception as e:
            logger.error(f"图片检索失败: {e}", exc_info=True)
            return []
    
    def _calculate_relevance_score(self, image: Image, keywords: List[str]) -> float:
        """
        计算图片与关键词的相关性分数
        
        评分规则:
        - description 中每个关键词匹配: +2 分
        - alt_text 中每个关键词匹配: +1.5 分
        - 标签完全匹配: +3 分
        - 标签部分匹配: +1 分
        """
        score = 0.0
        
        # 检查 description
        if image.description:
            description_lower = image.description.lower()
            for keyword in keywords:
                if keyword in description_lower:
                    score += 2.0
        
        # 检查 alt_text
        if image.alt_text:
            alt_text_lower = image.alt_text.lower()
            for keyword in keywords:
                if keyword in alt_text_lower:
                    score += 1.5
        
        # 检查标签
        if image.tags:
            for tag in image.tags:
                tag_name_lower = tag.name.lower()
                for keyword in keywords:
                    if tag_name_lower == keyword:
                        score += 3.0  # 完全匹配
                    elif keyword in tag_name_lower or tag_name_lower in keyword:
                        score += 1.0  # 部分匹配
        
        return score


# 全局实例
image_retrieval_service = ImageRetrievalService()
