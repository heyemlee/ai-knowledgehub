# 项目架构文档

本文档详细说明 ABC AI Knowledge Hub 项目的代码组织架构。

## 📋 目录结构总览

```
abc-ai-knowledgehub/
├── backend/                          # 后端服务
│   ├── app/                          # 应用主目录
│   │   ├── main.py                   # FastAPI 应用入口
│   │   ├── api/                      # API 路由层
│   │   ├── core/                     # 核心配置
│   │   ├── db/                       # 数据库层
│   │   ├── models/                   # 数据模型
│   │   ├── services/                 # 业务逻辑层
│   │   ├── utils/                    # 工具函数
│   │   └── middleware/               # 中间件
│   ├── requirements.txt              # Python 依赖
│   └── Dockerfile                    # Docker 配置
├── frontend/                         # 前端应用
│   ├── app/                          # Next.js App Router
│   ├── components/                   # React 组件
│   ├── lib/                          # 工具库
│   └── store/                        # 状态管理
├── documents/                        # 文档目录（git忽略）
├── scripts/                          # 工具脚本
└── .gitignore                        # Git 忽略规则
```

---

## 🏗️ 后端架构

### 1. 应用入口 (`app/main.py`)

**职责**: FastAPI 应用初始化、中间件配置、路由注册

**主要功能**:
- 创建 FastAPI 应用实例
- 配置 CORS、信任主机中间件
- 注册所有 API 路由
- 配置应用生命周期（数据库连接）
- 集成监控和限流中间件

**关键代码**:
```python
app = FastAPI(title="ABC AI Knowledge Hub API", ...)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["问答"])
# ... 其他路由
```

---

### 2. API 路由层 (`app/api/`)

**架构模式**: RESTful API，按功能模块划分

#### 2.1 认证模块 (`auth.py`)

**路径**: `/api/v1/auth`

**功能**:
- `POST /login` - 用户登录，返回 JWT Token
- `POST /register` - 用户注册（仅开发环境）
- `GET /me` - 获取当前用户信息

**依赖**:
- `User` 模型（数据库）
- `create_access_token`（JWT工具）
- `get_password_hash`（密码加密）

#### 2.2 问答模块 (`chat.py`)

**路径**: `/api/v1/chat`

**功能**:
- `POST /stream` - 流式问答接口（RAG + AI生成）

**工作流程**:
1. 接收用户问题
2. 生成问题向量嵌入
3. 在 Qdrant 中检索相似文档片段
4. 构建上下文提示词
5. 调用 OpenAI API 生成回答（流式）
6. 保存对话记录到数据库
7. 记录 Token 使用量

**依赖**:
- `OpenAIService` - AI 服务
- `QdrantService` - 向量检索
- `TokenUsageService` - Token 统计

#### 2.3 文档管理模块 (`documents.py`)

**路径**: `/api/v1/documents`

**功能**:
- `POST /upload` - 上传文档
- `GET /list` - 获取文档列表
- `GET /{file_id}/preview` - 预览文档
- `GET /{file_id}/download` - 下载文档
- `DELETE /{file_id}` - 删除文档

**工作流程（上传）**:
1. 验证文件类型和大小
2. 上传文件到 S3
3. 解析文档内容
4. 切分文本块
5. 生成向量嵌入
6. 存储到 Qdrant
7. 保存元数据到数据库

**依赖**:
- `S3Service` - 文件存储
- `DocumentParser` - 文档解析
- `OpenAIService` - 向量生成
- `QdrantService` - 向量存储

#### 2.4 对话管理模块 (`conversations.py`)

**路径**: `/api/v1/conversations`

**功能**:
- `GET /` - 获取对话列表
- `GET /{conversation_id}/messages` - 获取对话消息
- `DELETE /{conversation_id}` - 删除对话

#### 2.5 Token 使用统计 (`token_usage.py`)

**路径**: `/api/v1/token-usage`

**功能**:
- `GET /stats` - 获取 Token 使用统计

#### 2.6 API Key 管理 (`api_keys.py`)

**路径**: `/api/v1/api-keys`

