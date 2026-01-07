"""
智能文档检索服务
根据用户问题匹配最相关的完整文档（用于返回 PDF 预览）
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Document
from app.services.openai_service import openai_service
from typing import List, Dict, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)


class DocumentRetrievalService:
    """智能文档检索服务 - 根据问题匹配完整文档"""
    
    # 文档匹配阈值
    MATCH_THRESHOLD = 0.75
    
    async def search_documents(
        self,
        db: AsyncSession,
        question: str,
        limit: int = 3
    ) -> List[Dict]:
        """
        根据问题检索匹配的完整文档
        
        Args:
            db: 数据库会话
            question: 用户问题
            limit: 返回文档数量限制
            
        Returns:
            匹配的文档列表，每个包含 file_id, filename, title, preview_url, download_url
        """
        try:
            logger.info(f"开始智能文档检索，问题: {question[:50]}...")
            
            # 1. 获取所有有 metadata 的文档
            query = select(Document).where(Document.doc_metadata.isnot(None))
            result = await db.execute(query)
            documents = result.scalars().all()
            
            if not documents:
                # 如果没有带 metadata 的文档，尝试获取所有文档
                query = select(Document)
                result = await db.execute(query)
                documents = result.scalars().all()
                
            if not documents:
                logger.info("数据库中没有文档")
                return []
            
            logger.info(f"数据库中共有 {len(documents)} 个文档")
            
            # 2. 生成问题的 embedding
            try:
                question_embeddings, _ = openai_service.generate_embeddings([question])
                question_embedding = question_embeddings[0]
            except Exception as e:
                logger.error(f"生成问题 embedding 失败: {e}")
                # 降级到关键词匹配
                return await self._fallback_keyword_search(documents, question, limit)
            
            # 3. 为每个文档的标题+关键词生成 embedding 并计算相似度
            similarities = []
            for doc in documents:
                # 构建文档的搜索文本
                search_text = self._build_search_text(doc)
                
                try:
                    doc_embeddings, _ = openai_service.generate_embeddings([search_text])
                    doc_embedding = doc_embeddings[0]
                    
                    # 计算余弦相似度
                    similarity = self._cosine_similarity(question_embedding, doc_embedding)
                    similarities.append((doc, similarity))
                    
                    logger.debug(f"文档 {doc.filename}: 相似度 {similarity:.4f}")
                except Exception as e:
                    logger.warning(f"处理文档 {doc.filename} 失败: {e}")
                    continue
            
            if not similarities:
                return []
            
            # 4. 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # 5. 过滤低于阈值的结果
            matched_docs = [
                (doc, sim) for doc, sim in similarities 
                if sim >= self.MATCH_THRESHOLD
            ]
            
            if not matched_docs:
                logger.info(f"没有找到相似度 >= {self.MATCH_THRESHOLD} 的文档")
                # 如果没有超过阈值的，返回最相似的一个（如果相似度 > 0.6）
                if similarities and similarities[0][1] >= 0.6:
                    matched_docs = [similarities[0]]
                    logger.info(f"返回最相似的文档: {similarities[0][0].filename}, 相似度: {similarities[0][1]:.4f}")
                else:
                    return []
            
            # 6. 构建返回结果
            result_docs = []
            for doc, similarity in matched_docs[:limit]:
                metadata = doc.doc_metadata or {}
                result_docs.append({
                    'file_id': doc.file_id,
                    'filename': doc.filename,
                    'title': metadata.get('title', doc.filename),
                    'summary': metadata.get('summary', ''),
                    'preview_url': f'/api/v1/documents/{doc.file_id}/preview',
                    'download_url': f'/api/v1/documents/{doc.file_id}/download',
                    'relevance_score': round(similarity, 4)
                })
            
            logger.info(f"找到 {len(result_docs)} 个匹配文档")
            return result_docs
            
        except Exception as e:
            logger.error(f"智能文档检索失败: {e}", exc_info=True)
            return []
    
    def _build_search_text(self, doc: Document) -> str:
        """构建文档的搜索文本"""
        parts = [doc.filename]
        
        if doc.doc_metadata:
            if doc.doc_metadata.get('title'):
                parts.append(doc.doc_metadata['title'])
            if doc.doc_metadata.get('keywords'):
                parts.extend(doc.doc_metadata['keywords'])
            if doc.doc_metadata.get('summary'):
                parts.append(doc.doc_metadata['summary'])
        
        return ' '.join(parts)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
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
        documents: List[Document],
        question: str,
        limit: int
    ) -> List[Dict]:
        """降级方案：关键词匹配"""
        logger.info("使用降级方案：关键词匹配")
        
        question_lower = question.lower()
        matches = []
        
        for doc in documents:
            score = 0
            search_text = self._build_search_text(doc).lower()
            
            # 计算关键词匹配分数
            words = question_lower.split()
            for word in words:
                if len(word) >= 2 and word in search_text:
                    score += 1
            
            if score > 0:
                matches.append((doc, score / len(words) if words else 0))
        
        # 排序并返回
        matches.sort(key=lambda x: x[1], reverse=True)
        
        result_docs = []
        for doc, score in matches[:limit]:
            if score >= 0.3:  # 至少 30% 的词匹配
                metadata = doc.doc_metadata or {}
                result_docs.append({
                    'file_id': doc.file_id,
                    'filename': doc.filename,
                    'title': metadata.get('title', doc.filename),
                    'summary': metadata.get('summary', ''),
                    'preview_url': f'/api/v1/documents/{doc.file_id}/preview',
                    'download_url': f'/api/v1/documents/{doc.file_id}/download',
                    'relevance_score': round(score, 4)
                })
        
        return result_docs


# 全局实例
document_retrieval_service = DocumentRetrievalService()
