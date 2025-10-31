#!/usr/bin/env python3
"""
批量导入文档到 Qdrant 向量数据库

使用方法:
    python scripts/batch_import.py

功能:
    - 扫描 documents/ 目录下的所有文档
    - 支持 PDF、Word、Excel、TXT 格式
    - 自动解析、切块、生成向量并导入 Qdrant
    - 自动检测并删除重复文档（避免数据冗余）
    - 显示导入进度和统计信息

特性:
    - 如果文档已存在，会自动删除旧数据后再导入新数据
    - 避免重复导入导致的重复内容和数据冗余
    - 减少存储空间和 API 调用成本
"""
import sys
import os
from pathlib import Path
from typing import List
import logging
from datetime import datetime

# 添加项目根目录和 backend 目录到 Python 路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(project_root))

# 设置环境变量（如果需要）
os.chdir(str(backend_dir))

from app.services.openai_service import openai_service
from app.services.qdrant_service import qdrant_service
from app.services.s3_service import s3_service
from app.utils.document_parser import DocumentParser
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 支持的文档格式
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt'}


def scan_documents(documents_dir: Path) -> List[Path]:
    """
    扫描文档目录，返回所有支持的文档文件
    
    Args:
        documents_dir: 文档目录路径
        
    Returns:
        文档文件路径列表
    """
    documents = []
    if not documents_dir.exists():
        logger.warning(f"文档目录不存在: {documents_dir}")
        return documents
    
    for file_path in documents_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            documents.append(file_path)
    
    return sorted(documents)


def process_document(file_path: Path, parser: DocumentParser, documents_dir: Path) -> tuple:
    """
    处理单个文档：解析、切块、生成向量
    
    Args:
        file_path: 文档路径
        parser: 文档解析器
        
    Returns:
        (文本块列表, 元数据列表) 或 (None, None) 如果失败
    """
    try:
        logger.info(f"处理文档: {file_path.name}")
        
        # 读取文件内容（使用二进制模式以支持中文文件名）
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            raise
        
        # 解析文档
        texts = []
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.pdf':
            texts = parser.parse_pdf(file_content)
        elif file_extension in ['.docx', '.doc']:
            texts = parser.parse_docx(file_content)
        elif file_extension in ['.xlsx', '.xls']:
            texts = parser.parse_excel(file_content)
        elif file_extension == '.txt':
            texts = [file_content.decode('utf-8', errors='ignore')]
        else:
            logger.warning(f"不支持的文件格式: {file_extension}")
            return None, None
        
        if not texts:
            logger.warning(f"文档解析后为空: {file_path.name}")
            return None, None
        
        # 文本切块
        # 使用统一的配置常量
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
        from app.core.constants import DocumentParserConfig
        
        chunks = parser.chunk_text(
            texts, 
            chunk_size=DocumentParserConfig.DEFAULT_CHUNK_SIZE, 
            overlap=DocumentParserConfig.DEFAULT_OVERLAP
        )
        logger.info(f"  生成 {len(chunks)} 个文本块")
        
        # 构建元数据
        try:
            # 尝试获取相对于项目根目录的路径
            relative_path = str(file_path.relative_to(project_root))
        except (ValueError, TypeError):
            # 如果失败，使用相对于文档目录的路径
            try:
                relative_path = str(file_path.relative_to(documents_dir))
            except (ValueError, TypeError):
                relative_path = file_path.name
        
        metadata_list = [
            {
                "file_id": str(file_path.stem),
                "filename": file_path.name,
                "file_path": relative_path,
                "file_type": file_extension,
                "file_size": len(file_content),
                "chunk_index": i,
                "total_chunks": len(chunks),
                "import_time": datetime.utcnow().isoformat()
            }
            for i in range(len(chunks))
        ]
        
        return chunks, metadata_list
    
    except Exception as e:
        logger.error(f"处理文档失败 {file_path.name}: {e}", exc_info=True)
        return None, None


def import_to_qdrant(chunks: List[str], metadata_list: List[dict], file_path: Path, check_duplicate: bool = True):
    """
    将文档块导入到 Qdrant
    
    Args:
        chunks: 文本块列表
        metadata_list: 元数据列表
        file_path: 文档路径
        check_duplicate: 是否检查并删除重复数据（默认 True）
    """
    try:
        # 检查并删除重复数据
        if check_duplicate:
            filename = file_path.name
            try:
                deleted_count = qdrant_service.delete_documents(filename=filename)
                if deleted_count > 0:
                    logger.info(f"  ⚠️  检测到已存在的文档，已删除 {deleted_count} 个旧文档块")
            except Exception as e:
                logger.debug(f"检查重复文档时出错（可能是新文档）: {e}")
        
        # 生成向量嵌入
        logger.info(f"  生成向量嵌入...")
        embeddings = openai_service.generate_embeddings(chunks)
        logger.info(f"  生成了 {len(embeddings)} 个向量")
        
        # 导入到 Qdrant
        logger.info(f"  导入到 Qdrant...")
        point_ids = qdrant_service.add_documents(
            texts=chunks,
            embeddings=embeddings,
            metadata=metadata_list
        )
        logger.info(f"  ✓ 成功导入 {len(point_ids)} 个文档块")
        return len(point_ids)
    
    except Exception as e:
        logger.error(f"导入到 Qdrant 失败 {file_path.name}: {e}", exc_info=True)
        return 0