**功能**:
- `POST /encrypt` - 加密 API Key
- `POST /decrypt` - 解密 API Key
- `POST /rotate` - 轮换 API Key
- `GET /rotation-status/{key_name}` - 获取轮换状态

---

### 3. 核心配置 (`app/core/`)

#### 3.1 配置管理 (`config.py`)

**职责**: 统一管理环境变量和配置

**主要配置项**:
- `MODE` - 运行模式（development/production）
- `OPENAI_API_KEY` - OpenAI API 密钥
- `QDRANT_URL` / `QDRANT_API_KEY` - Qdrant 配置
- `AWS_*` - AWS 服务配置
- `JWT_SECRET_KEY` - JWT 密钥
- `DATABASE_URL` - 数据库连接
- `REDIS_URL` - Redis 连接（可选）

**安全特性**:
- 生产环境强制验证敏感配置
- 禁止使用默认密钥

#### 3.2 常量定义 (`constants.py`)

**职责**: 定义系统常量

**包含**:
- `RateLimitConfig` - API 限流配置
- `TokenLimitConfig` - Token 限制配置
- `SearchConfig` - 检索配置
- `ProcessingConfig` - 处理配置
- `CacheConfig` - 缓存配置
- `AIConfig` - AI 模型配置

---

### 4. 数据库层 (`app/db/`)

#### 4.1 数据库连接 (`database.py`)

**职责**: 数据库连接管理

**功能**:
- `get_db()` - 获取数据库会话（依赖注入）
- `init_db()` - 初始化数据库（创建表）
- `close_db()` - 关闭数据库连接

**支持的数据库**:
- SQLite（开发环境）
- PostgreSQL（生产环境）

#### 4.2 数据模型 (`models.py`)

**职责**: SQLAlchemy ORM 模型定义

**主要模型**:
- `User` - 用户模型
  - `id`, `email`, `hashed_password`, `full_name`, `is_active`, `created_at`
- `Document` - 文档模型
  - `id`, `file_id`, `filename`, `file_type`, `file_size`, `user_id`, `created_at`
- `Conversation` - 对话模型
  - `id`, `conversation_id`, `user_id`, `title`, `created_at`, `updated_at`
- `Message` - 消息模型
  - `id`, `conversation_id`, `role`, `content`, `sources`, `created_at`
- `TokenUsage` - Token 使用模型
  - `id`, `user_id`, `date`, `tokens_used`, `created_at`

---

### 5. 业务逻辑层 (`app/services/`)

#### 5.1 OpenAI 服务 (`openai_service.py`)

**职责**: OpenAI API 封装

**主要方法**:
- `generate_embeddings()` - 生成文本向量嵌入（带缓存）
- `generate_completion()` - 生成文本完成
- `generate_completion_stream()` - 流式生成文本

**特性**:
- 自动重试机制
- 缓存支持（减少 API 调用）
- Token 使用量统计

#### 5.2 Qdrant 服务 (`qdrant_service.py`)

**职责**: Qdrant 向量数据库操作

**主要方法**:
- `upload_vectors()` - 上传向量数据
- `search_similar()` - 相似度检索
- `delete_document_vectors()` - 删除文档向量
- `get_collection_info()` - 获取集合信息

#### 5.3 S3 服务 (`s3_service.py`)

**职责**: AWS S3 文件存储操作

**主要方法**:
- `upload_file()` - 上传文件
- `download_file()` - 下载文件
- `delete_file()` - 删除文件

#### 5.4 缓存服务 (`cache_service.py`)

**职责**: 缓存管理（支持内存缓存和 Redis）

**功能**:
- 自动检测 Redis 是否可用
- 回退到内存缓存
- 统一的缓存接口

**缓存策略**:
- Embedding 缓存：24 小时
- 检索结果缓存：1 小时

#### 5.5 Token 使用统计服务 (`token_usage_service.py`)

**职责**: Token 使用量统计和管理

**功能**:
- 记录 Token 使用量
- 计算每日/每月使用量
- 检查使用限制

#### 5.6 API Key 管理服务 (`api_key_manager.py`)

**职责**: API Key 加密存储和轮换

**功能**:
- 使用 Fernet 对称加密
- 支持密钥轮换
- 记录轮换历史

