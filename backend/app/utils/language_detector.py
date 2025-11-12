"""
语言检测工具
检测用户问题的语言（中文/英文），用于控制AI回答的语言
"""
import logging
from typing import Literal

logger = logging.getLogger(__name__)


def detect_language(text: str) -> Literal['zh', 'en']:
    """
    检测文本的主要语言
    
    Args:
        text: 待检测的文本
        
    Returns:
        'zh' 表示中文，'en' 表示英文
    """
    if not text or not text.strip():
        return 'en'  # 默认为英文
    
    # 移除空白字符进行统计
    text = text.strip()
    
    # 统计中文字符数量（使用 Unicode 范围直接检查）
    chinese_chars = 0
    chinese_punctuation = 0
    english_chars = 0
    
    for char in text:
        code_point = ord(char)
        # 检查是否是中文字符（CJK统一汉字）
        if 0x4E00 <= code_point <= 0x9FFF:  # CJK Unified Ideographs
            chinese_chars += 1
        # 检查是否是中文标点符号
        elif code_point in [0x3000, 0x3001, 0x3002, 0xFF01, 0xFF0C, 0xFF0E, 0xFF1A, 0xFF1B, 0xFF1F, 
                            0x300A, 0x300B, 0x300C, 0x300D, 0x300E, 0x300F, 0x3010, 0x3011,
                            0x201C, 0x201D, 0x2018, 0x2019, 0xFF08, 0xFF09, 0x3014, 0x3015]:
            chinese_punctuation += 1
        # 检查是否是英文字母或数字
        elif char.isalnum() and char.isascii():
            english_chars += 1
    
    # 总字符数（排除空格和标点）
    total_chars = chinese_chars + english_chars
    
    if total_chars == 0:
        return 'en'  # 默认为英文
    
    # 如果中文字符（包括中文标点）占比超过30%，判断为中文
    text_no_space = text.replace(' ', '')
    if len(text_no_space) == 0:
        return 'en'
    
    chinese_ratio = (chinese_chars + chinese_punctuation) / len(text_no_space)
    
    if chinese_ratio > 0.3:
        return 'zh'
    else:
        return 'en'


def is_chinese(text: str) -> bool:
    """
    判断文本是否为中文
    
    Args:
        text: 待检测的文本
        
    Returns:
        True 表示中文，False 表示英文
    """
    return detect_language(text) == 'zh'

