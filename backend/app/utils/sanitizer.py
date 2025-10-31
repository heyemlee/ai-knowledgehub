"""
输入验证和清理工具
防止注入攻击、XSS攻击等安全问题
"""
import re
import html
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class InputSanitizer:
    """输入清理和验证工具"""
    
    # 最大输入长度限制
    MAX_QUESTION_LENGTH = 10000  # 问题最大长度
    MAX_FILENAME_LENGTH = 255  # 文件名最大长度
    MAX_FULL_NAME_LENGTH = 100  # 全名最大长度
    MAX_CONVERSATION_ID_LENGTH = 100  # 对话ID最大长度
    
    # 允许的字符模式
    FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._\-\s\u4e00-\u9fff]+$')  # 允许中文、英文、数字、点、下划线、横线、空格
    CONVERSATION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9\-]+$')  # UUID格式或类似格式
    
    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None, strip_html: bool = True) -> str:
        """
        清理文本输入
        
        Args:
            text: 待清理的文本
            max_length: 最大长度限制
            strip_html: 是否移除HTML标签
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 移除HTML标签和实体编码
        if strip_html:
            text = html.escape(text)
        
        # 移除控制字符（保留换行符和制表符）
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # 限制长度
        if max_length:
            text = text[:max_length]
        
        return text.strip()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        清理文件名
        
        Args:
            filename: 文件名
            
        Returns:
            清理后的文件名
            
        Raises:
            ValueError: 如果文件名不符合要求
        """
        if not filename:
            raise ValueError("文件名不能为空")
        
        # 移除路径分隔符（防止路径遍历攻击）
        filename = filename.replace('/', '').replace('\\', '').replace('..', '')
        
        # 清理文件名
        filename = InputSanitizer.sanitize_text(filename, max_length=InputSanitizer.MAX_FILENAME_LENGTH)
        
        # 验证文件名格式
        if not InputSanitizer.FILENAME_PATTERN.match(filename):
            raise ValueError("文件名包含非法字符")
        
        # 移除首尾空格和点
        filename = filename.strip('. ')
        
        if not filename:
            raise ValueError("文件名无效")
        
        return filename
    
    @staticmethod
    def sanitize_question(question: str) -> str:
        """
        清理用户问题
        
        Args:
            question: 用户问题
            
        Returns:
            清理后的问题
            
        Raises:
            ValueError: 如果问题不符合要求
        """
        if not question:
            raise ValueError("问题不能为空")
        
        question = question.strip()
        
        if len(question) == 0:
            raise ValueError("问题不能为空")
        
        if len(question) > InputSanitizer.MAX_QUESTION_LENGTH:
            raise ValueError(f"问题长度超过限制（最大 {InputSanitizer.MAX_QUESTION_LENGTH} 字符）")
        
        # 清理文本（保留换行符）
        question = InputSanitizer.sanitize_text(
            question, 
            max_length=InputSanitizer.MAX_QUESTION_LENGTH,
            strip_html=True
        )
        
        return question
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """
        清理邮箱地址
        
        Args:
            email: 邮箱地址
            
        Returns:
            清理后的邮箱
        """
        if not email:
            return ""
        
        # 移除空格和特殊字符
        email = email.strip().lower()
        
        # 移除HTML标签
        email = html.escape(email)
        
        return email
    
    @staticmethod
    def sanitize_full_name(full_name: Optional[str]) -> Optional[str]:
        """
        清理用户全名
        
        Args:
            full_name: 用户全名
            
        Returns:
            清理后的全名
        """
        if not full_name:
            return None
        
        full_name = InputSanitizer.sanitize_text(
            full_name,
            max_length=InputSanitizer.MAX_FULL_NAME_LENGTH,
            strip_html=True
        )
        
        return full_name if full_name else None
    
    @staticmethod
    def sanitize_conversation_id(conversation_id: Optional[str]) -> Optional[str]:
        """
        清理对话ID
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            清理后的对话ID
        """
        if not conversation_id:
            return None
        
        # 验证格式（UUID格式）
        if not InputSanitizer.CONVERSATION_ID_PATTERN.match(conversation_id):
            raise ValueError("对话ID格式无效")
        
        if len(conversation_id) > InputSanitizer.MAX_CONVERSATION_ID_LENGTH:
            raise ValueError(f"对话ID长度超过限制（最大 {InputSanitizer.MAX_CONVERSATION_ID_LENGTH} 字符）")
        
        return conversation_id
    
    @staticmethod
    def validate_sql_injection_safe(text: str) -> bool:
        """
        检查文本是否包含SQL注入风险
        
        Args:
            text: 待检查的文本
            
        Returns:
            如果安全返回True，否则返回False
        """
        if not text:
            return True
        
        # SQL注入常见模式
        sql_patterns = [
            r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)',
            r'(\b(or|and)\s+\d+\s*=\s*\d+)',
            r'(\'\s*(or|and)\s+\')',
            r'(\-\-|\#|\/\*|\*\/)',
            r'(\bor\b\s+\d+\s*=\s*\d+)',
        ]
        
        text_lower = text.lower()
        for pattern in sql_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"检测到潜在的SQL注入尝试: {text[:100]}")
                return False
        
        return True
    
    @staticmethod
    def validate_xss_safe(text: str) -> bool:
        """
        检查文本是否包含XSS风险
        
        Args:
            text: 待检查的文本
            
        Returns:
            如果安全返回True，否则返回False
        """
        if not text:
            return True
        
        # XSS常见模式
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'<iframe[^>]*>.*?</iframe>',
            r'javascript:',
            r'on\w+\s*=',
            r'<img[^>]*src[^>]*javascript:',
            r'<svg[^>]*onload',
        ]
        
        text_lower = text.lower()
        for pattern in xss_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"检测到潜在的XSS尝试: {text[:100]}")
                return False
        
        return True

