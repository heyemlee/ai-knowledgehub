"""
AI 文档分析服务
自动从文档内容中提取标题、摘要、关键词
用于智能文档检索功能
"""
from openai import OpenAI
from app.core.config import settings
from typing import Dict, Optional
import logging
import json
import re

logger = logging.getLogger(__name__)


class DocumentAnalysisService:
    """AI 文档分析服务"""
    
    def __init__(self):
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self.client = None
            logger.warning("OpenAI API key not configured, document analysis will be disabled")
    
    def analyze_document(
        self,
        filename: str,
        content_preview: str,
        max_content_length: int = 3000
    ) -> Dict:
        """
        分析文档并提取元数据
        
        Args:
            filename: 文件名
            content_preview: 文档内容预览（前N个字符）
            max_content_length: 最大内容长度
            
        Returns:
            包含 title, summary, keywords, category 的字典
        """
        if not self.client:
            # 如果没有配置 OpenAI，使用文件名作为基本信息
            return self._fallback_analysis(filename)
        
        try:
            # 截取内容预览
            content = content_preview[:max_content_length] if content_preview else ""
            
            # 构建提示词
            prompt = f"""分析以下文档，提取关键信息用于智能检索。

文件名: {filename}

文档内容预览:
{content}

请返回 JSON 格式（不要包含 markdown 代码块标记）:
{{
    "title": "文档的主要标题或主题（基于文件名和内容判断，使用与文件名相同的语言）",
    "summary": "一句话描述文档的主要内容（不超过100字）",
    "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
    "category": "文档类型（如：price_list/catalog/manual/policy/report/other）"
}}

注意：
1. keywords 应包含中英文关键词，便于双语检索
2. 从文件名和内容中提取最重要的实体词和概念词
3. 如果是价格表，keywords 应包含"价格"、"price"、产品名称等
4. title 应该简洁明了，能够代表文档的主要内容"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一个文档分析专家。只返回 JSON 格式的结果，不要包含任何其他文字或 markdown 标记。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 清理可能的 markdown 代码块标记
            result_text = self._clean_json_response(result_text)
            
            # 解析 JSON
            result = json.loads(result_text)
            
            # 确保所有必需字段存在
            result = self._validate_result(result, filename)
            
            logger.info(f"文档分析成功: {filename} -> title: {result.get('title')}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"解析 AI 响应失败: {e}, 响应内容: {result_text[:200]}")
            return self._fallback_analysis(filename)
        except Exception as e:
            logger.error(f"文档分析失败: {e}")
            return self._fallback_analysis(filename)
    
    def _clean_json_response(self, text: str) -> str:
        """清理 JSON 响应中的 markdown 标记"""
        # 移除 ```json 和 ``` 标记
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return text.strip()
    
    def _validate_result(self, result: Dict, filename: str) -> Dict:
        """验证并补充缺失的字段"""
        if not result.get("title"):
            result["title"] = self._extract_title_from_filename(filename)
        
        if not result.get("summary"):
            result["summary"] = f"文档: {result['title']}"
        
        if not result.get("keywords"):
            # 从文件名提取基本关键词
            result["keywords"] = self._extract_keywords_from_filename(filename)
        
        if not result.get("category"):
            result["category"] = "other"
        
        return result
    
    def _fallback_analysis(self, filename: str) -> Dict:
        """降级方案：从文件名提取基本信息"""
        title = self._extract_title_from_filename(filename)
        keywords = self._extract_keywords_from_filename(filename)
        
        return {
            "title": title,
            "summary": f"文档: {title}",
            "keywords": keywords,
            "category": self._guess_category_from_filename(filename)
        }
    
    def _extract_title_from_filename(self, filename: str) -> str:
        """从文件名提取标题"""
        # 移除文件扩展名
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        # 清理常见的无意义字符
        name = re.sub(r'[-_]+', ' ', name)
        return name.strip()
    
    def _extract_keywords_from_filename(self, filename: str) -> list:
        """从文件名提取关键词"""
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        # 分割单词
        words = re.findall(r'[A-Za-z]+|[\u4e00-\u9fa5]+', name)
        # 过滤太短的词
        keywords = [w.lower() for w in words if len(w) >= 2]
        return keywords[:10]  # 最多返回10个
    
    def _guess_category_from_filename(self, filename: str) -> str:
        """从文件名猜测文档类型"""
        name_lower = filename.lower()
        
        if 'price' in name_lower or '价格' in name_lower:
            return 'price_list'
        elif 'catalog' in name_lower or '目录' in name_lower:
            return 'catalog'
        elif 'manual' in name_lower or '手册' in name_lower:
            return 'manual'
        elif 'policy' in name_lower or '政策' in name_lower:
            return 'policy'
        elif 'report' in name_lower or '报告' in name_lower:
            return 'report'
        else:
            return 'other'


# 全局实例
document_analysis_service = DocumentAnalysisService()