def upload_to_s3(file_path: Path) -> str:
    """
    上传文件到 S3（可选）
    
    Args:
        file_path: 文档路径
        
    Returns:
        文件ID或空字符串
    """
    try:
        with open(file_path, 'rb') as f:
            file_id = s3_service.upload_file(
                file_obj=f,
                filename=file_path.name,
                content_type=f"application/{file_path.suffix[1:]}"
            )
        logger.info(f"  ✓ 已上传到 S3 = {file_id}")
        return file_id
    except Exception as e:
        logger.warning(f"S3 上传失败（可选）: {e}")
        return ""


def main():
    """主函数"""
    print("=" * 60)
    print("批量导入文档到 Qdrant 向量数据库")
    print("=" * 60)
    
    # 检查环境变量
    try:
        if not settings.OPENAI_API_KEY:
            print("\n❌ 错误: OPENAI_API_KEY 未配置")
            print("请在 .env 文件中设置 OPENAI_API_KEY")
            sys.exit(1)
        
        if not settings.QDRANT_URL or not settings.QDRANT_API_KEY:
            print("\n⚠️  警告: Qdrant 配置未设置")
            print("请在 .env 文件中设置 QDRANT_URL 和 QDRANT_API_KEY")
            if settings.MODE == "production":
                print("生产模式必须配置 Qdrant，退出...")
                sys.exit(1)
            print("开发模式将继续，但无法导入到 Qdrant")
    except Exception as e:
        logger.error(f"配置检查失败: {e}")
        sys.exit(1)
    
    # 文档目录（相对于项目根目录）
    documents_dir = project_root / "documents"
    
    # 创建文档目录（如果不存在）
    documents_dir.mkdir(exist_ok=True)
    print(f"\n📁 文档目录: {documents_dir}")
    
    # 扫描文档
    print("\n🔍 扫描文档...")
    documents = scan_documents(documents_dir)
    
    if not documents:
        print(f"\n⚠️  未找到任何文档文件")
        print(f"请将文档放入 {documents_dir} 目录")
        print(f"支持格式: {', '.join(SUPPORTED_EXTENSIONS)}")
        sys.exit(0)
    
    print(f"✓ 找到 {len(documents)} 个文档文件")
    for doc in documents:
        print(f"  - {doc.name}")
    
    # 初始化解析器
    parser = DocumentParser()
    
    # 统计信息
    total_files = len(documents)
    success_files = 0
    failed_files = 0
    total_chunks = 0
    total_points = 0
    
    # 处理每个文档
    print("\n" + "=" * 60)
    print("开始导入...")
    print("=" * 60)
    
    for idx, file_path in enumerate(documents, 1):
        print(f"\n[{idx}/{total_files}] {file_path.name}")
        print("-" * 60)
        
        # 处理文档
        chunks, metadata_list = process_document(file_path, parser, documents_dir)
        
        if chunks is None or metadata_list is None:
            failed_files += 1
            continue
        
        # 导入到 Qdrant
        try:
            points_count = import_to_qdrant(chunks, metadata_list, file_path)
            if points_count > 0:
                success_files += 1
                total_chunks += len(chunks)
                total_points += points_count
            else:
                failed_files += 1
        except Exception as e:
            logger.error(f"导入失败: {e}")
            failed_files += 1
        
        # 可选：上传到 S3
        try:
            if settings.S3_BUCKET_NAME:
                upload_to_s3(file_path)
        except Exception:
            pass  # S3 上传失败不影响主流程
    
    # 输出统计信息
    print("\n" + "=" * 60)
    print("导入完成！")
    print("=" * 60)
    print(f"总文件数: {total_files}")
    print(f"成功导入: {success_files}")
    print(f"失败文件: {failed_files}")
    print(f"总文本块: {total_chunks}")
    print(f"总向量点: {total_points}")
    print("=" * 60)
    
    if success_files > 0:
        print("\n✅ 导入成功！现在可以测试问答功能了。")
    else:
        print("\n❌ 没有成功导入任何文档，请检查错误日志。")
        sys.exit(1)


if __name__ == "__main__":
    main()

