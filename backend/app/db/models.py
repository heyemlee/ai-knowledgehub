"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from datetime import datetime


# 图片-标签关联表（多对多）
image_tag_association = Table(
    'image_tag_associations',
    Base.metadata,
    Column('image_id', Integer, ForeignKey('images.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('image_tags.id', ondelete='CASCADE'), primary_key=True)
)


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(String(20), default="user", nullable=False)  # user | admin
    token_quota = Column(Integer, default=800000, nullable=False)  # 用户的 Token 配额，默认 80万
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="owner", cascade="all, delete-orphan")



class Document(Base):
    """文档模型"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String(255), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="completed", nullable=False)
    chunks_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    owner = relationship("User", back_populates="documents")


class Conversation(Base):
    """对话模型"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    owner = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    """消息模型"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    conversation = relationship("Conversation", back_populates="messages")


class TokenUsage(Base):
    """Token 使用量记录模型"""
    __tablename__ = "token_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    usage_date = Column(DateTime(timezone=True), nullable=False, index=True)  # 使用日期（用于按日统计）
    prompt_tokens = Column(Integer, default=0, nullable=False)  # 输入 token 数
    completion_tokens = Column(Integer, default=0, nullable=False)  # 输出 token 数
    total_tokens = Column(Integer, default=0, nullable=False)  # 总 token 数
    endpoint = Column(String(100), nullable=True)  # 使用的端点（如 chat/ask, chat/stream）
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 关系（可选，用于级联删除）
    user = relationship("User", backref="token_usage_records")


class ImageTag(Base):
    """图片标签模型"""
    __tablename__ = "image_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 多对多关系
    images = relationship("Image", secondary=image_tag_association, back_populates="tags")


class Image(Base):
    """图片模型"""
    __tablename__ = "images"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(String(255), unique=True, index=True, nullable=False)  # 唯一文件标识
    filename = Column(String(255), nullable=False)  # 存储文件名
    original_filename = Column(String(255), nullable=False)  # 原始文件名
    file_size = Column(Integer, nullable=False)  # 文件大小（字节）
    mime_type = Column(String(100), nullable=False)  # MIME 类型（image/jpeg, image/png 等）
    storage_path = Column(String(500), nullable=False)  # 存储路径
    thumbnail_path = Column(String(500), nullable=True)  # 缩略图路径（可选）
    description = Column(Text, nullable=True)  # 图片描述（用于检索）
    alt_text = Column(String(500), nullable=True)  # 替代文本（用于无障碍和检索）
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 关系
    owner = relationship("User", backref="images")
    tags = relationship("ImageTag", secondary=image_tag_association, back_populates="images")


class RegistrationCode(Base):
    """注册码模型 - 基于 Token 计量"""
    __tablename__ = "registration_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)  # 注册码
    description = Column(String(500), nullable=True)  # 描述（可选）
    is_active = Column(Boolean, default=True, nullable=False)  # 是否启用
    token_quota = Column(Integer, nullable=True)  # Token 配额（None 表示无限制）
    tokens_used = Column(Integer, default=0, nullable=False)  # 已使用的 tokens
    tokens_per_registration = Column(Integer, default=800000, nullable=False)  # 每次注册分配的 tokens (月度配额: 400问题 × 2000 tokens)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # 创建者
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 关系
    creator = relationship("User", backref="registration_codes")

