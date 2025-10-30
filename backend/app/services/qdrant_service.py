"""
Qdrant 向量数据库服务
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings
from typing import List, Dict, Optional
import logging
import uuid

logger = logging.getLogger(__name__)


class QdrantService:
    """Qdrant 向量数据库服务"""
    
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self._ensure_collection()
    
    def _ensure_collection(self):
        """确保集合存在，不存在则创建"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # text-embedding-3-large 的向量维度
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"创建集合: {self.collection_name}")
        except Exception as e:
            logger.error(f"确保集合存在失败: {e}")
            raise
    
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
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"成功添加 {len(points)} 个文档到向量数据库")
            return [point.id for point in points]
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            raise
    
    def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict]:
        """
        向量相似度搜索
        
        Args:
            query_embedding: 查询向量
            limit: 返回结果数量
            score_threshold: 相似度阈值
            
        Returns:
            搜索结果列表，每个包含 content 和 metadata
        """
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )
            
            documents = []
            for result in results:
                documents.append({
                    "content": result.payload.get("text", ""),
                    "metadata": {
                        k: v for k, v in result.payload.items() if k != "text"
                    },
                    "score": result.score
                })
            
            return documents
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            raise
    
    def delete_documents(self, file_id: str):
        """
        删除指定文件的所有文档
        
        Args:
            file_id: 文件ID
        """
        try:
            # 注意：Qdrant 的删除需要先查询出所有匹配的点
            # 这里简化处理，实际可能需要使用过滤器
            logger.info(f"删除文件 {file_id} 的文档")
            # TODO: 实现基于 file_id 的删除逻辑
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            raise


# 全局实例
qdrant_service = QdrantService()

