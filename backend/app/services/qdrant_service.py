"""
Qdrant 向量数据库服务
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings
from app.core.constants import QdrantConfig, CacheConfig, ProcessingConfig, SearchConfig
from app.services.cache_service import cache_service
from app.utils.retry import qdrant_retry, qdrant_operation_retry
from typing import List, Dict, Optional
import logging
import uuid

logger = logging.getLogger(__name__)


class QdrantService:
    """Qdrant 向量数据库服务"""
    
    def __init__(self):
        self._client = None
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self._initialized = False
    
    @qdrant_retry
    def _create_client(self):
        if not settings.QDRANT_URL or not settings.QDRANT_API_KEY:
            raise ValueError(
                "Qdrant 配置未设置。请在 .env 文件中配置 QDRANT_URL 和 QDRANT_API_KEY"
            )
        return QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
    
    def _reset_client(self):
        self._client = None
        self._initialized = False
    
    @property
    def client(self):
        if self._client is None:
            try:
                self._client = self._create_client()
                self._ensure_collection()
            except Exception as e:
                logger.error(f"创建 Qdrant 客户端失败: {e}", exc_info=True)
                self._reset_client()
                raise
        return self._client
    
    @qdrant_operation_retry
    def _get_collections(self):
        return self._client.get_collections().collections
    
    @qdrant_operation_retry
    def _create_collection(self, collection_name: str, vector_size: int):
        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )
    
    @qdrant_operation_retry
    def _get_collection_info(self, collection_name: str):
        return self._client.get_collection(collection_name)
    
    def _ensure_collection(self):
        if self._initialized:
            return
        
        try:
            collections = self._get_collections()
            collection_names = [col.name for col in collections]
            
            embedding_model = settings.OPENAI_EMBEDDING_MODEL
            if "text-embedding-3-large" in embedding_model:
                vector_size = 3072
            elif "text-embedding-3-small" in embedding_model:
                vector_size = 1536
            elif "text-embedding-ada-002" in embedding_model:
                vector_size = 1536
            else:
                vector_size = 1536
                logger.warning(f"未知的 embedding 模型 {embedding_model}，使用默认维度 1536")
            
            if self.collection_name not in collection_names:
                self._create_collection(self.collection_name, vector_size)
                logger.info(f"创建集合: {self.collection_name}，向量维度: {vector_size}")
            else:
                try:
                    collection_info = self._get_collection_info(self.collection_name)
                    existing_size = collection_info.config.params.vectors.size
                    if existing_size != vector_size:
                        logger.warning(
                            f"集合 {self.collection_name} 的向量维度 ({existing_size}) "
                            f"与配置的 embedding 模型维度 ({vector_size}) 不匹配。"
                            f"请删除集合并重新创建，或修改 embedding 模型配置。"
                        )
                except Exception as parse_error:
                    logger.warning(f"无法解析集合信息（可能是版本兼容性问题）: {parse_error}")
                    logger.info("继续使用现有集合，但可能无法验证维度匹配")
            
            self._initialized = True
        except Exception as e:
            logger.error(f"确保集合存在失败: {e}", exc_info=True)
            if settings.MODE == "development":
                logger.warning("Qdrant 连接或验证失败，但开发模式允许继续运行。某些功能可能不可用。")
                self._initialized = True
            else:
                raise
    
    @qdrant_operation_retry
    def _upsert_points(self, points: List[PointStruct]):
        """插入/更新点（带重试）"""
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict]
    ) -> List[str]:
        """
        添加文档到向量数据库
        
        Args:
            texts: 文本列表
            embeddings: 向量列表
            metadata: 元数据列表
            
        Returns:
            文档ID列表
        """
        try:
            points = []
            for i, (text, embedding, meta) in enumerate(zip(texts, embeddings, metadata)):
                point_id = str(uuid.uuid4())
                payload = {
                    "text": text,
                    **meta
                }
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                )
            
            self._upsert_points(points)
            
            logger.info(f"成功添加 {len(points)} 个文档到向量数据库")
            return [point.id for point in points]
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            raise
    
    @qdrant_operation_retry
    def _search_points(self, query_embedding: List[float], limit: int, score_threshold: float = None):
        """搜索点（带重试）"""
        if score_threshold and score_threshold > 0:
            return self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )
        else:
            return self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit
            )
    
    def search(
        self,
        query_embedding: List[float],
        limit: int = QdrantConfig.DEFAULT_SEARCH_LIMIT,
        score_threshold: float = QdrantConfig.DEFAULT_SCORE_THRESHOLD,
        query_text: str = None
    ) -> List[Dict]:
        """
        向量相似度搜索（优化版：智能缓存、去重、重排序）
        
        Args:
            query_embedding: 查询向量
            limit: 返回结果数量
            score_threshold: 相似度阈值
            query_text: 查询文本（用于关键词匹配优先级）
            
        Returns:
            搜索结果列表，每个包含 content 和 metadata
        """
        import time
        import hashlib
        start_time = time.time()
        
        # 检查缓存是否启用
        if CacheConfig.ENABLE_CACHE:
            # 使用embedding的哈希值作为缓存键（更准确）
            embedding_hash = hashlib.md5(
                str(query_embedding).encode()
            ).hexdigest()[:16]
            
            cache_key = cache_service.cache_key(
                CacheConfig.SEARCH_CACHE_PREFIX,
                embedding_hash=embedding_hash,
                limit=limit,
                score_threshold=score_threshold,
                query_text=query_text,
                collection=self.collection_name
            )
            
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                logger.info(f"检索结果缓存命中 (耗时: {time.time() - start_time:.3f}s)")
                return cached_result
        
        try:
            search_limit = limit * SearchConfig.EXPANDED_SEARCH_MULTIPLIER if query_text else limit
            
            results = self._search_points(query_embedding, search_limit, score_threshold)
            
            documents = []
            seen_contents = set()
            seen_file_chunks = {}
            
            for result in results:
                content = result.payload.get("text", "").strip()
                if not content:
                    continue
                
                content_fingerprint = content[:100]
                if content_fingerprint in seen_contents:
                    continue
                seen_contents.add(content_fingerprint)
                
                file_id = result.payload.get("file_id", "unknown")
                chunk_count = seen_file_chunks.get(file_id, 0)
                if chunk_count >= ProcessingConfig.MAX_CHUNKS_PER_FILE:
                    continue
                seen_file_chunks[file_id] = chunk_count + 1
                
                doc = {
                    "content": content,
                    "metadata": {
                        k: v for k, v in result.payload.items() if k != "text"
                    },
                    "score": result.score
                }
                
                if query_text:
                    query_lower = query_text.lower()
                    content_lower = content.lower()
                    
                    doc["has_exact_match"] = query_lower in content_lower
                    
                    keywords = query_lower.split()
                    match_count = sum(1 for kw in keywords if kw in content_lower)
                    doc["keyword_match_count"] = match_count
                    doc["has_keyword"] = match_count > 0
                
                documents.append(doc)
            
            if query_text:
                def sort_key(doc):
                    if doc.get("has_exact_match", False):
                        return (3, doc["score"])
                    elif doc.get("keyword_match_count", 0) > 1:
                        return (2, doc["score"])
                    elif doc.get("has_keyword", False):
                        return (1, doc["score"])
                    else:
                        return (0, doc["score"])
                
                documents = sorted(documents, key=sort_key, reverse=True)
                
                exact_match_count = sum(1 for d in documents if d.get("has_exact_match", False))
                keyword_match_count = sum(1 for d in documents if d.get("has_keyword", False))
                
                logger.info(
                    f"检索完成: 完全匹配={exact_match_count}, "
                    f"关键词匹配={keyword_match_count}, "
                    f"总文档={len(documents)}, "
                    f"耗时={time.time() - start_time:.3f}s"
                )
            else:
                documents = sorted(documents, key=lambda x: x["score"], reverse=True)
                logger.info(
                    f"检索完成: 返回{len(documents)}个文档, "
                    f"耗时={time.time() - start_time:.3f}s"
                )
            
            documents = documents[:limit]
            
            if CacheConfig.ENABLE_CACHE:
                embedding_hash = hashlib.md5(
                    str(query_embedding).encode()
                ).hexdigest()[:16]
                
                cache_key = cache_service.cache_key(
                    CacheConfig.SEARCH_CACHE_PREFIX,
                    embedding_hash=embedding_hash,
                    limit=limit,
                    score_threshold=score_threshold,
                    query_text=query_text,
                    collection=self.collection_name
                )
                cache_service.set(
                    cache_key,
                    documents,
                    ttl=CacheConfig.SEARCH_RESULT_CACHE_TTL
                )
            
            return documents
        except Exception as e:
            logger.error(f"向量搜索失败: {e}", exc_info=True)
            if settings.MODE == "development":
                logger.warning("向量搜索失败，返回空结果")
                return []
            raise
    
    @qdrant_operation_retry
    def _scroll_points(self, filter_condition, limit: int):
        """滚动查询点（带重试）"""
        return self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=filter_condition,
            limit=limit,
            with_payload=False,
            with_vectors=False
        )
    
    @qdrant_operation_retry
    def _delete_points(self, point_ids: List):
        """删除点（带重试）"""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=point_ids,
            wait=True
        )
    
    def delete_documents(self, file_id: str = None, filename: str = None):
        """
        删除指定文件的所有文档（同时清除相关缓存）
        
        Args:
            file_id: 文件ID（文件名不含扩展名）
            filename: 文件名（完整文件名）
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            if file_id:
                filter_condition = Filter(
                    must=[
                        FieldCondition(
                            key="file_id",
                            match=MatchValue(value=file_id)
                        )
                    ]
                )
            elif filename:
                filter_condition = Filter(
                    must=[
                        FieldCondition(
                            key="filename",
                            match=MatchValue(value=filename)
                        )
                    ]
                )
            else:
                raise ValueError("必须提供 file_id 或 filename")
            
            scroll_result = self._scroll_points(filter_condition, QdrantConfig.MAX_DELETE_POINTS)
            
            point_ids = [point.id for point in scroll_result[0]]
            
            if not point_ids:
                logger.info(f"未找到匹配的文档: file_id={file_id}, filename={filename}")
                return 0
            
            self._delete_points(point_ids)
            
            deleted_count = len(point_ids)
            logger.info(f"成功删除 {deleted_count} 个文档块: file_id={file_id}, filename={filename}")
            
            # 清除搜索缓存（因为知识库已更新）
            if CacheConfig.ENABLE_CACHE:
                cache_service.clear(prefix=CacheConfig.SEARCH_CACHE_PREFIX)
                logger.info("已清除搜索缓存")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"删除文档失败: {e}", exc_info=True)
            raise
    
    @qdrant_operation_retry
    def _scroll_all_points(self, limit: int, offset=None):
        """滚动查询所有点（带重试）"""
        return self.client.scroll(
            collection_name=self.collection_name,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
    
    def get_all_documents(self) -> List[Dict]:
        """
        获取所有文档的元数据
        
        Returns:
            文档元数据列表，每个包含 file_id, filename, file_type, upload_time 等信息
        """
        try:
            all_points = []
            next_page_offset = None
            
            while True:
                scroll_result = self._scroll_all_points(1000, next_page_offset)
                
                points, next_page_offset = scroll_result
                all_points.extend(points)
                
                if next_page_offset is None:
                    break
            
            documents = []
            for point in all_points:
                payload = point.payload
                if "file_id" in payload:
                    doc = {
                        "file_id": payload.get("file_id"),
                        "filename": payload.get("filename", "未知文件"),
                        "file_type": payload.get("file_type", ""),
                        "file_size": payload.get("file_size", 0),
                        "upload_time": payload.get("upload_time", ""),
                        "chunk_index": payload.get("chunk_index", 0)
                    }
                    documents.append(doc)
            
            logger.info(f"从 Qdrant 获取到 {len(documents)} 个文档块")
            return documents
            
        except Exception as e:
            logger.error(f"获取文档列表失败: {e}", exc_info=True)
            if settings.MODE == "development":
                logger.warning("获取文档列表失败，返回空列表")
                return []
            raise

_qdrant_service_instance = None

def get_qdrant_service() -> QdrantService:
    """获取 Qdrant 服务实例（单例模式）"""
    global _qdrant_service_instance
    if _qdrant_service_instance is None:
        _qdrant_service_instance = QdrantService()
    return _qdrant_service_instance

class QdrantServiceProxy:
    """Qdrant 服务代理，延迟初始化"""
    def __getattr__(self, name):
        service = get_qdrant_service()
        return getattr(service, name)

qdrant_service = QdrantServiceProxy()