#### 5.7 提示词管理 (`prompts.py`)

**职责**: 管理 AI 提示词模板

**主要提示词**:
- 问答系统提示词（中文）
- 上下文构建模板
- 支持多语言

---

### 6. 工具函数 (`app/utils/`)

#### 6.1 认证工具 (`auth.py`)

**功能**:
- `create_access_token()` - 创建 JWT Token
- `verify_token()` - 验证 JWT Token
- `get_current_user()` - 获取当前用户（依赖注入）

#### 6.2 文档解析器 (`document_parser.py`)

**功能**:
- 支持 PDF、Word、Excel 解析
- 中文内容提取
- 智能文本切分（按句子、段落）
- 表格内容提取

#### 6.3 文件验证 (`file_validator.py`)

**功能**:
- 验证文件类型
- 验证文件大小
- 检查文件扩展名

#### 6.4 输入清理 (`sanitizer.py`)

**功能**:
- SQL 注入防护
- XSS 防护
- 输入长度限制
- 格式验证

#### 6.5 语言检测 (`language_detector.py`)

**功能**:
- 检测文本语言
- 支持中文、英文等多语言

#### 6.6 重试机制 (`retry.py`)

**功能**:
- OpenAI API 调用重试
- 指数退避策略
- 错误处理

---

### 7. 中间件 (`app/middleware/`)

#### 7.1 限流中间件 (`rate_limit.py`)

**功能**:
- API 请求限流
- 基于 IP 或用户 ID
- 不同接口不同限流规则

#### 7.2 监控中间件 (`monitoring.py`)

**功能**:
- API 请求监控
- 响应时间统计
- 错误率统计
- 提供 `/api/v1/metrics` 端点

---

### 8. 数据模型 (`app/models/schemas.py`)

**职责**: Pydantic 数据模型（请求/响应验证）

**主要模型**:
- `UserLogin` - 登录请求
- `UserCreate` - 注册请求
- `UserResponse` - 用户响应
- `ChatRequest` - 聊天请求
- `ChatResponse` - 聊天响应
- `DocumentUpload` - 文档上传响应
- `ConversationResponse` - 对话响应
- `MessageResponse` - 消息响应
- `TokenUsageStats` - Token 统计响应

---

## 🎨 前端架构

### 1. 应用入口 (`app/`)

#### 1.1 根布局 (`layout.tsx`)

**职责**: 全局布局和样式

#### 1.2 主页面 (`page.tsx`)

**职责**: 根据认证状态显示登录或聊天界面

### 2. 组件 (`components/`)

#### 2.1 登录表单 (`LoginForm.tsx`)

**功能**: 用户登录界面

#### 2.2 聊天界面 (`ChatInterface.tsx`)

**功能**:
- 显示对话历史
- 发送消息
- 接收流式响应
- 显示来源文档

#### 2.3 对话历史 (`ConversationHistory.tsx`)

**功能**: 显示和管理对话列表

#### 2.4 文档预览 (`DocumentPreview.tsx`)

**功能**: 预览文档内容

#### 2.5 用户资料 (`UserProfile.tsx`)

**功能**: 显示用户信息和 Token 使用统计

### 3. 状态管理 (`store/authStore.ts`)

**职责**: 使用 Zustand 管理认证状态

**状态**:
- `user` - 当前用户信息
- `token` - JWT Token
- `isAuthenticated` - 认证状态

**方法**:
- `login()` - 登录
- `logout()` - 登出
- `checkAuth()` - 检查认证状态

### 4. API 客户端 (`lib/api.ts`)

**职责**: 封装 HTTP 请求

**功能**:
- Axios 实例配置
- 请求拦截器（自动添加 Token）
- 响应拦截器（处理错误）
- API 方法封装

---

## 🔄 数据流转

### 1. 文档上传流程

```
用户上传文档
  ↓
文件验证（类型、大小）
  ↓
上传到 S3
  ↓
文档解析（提取文本）
  ↓
文本切分（智能切块）
  ↓
生成向量嵌入（OpenAI）
  ↓
存储到 Qdrant
  ↓
保存元数据到数据库
  ↓
返回成功响应
```

### 2. 问答流程

