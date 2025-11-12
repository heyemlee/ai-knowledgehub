#!/usr/bin/env python3
"""
检查知识库内容和检索功能

使用方法:
    python scripts/check_knowledge_base.py
    
功能:
    - 检查 Qdrant 集合中的文档数量
    - 测试检索功能
    - 显示文档片段示例
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
from app.services.openai_service import openai_service
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_collection():
    """检查集合信息"""
    try:
        client = qdrant_service.client
        collection_name = settings.QDRANT_COLLECTION_NAME
        
        print(f"\n📊 集合信息: {collection_name}")
        
        # 使用 scroll 方法检查文档数量（避免版本兼容性问题）
        try:
            scroll_result = client.scroll(
                collection_name=collection_name,
                limit=1,
                with_payload=False,
                with_vectors=False
            )
            # 尝试获取更多点来估算总数
            count_result = client.count(
                collection_name=collection_name
            )
            point_count = count_result.count if hasattr(count_result, 'count') else 0
            
            if point_count > 0:
                print(f"   ✓ 向量数量: {point_count}")
                # 尝试获取第一个点的向量维度
                if scroll_result[0]:
                    first_point = scroll_result[0][0]
                    if hasattr(first_point, 'vector') and first_point.vector:
                        dim = len(first_point.vector) if isinstance(first_point.vector, list) else 0
                        if dim > 0:
                            print(f"   ✓ 向量维度: {dim}")
                return True
            else:
                print(f"   ⚠️  向量数量: 0（集合为空）")
                return False
        except Exception as scroll_error:
            logger.warning(f"使用 scroll 检查失败: {scroll_error}")
            # 尝试使用集合列表检查
            collections = client.get_collections().collections
            if collection_name in [col.name for col in collections]:
                print(f"   ✓ 集合存在（无法获取详细信息，可能是版本兼容性问题）")
                return True
            else:
                print(f"   ⚠️  集合不存在")
                return False
        
    except Exception as e:
        logger.error(f"检查集合失败: {e}", exc_info=True)
        print(f"   ⚠️  检查失败（可能是版本兼容性问题）")
        # 即使失败，也尝试继续执行其他检查
        return None  # 返回 None 表示不确定


def test_search(query: str):
    """测试检索功能"""
    try:
        print(f"\n🔍 测试检索: '{query}'")
        print("-" * 60)
        
        # 生成查询向量
        embeddings = openai_service.generate_embeddings([query])
        query_embedding = embeddings[0]
        
        # 执行检索（使用极低阈值）
        results = qdrant_service.search(
            query_embedding=query_embedding,
            limit=10,
            score_threshold=0.0  # 无阈值，返回所有结果
        )
        
        print(f"找到 {len(results)} 个文档片段")
        
        if results:
            print("\n前5个结果：")
            for i, doc in enumerate(results[:5], 1):
                score = doc.get('score', 0)
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                filename = metadata.get('filename', '未知')
                
                print(f"\n[{i}] 相似度: {score:.2%} | 来源: {filename}")
                print(f"    内容: {content[:300]}...")
                
                # 检查是否包含查询关键词
                if query in content:
                    print(f"    ✓ 包含关键词 '{query}'")
        else:
            print("⚠️  未找到任何文档片段")
        
        return len(results) > 0
        
    except Exception as e:
        logger.error(f"测试检索失败: {e}", exc_info=True)
        return False


def list_all_documents():
    """列出所有文档片段（用于调试）"""
    try:
        client = qdrant_service.client
        collection_name = settings.QDRANT_COLLECTION_NAME
        
        print("\n📚 列出所有文档片段（前20个）...")
        print("-" * 60)
        
        # 滚动获取所有点
        try:
            scroll_result = client.scroll(
                collection_name=collection_name,
                limit=20,
                with_payload=True,
                with_vectors=False
            )
            points = scroll_result[0] if isinstance(scroll_result, tuple) else scroll_result
        except Exception as e:
            logger.warning(f"使用 scroll 获取文档失败: {e}")
            # 尝试使用 count + search 组合
            try:
                # 先搜索获取一些点
                dummy_embedding = [0.0] * 1536  # 使用零向量
                search_results = client.search(
                    collection_name=collection_name,
                    query_vector=dummy_embedding,
                    limit=20
                )
                points = []
                for result in search_results:
                    # 构建类似 scroll 结果的格式
                    class Point:
                        def __init__(self, payload):
                            self.payload = payload
                    points.append(Point(result.payload))
            except Exception as e2:
                logger.error(f"获取文档失败: {e2}")
                return False
        
        print(f"总共找到 {len(points)} 个文档片段（显示前20个）\n")
        
        # 按文件名分组
        doc_groups = {}
        for point in points:
            payload = point.payload
            filename = payload.get('filename', '未知')
            if filename not in doc_groups:
                doc_groups[filename] = []
            doc_groups[filename].append(payload)
        
        for filename, docs in doc_groups.items():
            print(f"\n📄 文件: {filename} ({len(docs)} 个片段)")
            for i, doc in enumerate(docs[:3], 1):  # 每个文件只显示前3个片段
                content = doc.get('text', '')[:150]
                print(f"  片段 {i}: {content}...")
        
        return len(points) > 0
        
    except Exception as e:
        logger.error(f"列出文档失败: {e}", exc_info=True)
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("知识库诊断工具")
    print("=" * 60)
    
    # 检查配置
    try:
        if not settings.OPENAI_API_KEY:
            print("\n❌ 错误: OPENAI_API_KEY 未配置")
            sys.exit(1)
        
        if not settings.QDRANT_URL or not settings.QDRANT_API_KEY:
            print("\n❌ 错误: Qdrant 配置未设置")
            sys.exit(1)
    except Exception as e:
        logger.error(f"配置检查失败: {e}")
        sys.exit(1)
    
    # 1. 检查集合
    print("\n" + "=" * 60)
    print("1. 检查集合")
    print("=" * 60)
    has_documents = check_collection()
    
    if has_documents is False:
        print("\n⚠️  集合中没有文档！")
        print("请先运行批量导入脚本：")
        print("  python scripts/batch_import.py")
        sys.exit(1)
    elif has_documents is None:
        print("\n⚠️  无法确定集合状态（可能是版本兼容性问题）")
        print("继续执行其他检查...")
    
    # 2. 列出文档片段
    print("\n" + "=" * 60)
    print("2. 列出文档片段")
    print("=" * 60)
    list_all_documents()
    
    # 3. 测试检索
    print("\n" + "=" * 60)
    print("3. 测试检索功能")
    print("=" * 60)
    
    test_queries = [
        "公司产品",
        "公司地址",
        "橱柜材质",
        "公司名字"
    ]
    
    for query in test_queries:
        test_search(query)
    
    print("\n" + "=" * 60)
    print("诊断完成！")
    print("=" * 60)
    print("\n💡 提示：")
    print("- 如果检索不到结果，可能是文档未正确导入")
    print("- 如果检索到结果但AI回答不准确，可能是文档切分问题")
    print("- 检查后端日志中的'检索到的文档片段预览'以查看实际检索到的内容")


if __name__ == "__main__":
    main()

