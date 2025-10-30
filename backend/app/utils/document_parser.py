"""
文档解析工具
支持 PDF、Word、Excel 等格式
"""
import logging
from typing import List
from io import BytesIO
import PyPDF2
from docx import Document
import openpyxl

logger = logging.getLogger(__name__)


class DocumentParser:
    """文档解析器"""
    
    @staticmethod
    def parse_pdf(file_content: bytes) -> List[str]:
        """
        解析 PDF 文件
        
        Args:
            file_content: PDF 文件内容（字节）
            
        Returns:
            文本块列表
        """
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            texts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text.strip():
                    texts.append(text)
            
            return texts
        except Exception as e:
            logger.error(f"PDF 解析失败: {e}")
            raise
    
    @staticmethod
    def parse_docx(file_content: bytes) -> List[str]:
        """
        解析 Word 文档
        
        Args:
            file_content: DOCX 文件内容（字节）
            
        Returns:
            文本块列表
        """
        try:
            doc_file = BytesIO(file_content)
            doc = Document(doc_file)
            
            texts = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    texts.append(paragraph.text)
            
            return texts
        except Exception as e:
            logger.error(f"DOCX 解析失败: {e}")
            raise
    
    @staticmethod
    def parse_excel(file_content: bytes) -> List[str]:
        """
        解析 Excel 文件
        
        Args:
            file_content: Excel 文件内容（字节）
            
        Returns:
            文本块列表
        """
        try:
            excel_file = BytesIO(file_content)
            workbook = openpyxl.load_workbook(excel_file)
            
            texts = []
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                sheet_text = []
                for row in sheet.iter_rows(values_only=True):
                    row_text = " | ".join([str(cell) if cell else "" for cell in row])
                    if row_text.strip():
                        sheet_text.append(row_text)
                if sheet_text:
                    texts.append(f"工作表: {sheet_name}\n" + "\n".join(sheet_text))
            
            return texts
        except Exception as e:
            logger.error(f"Excel 解析失败: {e}")
            raise
    
    @staticmethod
    def chunk_text(texts: List[str], chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        将文本切分成块
        
        Args:
            texts: 文本列表
            chunk_size: 每块大小（字符数）
            overlap: 重叠字符数
            
        Returns:
            文本块列表
        """
        chunks = []
        full_text = "\n\n".join(texts)
        
        start = 0
        while start < len(full_text):
            end = start + chunk_size
            chunk = full_text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        return chunks

