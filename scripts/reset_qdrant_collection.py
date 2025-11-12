#!/usr/bin/env python3
"""
重置 Qdrant 集合（删除并重新创建）

使用方法:
    python scripts/reset_qdrant_collection.py

注意：这将删除集合中的所有数据！
"""
import sys
import os
from pathlib import Path

# 添加项目根目录和 backend 目录到 Python 路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(project_root))

os.chdir(str(backend_dir))

from app.services.qdrant_service import qdrant_service
from app.core.config import settings
from qdrant_client.models import Distance, VectorParams
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reset_collection():
    """删除并重新创建 Qdrant 集合"""
    try:
        client = qdrant_service.client
        collection_name = settings.QDRANT_COLLECTION_NAME
        
        # 确定向量维度
        embedding_model = settings.OPENAI_EMBEDDING_MODEL
        if "text-embedding-3-large" in embedding_model:
            vector_size = 3072
        elif "text-embedding-3-small" in embedding_model:
            vector_size = 1536
        else:
            vector_size = 1536
        
        print(f"集合名称: {collection_name}")
        print(f"Embedding 模型: {embedding_model}")
        print(f"向量维度: {vector_size}")
        print("\n⚠️  警告：这将删除集合中的所有数据！")
        
        response = input("确认删除并重新创建集合？(yes/no): ")
        if response.lower() != 'yes':
            print("已取消操作")
            return
        
        # 删除现有集合（如果存在）
        try:
            collections = client.get_collections().collections
            if collection_name in [col.name for col in collections]:
                print(f"\n删除现有集合: {collection_name}")
                client.delete_collection(collection_name)
                print("✓ 集合已删除")
        except Exception as e:
            logger.warning(f"删除集合时出错（可能不存在）: {e}")
        
        # 创建新集合
        print(f"\n创建新集合: {collection_name}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )
        print(f"✓ 集合已创建，向量维度: {vector_size}")
        print("\n✅ 完成！现在可以重新运行批量导入脚本了。")
        
    except Exception as e:
        logger.error(f"重置集合失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    import os
    reset_collection()

