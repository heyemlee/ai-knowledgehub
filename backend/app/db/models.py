"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from datetime import datetime


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
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

