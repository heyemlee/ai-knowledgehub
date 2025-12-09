"""
Pydantic 数据模型
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.utils.sanitizer import InputSanitizer


class Token(BaseModel):
    """JWT Token 响应"""
    access_token: str
    token_type: str = "bearer"


class UserLogin(BaseModel):
    """用户登录请求"""
    email: EmailStr = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """验证并清理邮箱"""
        return InputSanitizer.sanitize_email(v)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """验证密码"""
        if not v or len(v.strip()) == 0:
            raise ValueError("密码不能为空")
        if len(v) > 128:
            raise ValueError("密码长度不能超过128字符")
        return v


class UserCreate(BaseModel):
    """用户创建请求"""
    email: EmailStr = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """验证并清理邮箱"""
        return InputSanitizer.sanitize_email(v)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """验证密码强度"""
        if not v or len(v.strip()) == 0:
            raise ValueError("密码不能为空")
        if len(v) < 8:
            raise ValueError("密码长度至少8个字符")
        if len(v) > 128:
            raise ValueError("密码长度不能超过128字符")
        # 检查是否包含数字和字母
        if not any(c.isdigit() for c in v) or not any(c.isalpha() for c in v):
            raise ValueError("密码必须包含至少一个数字和一个字母")
        return v
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        """验证并清理全名"""
        if v is None:
            return None
        return InputSanitizer.sanitize_full_name(v)


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    role: str = "user"
    created_at: Optional[datetime] = None  # 允许为 None，简化开发

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str  # user | assistant
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., min_length=1, max_length=10000)
    conversation_id: Optional[str] = Field(None, max_length=100)
    max_tokens: Optional[int] = Field(1000, ge=1, le=100000)
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    locale: Optional[str] = Field('zh-CN', max_length=10)  # 用户语言（zh-CN 或 en-US）
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        """验证并清理问题"""
        if not v or len(v.strip()) == 0:
            raise ValueError("问题不能为空")
        # 清理问题文本
        cleaned = InputSanitizer.sanitize_question(v)
        # 检查XSS风险（保留XSS检测，因为返回内容会在前端显示）
        # 注：不检查SQL注入，因为系统使用ORM不会直接拼接SQL，且用户问题不用于SQL查询
        if not InputSanitizer.validate_xss_safe(cleaned):
            raise ValueError("问题包含非法字符")
        return cleaned
    
    @field_validator('conversation_id')
    @classmethod
    def validate_conversation_id(cls, v):
        """验证对话ID"""
        if v is None:
            return None
        return InputSanitizer.sanitize_conversation_id(v)


class ChatResponse(BaseModel):
    """问答响应"""
    answer: str
    sources: List[dict] = []
    conversation_id: str
    tokens_used: Optional[int] = None


class DocumentUpload(BaseModel):
    """文档上传响应"""
    file_id: str
    filename: str
    file_size: int
    upload_time: datetime
    status: str  # processing | completed | failed


class DocumentMetadata(BaseModel):
    """文档元数据"""
    file_id: str
    filename: str
    file_type: str
    file_size: int
    upload_time: datetime
    chunks_count: int
    status: str
    user_id: Optional[int] = None  # 管理员可见


class ConversationResponse(BaseModel):
    """对话响应"""
    id: int
    conversation_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    role: str
    content: str
    sources: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==============================
# 图片相关 Schemas
# ==============================

class ImageTagCreate(BaseModel):
    """创建图片标签请求"""
    name: str = Field(..., min_length=1, max_length=100)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """验证并清理标签名"""
        if not v or len(v.strip()) == 0:
            raise ValueError("标签名不能为空")
        return v.strip()


class ImageTagResponse(BaseModel):
    """图片标签响应"""
    id: int
    name: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ImageUploadResponse(BaseModel):
    """图片上传响应"""
    file_id: str
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    storage_path: str
    thumbnail_path: Optional[str] = None
    upload_time: datetime


class ImageUpdate(BaseModel):
    """图片更新请求"""
    description: Optional[str] = Field(None, max_length=2000)
    alt_text: Optional[str] = Field(None, max_length=500)
    tag_ids: Optional[List[int]] = None
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """验证描述"""
        if v is None:
            return None
        return v.strip()
    
    @field_validator('alt_text')
    @classmethod
    def validate_alt_text(cls, v):
        """验证替代文本"""
        if v is None:
            return None
        return v.strip()


class ImageResponse(BaseModel):
    """图片详情响应"""
    id: int
    file_id: str
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    storage_path: str
    thumbnail_path: Optional[str] = None
    description: Optional[str] = None
    alt_text: Optional[str] = None
    user_id: int
    tags: List[ImageTagResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ImageListResponse(BaseModel):
    """图片列表响应"""
    images: List[ImageResponse]
    total: int
    page: int
    page_size: int


class ChatResponseWithImages(BaseModel):
    """问答响应（包含图片）"""
    answer: str
    sources: List[dict] = []
    images: List[ImageResponse] = []  # 新增：相关图片列表
    conversation_id: str
    tokens_used: Optional[int] = None