```
用户提问
  ↓
生成问题向量嵌入
  ↓
在 Qdrant 中检索相似文档片段
  ↓
构建上下文提示词
  ↓
调用 OpenAI API（流式）
  ↓
实时返回生成内容
  ↓
保存对话到数据库
  ↓
记录 Token 使用量
```

### 3. 认证流程

```
用户登录
  ↓
验证邮箱和密码
  ↓
生成 JWT Token
  ↓
返回 Token
  ↓
前端存储 Token
  ↓
后续请求携带 Token
  ↓
中间件验证 Token
  ↓
获取用户信息
```

---

## 🔐 安全架构

### 1. 认证和授权

- **JWT Token**: 无状态认证
- **密码加密**: bcrypt 哈希
- **Token 过期**: 可配置过期时间

### 2. 输入验证

- **Pydantic**: 自动验证请求数据
- **SQL 注入防护**: 输入清理
- **XSS 防护**: HTML 标签过滤
- **文件验证**: 类型和大小检查

### 3. API 安全

- **限流**: 防止滥用
- **CORS**: 跨域安全配置
- **HTTPS**: 生产环境强制使用
- **信任主机**: 生产环境验证主机

### 4. 敏感数据保护

- **环境变量**: 敏感配置不硬编码
- **API Key 加密**: Fernet 对称加密
- **密钥轮换**: 支持定期轮换
- **生产环境检查**: 禁止使用默认密钥

---

## 📊 性能优化

### 1. 缓存策略

- **Embedding 缓存**: 相同文本不重复生成向量
- **检索结果缓存**: 减少 Qdrant 查询
- **Redis 支持**: 多实例共享缓存

### 2. 异步处理

- **异步数据库**: SQLAlchemy async
- **异步 HTTP**: FastAPI async/await
- **流式响应**: 减少等待时间

### 3. 批量处理

- **批量导入**: 文档批量处理
- **批量向量生成**: 减少 API 调用次数

---

## 🛠️ 工具脚本 (`scripts/`)

### 1. 数据库初始化 (`init_db.py`)

**功能**: 创建数据库表和默认用户

### 2. 批量导入 (`batch_import.py`)

**功能**: 批量导入文档到知识库

### 3. 文档更新 (`update_documents.py`)

**功能**: 更新已存在的文档

### 4. 知识库检查 (`check_knowledge_base.py`)

**功能**: 检查知识库状态和数据

### 5. 重置集合 (`reset_qdrant_collection.py`)

**功能**: 重置 Qdrant 集合（清空数据）

---

## 📝 开发规范

### 1. 代码组织

- **分层架构**: API → Service → Database
- **单一职责**: 每个模块职责明确
- **依赖注入**: 使用 FastAPI 依赖注入

### 2. 错误处理

- **统一异常**: HTTPException
- **日志记录**: 记录错误详情
- **用户友好**: 返回清晰的错误信息

### 3. 代码风格

- **类型提示**: 使用类型注解
- **文档字符串**: 函数和类都有文档
- **命名规范**: 清晰的变量和函数名

---

## 🔗 外部依赖

### 1. OpenAI API

- **GPT-4-Turbo**: 文本生成
- **text-embedding-3-large**: 向量嵌入

### 2. Qdrant Cloud

- **向量存储**: 文档向量存储
- **相似度检索**: 语义搜索

### 3. AWS S3

- **文件存储**: 文档文件存储

### 4. Redis（可选）

- **缓存**: 性能优化

---

## 📈 扩展性

### 1. 水平扩展

- **无状态 API**: 可以部署多个实例
- **Redis 缓存**: 共享缓存
- **数据库连接池**: 支持高并发

### 2. 垂直扩展

- **异步处理**: 提高吞吐量
- **缓存优化**: 减少数据库查询
- **批量处理**: 提高效率

---

## 🎯 总结

本项目采用**分层架构**和**模块化设计**：

1. **API 层**: 处理 HTTP 请求和响应
2. **服务层**: 业务逻辑封装
3. **数据层**: 数据库和外部服务交互
4. **工具层**: 通用工具函数

每个层次职责明确，便于维护和扩展。代码遵循最佳实践，注重安全性和性能优化。

