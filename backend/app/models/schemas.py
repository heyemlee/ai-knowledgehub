"""
Pydantic 数据模型
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class Token(BaseModel):
    """JWT Token 响应"""
    access_token: str
    token_type: str = "bearer"


class UserLogin(BaseModel):
    """用户登录请求"""
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    """用户创建请求"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str  # user | assistant
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """问答请求"""
    question: str
    conversation_id: Optional[str] = None
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7


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

