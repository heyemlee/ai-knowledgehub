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
from app.core.constants import DocumentParserConfig

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
        解析 Word 文档（支持中文）
        
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
                para_text = paragraph.text.strip()
                if para_text:
                    texts.append(para_text)
            
            for table in doc.tables:
                table_texts = []
                for row in table.rows:
                    row_texts = []
                    for cell in row.cells:
                        cell_text = cell.text.strip()
                        if cell_text:
                            row_texts.append(cell_text)
                    if row_texts:
                        table_texts.append(" | ".join(row_texts))
                
                if table_texts:
                    texts.append("表格内容:\n" + "\n".join(table_texts))
            
            if not texts:
                logger.warning("Word 文档解析后为空，可能文档格式特殊或内容为空")
                texts.append("")
            
            logger.info(f"成功解析 Word 文档，提取了 {len(texts)} 个文本片段")
            return texts
        except Exception as e:
            logger.error(f"DOCX 解析失败: {e}", exc_info=True)
            raise
    
    @staticmethod
    def parse_text(file_content: bytes) -> List[str]:
        """
        解析纯文本文件
        
        Args:
            file_content: TXT 文件内容（字节）
            
        Returns:
            文本块列表
        """
        try:
            text = file_content.decode('utf-8')
            if not text.strip():
                logger.warning("TXT 文件内容为空")
                return [""]
            
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return lines if lines else [text]
        except UnicodeDecodeError:
            try:
                text = file_content.decode('gbk')
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                return lines if lines else [text]
            except Exception as e:
                logger.error(f"TXT 文件解析失败: {e}")
                raise ValueError(f"无法解析文本文件，编码不支持: {e}")
        except Exception as e:
            logger.error(f"TXT 解析失败: {e}")
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
    def chunk_text(
        texts: List[str], 
        chunk_size: int = DocumentParserConfig.DEFAULT_CHUNK_SIZE, 
        overlap: int = DocumentParserConfig.DEFAULT_OVERLAP
    ) -> List[str]:
        """
        将文本切分成块（支持中文，优化结构化信息保留）
        
        Args:
            texts: 文本列表
            chunk_size: 每块大小（字符数，中文按字符计算）
            overlap: 重叠字符数
            
        Returns:
            文本块列表
        """
        if not texts:
            return []
        
        chunks = []
        full_text = "\n\n".join(texts)
        
        start = 0
        text_length = len(full_text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk = full_text[start:end]
            
            if end < text_length:
                best_split = len(chunk)
                
                last_newline = chunk.rfind('\n')
                if last_newline > len(chunk) * DocumentParserConfig.NEWLINE_THRESHOLD:
                    best_split = last_newline + 1
                
                if best_split == len(chunk):
                    for punct in DocumentParserConfig.STRUCTURED_SEPARATORS:
                        punct_pos = chunk.rfind(punct)
                        if punct_pos > len(chunk) * DocumentParserConfig.PUNCTUATION_THRESHOLD:
                            best_split = punct_pos + 1
                            break
                
                if best_split == len(chunk):
                    for punct in DocumentParserConfig.SENTENCE_SEPARATORS:
                        punct_pos = chunk.rfind(punct)
                        if punct_pos > len(chunk) * DocumentParserConfig.SENTENCE_PUNCTUATION_THRESHOLD:
                            best_split = punct_pos + 1
                            break
                
                if best_split < len(chunk) and best_split > len(chunk) * DocumentParserConfig.MIN_SPLIT_RATIO:
                    chunk = chunk[:best_split]
                    end = start + len(chunk)
            
            if chunk.strip():
                chunks.append(chunk)
            
            if end >= text_length:
                break
            
            next_start = end - overlap
            if next_start <= start:
                next_start = start + 1
            
            start = next_start
        
        logger.info(f"文本切分完成: 原始文本长度 {text_length} 字符，切分成 {len(chunks)} 个块")
        return chunks

