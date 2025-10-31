#!/usr/bin/env python3
"""
更新文档到 Qdrant 向量数据库

功能：
- 更新指定文档（先删除旧数据，再导入新数据）
- 支持更新所有文档
- 支持更新单个文档

使用方法:
    # 更新所有文档
    python scripts/update_documents.py
    
    # 更新指定文档
    python scripts/update_documents.py --file "知识.docx"
    
    # 更新多个文档（逗号分隔）
    python scripts/update_documents.py --file "知识.docx,员工手册.pdf"
"""
import sys
import os
import argparse
from pathlib import Path
from typing import List, Optional
import logging
from datetime import datetime

# 添加项目根目录和 backend 目录到 Python 路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(project_root))

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


def scan_documents(documents_dir: Path, file_filter: Optional[List[str]] = None) -> List[Path]:
    """
    扫描文档目录，返回所有支持的文档文件
    
    Args:
        documents_dir: 文档目录路径
        file_filter: 文件名过滤列表（如果提供，只返回匹配的文件）
        
    Returns:
        文档文件路径列表
    """
    documents = []
    if not documents_dir.exists():
        logger.warning(f"文档目录不存在: {documents_dir}")
        return documents
    
    for file_path in documents_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            if file_filter:
                # 如果指定了过滤列表，只返回匹配的文件
                if any(file_path.name == f or file_path.name.startswith(f) for f in file_filter):
                    documents.append(file_path)
            else:
                documents.append(file_path)
    
    return sorted(documents)


def process_document(file_path: Path, parser: DocumentParser, documents_dir: Path) -> tuple:
    """
    处理单个文档：解析、切块
    
    Args:
        file_path: 文档路径
        parser: 文档解析器
        documents_dir: 文档目录
        
    Returns:
        (文本块列表, 元数据列表) 或 (None, None) 如果失败
    """
    try:
        logger.info(f"处理文档: {file_path.name}")
        
        # 读取文件内容
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
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
            relative_path = str(file_path.relative_to(project_root))
        except (ValueError, TypeError):
            try:
                relative_path = str(file_path.relative_to(documents_dir))
            except (ValueError, TypeError):
                relative_path = file_path.name
        
        # 使用文件名（不含扩展名）作为 file_id，方便更新
        file_id = file_path.stem
        
        metadata_list = [
            {
                "file_id": file_id,
                "filename": file_path.name,
                "file_path": relative_path,
                "file_type": file_extension,
                "file_size": len(file_content),
                "chunk_index": i,
                "total_chunks": len(chunks),
                "import_time": datetime.utcnow().isoformat(),
                "updated": True  # 标记为更新
            }
            for i in range(len(chunks))
        ]
        
        return chunks, metadata_list
    
    except Exception as e:
        logger.error(f"处理文档失败 {file_path.name}: {e}", exc_info=True)
        return None, None


def update_document(file_path: Path, parser: DocumentParser, documents_dir: Path) -> bool:
    """
    更新单个文档：先删除旧数据，再导入新数据
    
    Args:
        file_path: 文档路径
        parser: 文档解析器
        documents_dir: 文档目录
        
    Returns:
        是否成功
    """
    try:
        file_id = file_path.stem
        filename = file_path.name
        
        print(f"\n更新文档: {filename}")
        print("-" * 60)
        
        # 1. 删除旧数据
        try:
            deleted_count = qdrant_service.delete_documents(filename=filename)
            if deleted_count > 0:
                print(f"  ✓ 已删除 {deleted_count} 个旧文档块")
            else:
                print(f"  ℹ 未找到旧文档，将直接导入")
        except Exception as e:
            logger.warning(f"删除旧文档失败（可能不存在）: {e}")
        
        # 2. 处理新文档
        chunks, metadata_list = process_document(file_path, parser, documents_dir)
        
        if chunks is None or metadata_list is None:
            return False
        
        # 3. 生成向量嵌入
        logger.info(f"  生成向量嵌入...")
        embeddings = openai_service.generate_embeddings(chunks)
        logger.info(f"  生成了 {len(embeddings)} 个向量")
        
        # 4. 导入新数据
        logger.info(f"  导入到 Qdrant...")
        point_ids = qdrant_service.add_documents(
            texts=chunks,
            embeddings=embeddings,
            metadata=metadata_list
        )
        
        print(f"  ✓ 成功导入 {len(point_ids)} 个新文档块")
        return True
        
    except Exception as e:
        logger.error(f"更新文档失败 {file_path.name}: {e}", exc_info=True)
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='更新文档到 Qdrant 向量数据库')
    parser.add_argument(
        '--file',
        type=str,
        help='要更新的文件名（支持多个，用逗号分隔），如: "知识.docx" 或 "知识.docx,员工手册.pdf"'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("更新文档到 Qdrant 向量数据库")
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
    
    # 文档目录
    documents_dir = project_root / "documents"
    documents_dir.mkdir(exist_ok=True)
    print(f"\n📁 文档目录: {documents_dir}")
    
    # 确定要更新的文件
    file_filter = None
    if args.file:
        file_filter = [f.strip() for f in args.file.split(',')]
        print(f"\n🎯 更新指定文档: {', '.join(file_filter)}")
    
    # 扫描文档
    print("\n🔍 扫描文档...")
    documents = scan_documents(documents_dir, file_filter)
    
    if not documents:
        print(f"\n⚠️  未找到任何文档文件")
        if file_filter:
            print(f"请检查文件名是否正确: {', '.join(file_filter)}")
        print(f"文档目录: {documents_dir}")
        sys.exit(0)
    
    print(f"✓ 找到 {len(documents)} 个文档文件")
    for doc in documents:
        print(f"  - {doc.name}")
    
    # 确认操作
    if not args.file:
        print("\n⚠️  警告：将更新所有文档！")
        response = input("确认继续？(yes/no): ")
        if response.lower() != 'yes':
            print("已取消操作")
            sys.exit(0)
    
    # 初始化解析器
    parser = DocumentParser()
    
    # 统计信息
    total_files = len(documents)
    success_files = 0
    failed_files = 0
    
    # 处理每个文档
    print("\n" + "=" * 60)
    print("开始更新...")
    print("=" * 60)
    
    for idx, file_path in enumerate(documents, 1):
        print(f"\n[{idx}/{total_files}] {file_path.name}")
        
        success = update_document(file_path, parser, documents_dir)
        
        if success:
            success_files += 1
        else:
            failed_files += 1
    
    # 输出统计信息
    print("\n" + "=" * 60)
    print("更新完成！")
    print("=" * 60)
    print(f"总文件数: {total_files}")
    print(f"成功更新: {success_files}")
    print(f"失败文件: {failed_files}")
    print("=" * 60)
    
    if success_files > 0:
        print("\n✅ 更新成功！知识库已更新最新内容。")
    else:
        print("\n❌ 没有成功更新任何文档，请检查错误日志。")
        sys.exit(1)


if __name__ == "__main__":
    main()

