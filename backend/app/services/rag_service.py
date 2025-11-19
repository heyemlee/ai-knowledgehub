from typing import List, Dict, Optional, AsyncGenerator, Tuple
from app.services.openai_service import openai_service
from app.services.qdrant_service import qdrant_service
from app.core.constants import SearchConfig, ProcessingConfig, RerankConfig
import logging
import time
import asyncio

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.openai_service = openai_service
        self.qdrant_service = qdrant_service
    
    def process_query(
        self,
        question: str,
        limit: int = None,
        score_threshold: float = None
    ) -> Tuple[str, List[Dict], Dict]:
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
        start_time = time.time()
        metrics = {
            'question_length': len(question),
            'embedding_time': 0,
            'keyword_extraction_time': 0,
            'parallel_time': 0,
            'retrieval_time': 0,
            'rerank_time': 0,
            'generation_time': 0,
            'total_time': 0,
            'documents_retrieved': 0,
            'documents_after_rerank': 0,
            'documents_used': 0,
            'token_usage': {}
        }
        
        try:
            # 1. 并行执行：生成问题向量嵌入 + 提取关键词（优化：并行处理）
            logger.info(f"[RAG Stream] 开始处理问题: {question[:50]}...")
            parallel_start = time.time()
            
            # 创建并行任务
            async def generate_embedding_task():
                embed_start = time.time()
                # 在异步环境中调用同步函数，使用 run_in_executor
                loop = asyncio.get_event_loop()
                embeddings, token_usage = await loop.run_in_executor(
                    None, 
                    self.openai_service.generate_embeddings, 
                    [question]
                )
                embed_time = time.time() - embed_start
                return embeddings, token_usage, embed_time
            
            async def extract_keywords_task():
                keyword_start = time.time()
                loop = asyncio.get_event_loop()
                keywords, token_usage = await loop.run_in_executor(
                    None,
                    self.openai_service.extract_keywords,
                    question
                )
                keyword_time = time.time() - keyword_start
                return keywords, token_usage, keyword_time
            
            # 并行执行两个任务
            (embeddings, embedding_token_usage, embed_time), \
            (keywords, keyword_token_usage, keyword_time) = await asyncio.gather(
                generate_embedding_task(),
                extract_keywords_task()
            )
            
            question_embedding = embeddings[0] if embeddings else None
            
            if not question_embedding:
                raise ValueError("生成问题向量失败")
            
            metrics['parallel_time'] = time.time() - parallel_start
            metrics['embedding_time'] = embed_time
            metrics['keyword_extraction_time'] = keyword_time
            
            if embedding_token_usage:
                metrics['token_usage']['embedding'] = embedding_token_usage
            if keyword_token_usage:
                metrics['token_usage']['keyword_extraction'] = keyword_token_usage
            
            logger.info(f"[并行优化] Embedding: {embed_time:.3f}s, 关键词: {keyword_time:.3f}s, 总耗时: {metrics['parallel_time']:.3f}s（节省 {max(embed_time, keyword_time) - metrics['parallel_time']:.3f}s）")
            
            # 2. 智能确定检索参数（Rerank 模式：检索更多文档）
            if RerankConfig.ENABLE_RERANK:
                # 启用 Rerank 时，检索更多文档（10个）
                retrieval_limit = RerankConfig.INITIAL_RETRIEVAL_LIMIT
                final_limit = RerankConfig.FINAL_TOP_K
            else:
                # 未启用 Rerank 时，使用原有逻辑
                retrieval_params = self._determine_retrieval_params(
                    question, limit, score_threshold
                )
                retrieval_limit = retrieval_params['limit']
                final_limit = retrieval_limit
            
            # 3. 在 Qdrant 中检索相似文档（优化：使用 ef_search=128）
            retrieval_start = time.time()
            
            relevant_docs = self.qdrant_service.search(
                query_embedding=question_embedding,
                limit=retrieval_limit,
                score_threshold=score_threshold or SearchConfig.NORMAL_QUERY_THRESHOLD_SCORE,
                query_text=question
            )
            
            metrics['retrieval_time'] = time.time() - retrieval_start
            metrics['documents_retrieved'] = len(relevant_docs)
            
            logger.info(f"[检索完成] 使用 ef_search=128，检索到 {len(relevant_docs)} 个文档，耗时 {metrics['retrieval_time']:.3f}s")
            
            # 4. 如果没有找到足够的文档，降级检索
            if len(relevant_docs) < 1:
                logger.warning(f"检索到的文档数量不足，尝试降级检索")
                relevant_docs = self._fallback_retrieval(question_embedding, question)
                metrics['used_fallback'] = True
            
            # 5. Rerank：使用 GPT-4o-mini 重排序（优化：Rerank）
            if RerankConfig.ENABLE_RERANK and len(relevant_docs) > 0:
                rerank_start = time.time()
                
                loop = asyncio.get_event_loop()
                reranked_docs, rerank_token_usage = await loop.run_in_executor(
                    None,
                    self.openai_service.rerank_documents,
                    question,
                    relevant_docs,
                    final_limit
                )
                
                metrics['rerank_time'] = time.time() - rerank_start
                metrics['documents_after_rerank'] = len(reranked_docs)
                
                if rerank_token_usage:
                    metrics['token_usage']['rerank'] = rerank_token_usage
                
                logger.info(f"[Rerank 完成] 从 {len(relevant_docs)} 个文档中选出 {len(reranked_docs)} 个，耗时 {metrics['rerank_time']:.3f}s")
                
                # 使用重排序后的文档
                relevant_docs = reranked_docs
            else:
                # 未启用 Rerank，直接截取
                relevant_docs = relevant_docs[:final_limit]
                metrics['documents_after_rerank'] = len(relevant_docs)
            
            # 6. 流式生成回答
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
                    for key in ['embedding', 'keyword_extraction', 'rerank', 'generation']:
                        if key in metrics['token_usage']:
                            total_tokens += metrics['token_usage'][key].get('total_tokens', 0)
                    metrics['token_usage']['total'] = total_tokens
                    
                    logger.info(
                        f"[RAG Stream] 完成查询处理: "
                        f"检索={metrics['documents_retrieved']}文档, "
                        f"Rerank后={metrics['documents_after_rerank']}文档, "
                        f"使用={metrics['documents_used']}文档, "
                        f"tokens={total_tokens}, "
                        f"耗时={metrics['total_time']:.2f}s "
                        f"(并行={metrics['parallel_time']:.2f}s, "
                        f"检索={metrics['retrieval_time']:.2f}s, "
                        f"Rerank={metrics.get('rerank_time', 0):.2f}s, "
                        f"生成={metrics['generation_time']:.2f}s)"
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


_rag_service_instance = None

def get_rag_service() -> RAGService:
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance

rag_service = get_rag_service()
