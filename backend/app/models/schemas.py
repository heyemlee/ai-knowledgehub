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
    account: str = Field(..., min_length=1, max_length=255)  # 改为 account，支持任意账号
    password: str = Field(..., min_length=1, max_length=128)
    
    @field_validator('account')
    @classmethod
    def validate_account(cls, v):
        """验证并清理账号"""
        if not v or len(v.strip()) == 0:
            raise ValueError("账号不能为空")
        return v.strip().lower()  # 统一转换为小写
    
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
    account: str = Field(..., min_length=1, max_length=255)  # 账号：可以是名字或数字
    password: str = Field(..., min_length=6, max_length=128)  # 密码最少6位
    registration_code: str = Field(..., min_length=1, max_length=100)  # 新增：注册码
    
    @field_validator('account')
    @classmethod
    def validate_account(cls, v):
        """验证并清理账号"""
        if not v or len(v.strip()) == 0:
            raise ValueError("账号不能为空")
        return v.strip().lower()  # 统一转换为小写
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """验证密码"""
        if not v or len(v.strip()) == 0:
            raise ValueError("密码不能为空")
        if len(v) < 6:
            raise ValueError("密码长度至少6个字符")
        if len(v) > 128:
            raise ValueError("密码长度不能超过128字符")
        return v
    
    @field_validator('registration_code')
    @classmethod
    def validate_registration_code(cls, v):
        """验证注册码"""
        if not v or len(v.strip()) == 0:
            raise ValueError("注册码不能为空")
        return v.strip()


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    role: str = "user"
    token_quota: int = 800000  # Token 配额
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


class DocumentReference(BaseModel):
    """文档引用响应 - 用于智能文档检索"""
    file_id: str
    filename: str
    title: Optional[str] = None
    summary: Optional[str] = None
    preview_url: str
    download_url: str
    relevance_score: Optional[float] = None


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


class BatchUploadResult(BaseModel):
    """单张图片批量上传结果"""
    filename: str
    success: bool
    error: Optional[str] = None
    image_id: Optional[int] = None


class BatchUploadResponse(BaseModel):
    """批量上传响应"""
    total: int                         # 总图片数
    success_count: int                 # 成功数
    failed_count: int                  # 失败数
    results: List[BatchUploadResult]   # 详细结果


class ChatResponseWithImages(BaseModel):
    """问答响应（包含图片）"""
    answer: str
    sources: List[dict] = []
    images: List[ImageResponse] = []  # 新增：相关图片列表
    conversation_id: str
    tokens_used: Optional[int] = None


# ==============================
# 注册码相关 Schemas
# ==============================

class RegistrationCodeCreate(BaseModel):
    """创建注册码请求 - Token 计量"""
    code: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    token_quota: Optional[int] = Field(None, ge=1)  # Token 配额，None 表示无限制
    tokens_per_registration: int = Field(800000, ge=1)  # 每次注册分配的 tokens，默认 800000 (月度配额)
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        """验证注册码"""
        if not v or len(v.strip()) == 0:
            raise ValueError("注册码不能为空")
        return v.strip()


class RegistrationCodeUpdate(BaseModel):
    """更新注册码请求"""
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    token_quota: Optional[int] = Field(None, ge=1)


class RegistrationCodeResponse(BaseModel):
    """注册码响应 - Token 计量"""
    id: int
    code: str
    description: Optional[str] = None
    is_active: bool
    token_quota: Optional[int] = None  # Token 配额
    tokens_used: int  # 已使用的 tokens
    tokens_per_registration: int  # 每次注册消耗的 tokens
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==============================
# 管理员用户管理相关 Schemas
# ==============================

class AdminUserDetailResponse(BaseModel):
    """管理员查看用户详情响应（包含 Token 使用情况）"""
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    role: str = "user"
    token_quota: int = 800000  # Token 配额
    tokens_used: int = 0  # 已使用的 tokens
    tokens_remaining: int = 800000  # 剩余 tokens
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserQuotaUpdate(BaseModel):
    """更新用户 Token 配额请求"""
    token_quota: int = Field(..., ge=0, description="新的 Token 配额")
