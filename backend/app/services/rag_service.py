"""
RAG（检索增强生成）服务
整合 embedding、检索、生成的完整流程，提供统一接口和性能监控
"""
from typing import List, Dict, Optional, AsyncGenerator, Tuple
from app.services.openai_service import openai_service
from app.services.qdrant_service import qdrant_service
from app.core.constants import SearchConfig, ProcessingConfig
import logging
import time

logger = logging.getLogger(__name__)


class RAGService:
    """RAG服务：完整的检索增强生成流程"""
    
    def __init__(self):
        self.openai_service = openai_service
        self.qdrant_service = qdrant_service
    
    def process_query(
        self,
        question: str,
        limit: int = None,
        score_threshold: float = None
    ) -> Tuple[str, List[Dict], Dict]:
        """
        处理用户查询（非流式版本）
        
        Args:
            question: 用户问题
            limit: 返回结果数量
            score_threshold: 相似度阈值
            
        Returns:
            (answer, sources, metrics) 元组
        """
        start_time = time.time()
        metrics = {
            'question_length': len(question),
            'embedding_time': 0,
            'retrieval_time': 0,
            'generation_time': 0,
            'total_time': 0,
            'documents_retrieved': 0,
            'documents_used': 0,
            'token_usage': {}
        }
        
        try:
            # 1. 生成问题向量嵌入
            logger.info(f"[RAG] 开始处理问题: {question[:50]}...")
            embed_start = time.time()
            
            embeddings, embedding_token_usage = self.openai_service.generate_embeddings([question])
            question_embedding = embeddings[0] if embeddings else None
            
            if not question_embedding:
                raise ValueError("生成问题向量失败")
            
            metrics['embedding_time'] = time.time() - embed_start
            if embedding_token_usage:
                metrics['token_usage']['embedding'] = embedding_token_usage
            
            # 2. 智能确定检索参数
            retrieval_params = self._determine_retrieval_params(
                question, limit, score_threshold
            )
            
            # 3. 在 Qdrant 中检索相似文档
            retrieval_start = time.time()
            
            relevant_docs = self.qdrant_service.search(
                query_embedding=question_embedding,
                limit=retrieval_params['limit'],
                score_threshold=retrieval_params['score_threshold'],
                query_text=question
            )
            
            metrics['retrieval_time'] = time.time() - retrieval_start
            metrics['documents_retrieved'] = len(relevant_docs)
            
            # 4. 如果没有找到足够的文档，降级检索
            if len(relevant_docs) < retrieval_params.get('min_docs', 1):
                logger.warning(f"检索到的文档数量不足 ({len(relevant_docs)})，尝试降级检索")
                relevant_docs = self._fallback_retrieval(question_embedding, question)
                metrics['used_fallback'] = True
            
            # 5. 构建上下文并生成回答
            generation_start = time.time()
            
            answer, generation_token_usage = self.openai_service.generate_answer(
                question=question,
                context=relevant_docs
            )
            
            metrics['generation_time'] = time.time() - generation_start
            if generation_token_usage:
                metrics['token_usage']['generation'] = generation_token_usage
            
            # 6. 提取文档来源
            sources = self._extract_sources(relevant_docs)
            metrics['documents_used'] = len(sources)
            
            # 7. 计算总耗时
            metrics['total_time'] = time.time() - start_time
            
            # 8. 计算总token使用量
            total_tokens = 0
            if embedding_token_usage:
                total_tokens += embedding_token_usage.get('total_tokens', 0)
            if generation_token_usage:
                total_tokens += generation_token_usage.get('total_tokens', 0)
            metrics['token_usage']['total'] = total_tokens
            
            logger.info(
                f"[RAG] 完成查询处理: "
                f"检索={metrics['documents_retrieved']}文档, "
                f"使用={metrics['documents_used']}文档, "
                f"tokens={total_tokens}, "
                f"耗时={metrics['total_time']:.2f}s"
            )
            
            return answer, sources, metrics
            
        except Exception as e:
            logger.error(f"[RAG] 查询处理失败: {e}", exc_info=True)
            metrics['error'] = str(e)
            raise
    
    async def stream_query(
        self,
        question: str,
        limit: int = None,
        score_threshold: float = None
    ) -> AsyncGenerator[Tuple[Optional[str], Optional[List[Dict]], Optional[Dict]], None]:
        """
        流式处理用户查询
        
        Args:
            question: 用户问题
            limit: 返回结果数量
            score_threshold: 相似度阈值
            
        Yields:
            (content, sources, metrics) 元组
            - content: 文本片段（生成过程中）或 None（完成时）
            - sources: 文档来源（完成时）或 None
            - metrics: 性能指标（完成时）或 None
        """
        start_time = time.time()
        metrics = {
            'question_length': len(question),
            'embedding_time': 0,
            'retrieval_time': 0,
            'generation_time': 0,
            'total_time': 0,
            'documents_retrieved': 0,
            'documents_used': 0,
            'token_usage': {}
        }
        
        try:
            # 1. 生成问题向量嵌入
            logger.info(f"[RAG Stream] 开始处理问题: {question[:50]}...")
            embed_start = time.time()
            
            embeddings, embedding_token_usage = self.openai_service.generate_embeddings([question])
            question_embedding = embeddings[0] if embeddings else None
            
            if not question_embedding:
                raise ValueError("生成问题向量失败")
            
            metrics['embedding_time'] = time.time() - embed_start
            if embedding_token_usage:
                metrics['token_usage']['embedding'] = embedding_token_usage
            
            # 2. 智能确定检索参数
            retrieval_params = self._determine_retrieval_params(
                question, limit, score_threshold
            )
            
            # 3. 在 Qdrant 中检索相似文档
            retrieval_start = time.time()
            
            relevant_docs = self.qdrant_service.search(
                query_embedding=question_embedding,
                limit=retrieval_params['limit'],
                score_threshold=retrieval_params['score_threshold'],
                query_text=question
            )
            
            metrics['retrieval_time'] = time.time() - retrieval_start
            metrics['documents_retrieved'] = len(relevant_docs)
            
            # 4. 如果没有找到足够的文档，降级检索
            if len(relevant_docs) < retrieval_params.get('min_docs', 1):
                logger.warning(f"检索到的文档数量不足 ({len(relevant_docs)})，尝试降级检索")
                relevant_docs = self._fallback_retrieval(question_embedding, question)
                metrics['used_fallback'] = True
            
            # 5. 流式生成回答
            generation_start = time.time()
            
            async for content, token_usage in self.openai_service.stream_answer(
                question=question,
                context=relevant_docs
            ):
                if content:
                    # 生成过程中，只返回内容
                    yield (content, None, None)
                elif token_usage:
                    # 生成完成，返回来源和指标
                    metrics['generation_time'] = time.time() - generation_start
                    metrics['token_usage']['generation'] = token_usage
                    
                    # 提取文档来源
                    sources = self._extract_sources(relevant_docs)
                    metrics['documents_used'] = len(sources)
                    
                    # 计算总耗时
                    metrics['total_time'] = time.time() - start_time
                    
                    # 计算总token使用量
                    total_tokens = 0
                    if embedding_token_usage:
                        total_tokens += embedding_token_usage.get('total_tokens', 0)
                    if token_usage:
                        total_tokens += token_usage.get('total_tokens', 0)
                    metrics['token_usage']['total'] = total_tokens
                    
                    logger.info(
                        f"[RAG Stream] 完成查询处理: "
                        f"检索={metrics['documents_retrieved']}文档, "
                        f"使用={metrics['documents_used']}文档, "
                        f"tokens={total_tokens}, "
                        f"耗时={metrics['total_time']:.2f}s"
                    )
                    
                    yield (None, sources, metrics)
            
        except Exception as e:
            logger.error(f"[RAG Stream] 查询处理失败: {e}", exc_info=True)
            metrics['error'] = str(e)
            raise
    
    def _determine_retrieval_params(
        self,
        question: str,
        limit: int = None,
        score_threshold: float = None
    ) -> Dict:
        """
        智能确定检索参数（基于问题长度和复杂度）
        
        Args:
            question: 用户问题
            limit: 指定的返回数量
            score_threshold: 指定的相似度阈值
            
        Returns:
            检索参数字典
        """
        question_length = len(question.strip())
        
        # 短问题使用更宽松的检索策略
        if question_length <= SearchConfig.SHORT_QUERY_THRESHOLD:
            default_limit = SearchConfig.SHORT_QUERY_LIMIT
            default_threshold = SearchConfig.SHORT_QUERY_THRESHOLD_SCORE
            min_docs = 5
        else:
            default_limit = SearchConfig.NORMAL_QUERY_LIMIT
            default_threshold = SearchConfig.NORMAL_QUERY_THRESHOLD_SCORE
            min_docs = 3
        
        return {
            'limit': limit if limit is not None else default_limit,
            'score_threshold': score_threshold if score_threshold is not None else default_threshold,
            'min_docs': min_docs
        }
    
    def _fallback_retrieval(
        self,
        question_embedding: List[float],
        question: str
    ) -> List[Dict]:
        """
        降级检索策略（当主检索结果不足时）
        
        Args:
            question_embedding: 问题向量
            question: 问题文本
            
        Returns:
            检索到的文档列表
        """
        try:
            # 使用更宽松的阈值重新检索
            return self.qdrant_service.search(
                query_embedding=question_embedding,
                limit=SearchConfig.FALLBACK_LIMIT,
                score_threshold=SearchConfig.FALLBACK_THRESHOLD_SCORE,
                query_text=question
            )
        except Exception as e:
            logger.error(f"降级检索失败: {e}")
            return []
    
    def _extract_sources(self, documents: List[Dict]) -> List[Dict]:
        """
        从文档中提取来源信息
        
        Args:
            documents: 文档列表
            
        Returns:
            来源信息列表
        """
        sources = []
        seen_files = set()
        
        for doc in documents:
            metadata = doc.get('metadata', {})
            filename = metadata.get('filename', '未知文档')
            
            # 去重（同一文件只显示一次）
            if filename in seen_files:
                continue
            seen_files.add(filename)
            
            source = {
                'filename': filename,
                'file_type': metadata.get('file_type', ''),
                'score': doc.get('score', 0.0),
                'chunk_index': metadata.get('chunk_index', 0)
            }
            sources.append(source)
        
        # 按相关度排序
        sources = sorted(sources, key=lambda x: x['score'], reverse=True)
        
        # 限制来源数量
        return sources[:ProcessingConfig.MAX_CONTEXT_DOCS]


# 全局单例
_rag_service_instance = None

def get_rag_service() -> RAGService:
    """获取 RAG 服务实例（单例模式）"""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance

# 便捷访问
rag_service = get_rag_service()





