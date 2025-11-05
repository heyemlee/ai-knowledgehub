# ABC AI Knowledge Hub - 架构文档

企业级知识库系统的技术架构详细说明

## 📋 目录

1. [整体架构](#整体架构)
2. [后端架构](#后端架构)
3. [前端架构](#前端架构)
4. [数据流](#数据流)
5. [安全机制](#安全机制)
6. [部署架构](#部署架构)
7. [性能优化](#性能优化)
8. [错误处理](#错误处理)

---

## 整体架构

### 系统架构图

```
┌─────────────┐
│   浏览器     │
└──────┬──────┘
       │ HTTP/SSE
┌──────▼──────────────────┐
│   Next.js 前端          │
│  - React 组件           │
│  - Zustand 状态管理     │
│  - TailwindCSS 样式     │
│  - next-intl 国际化     │
└──────┬──────────────────┘
       │ REST API / SSE
┌──────▼──────────────────┐
│   FastAPI 后端          │
│  - JWT 认证             │
│  - RAG 问答引擎         │
│  - 文档处理管道         │
│  - 请求限流             │
│  - API 监控             │
└──┬───┬───┬───┬──────────┘
   │   │   │   │
┌──▼───▼───▼───▼──────┐
│  数据存储层          │
│  - PostgreSQL/SQLite│
│  - Qdrant 向量库    │
│  - 本地文件存储     │
│  - Redis 缓存(可选) │
└─────────────────────┘
         │
    ┌────▼────┐
    │ OpenAI  │
    │  API    │
    └─────────┘
```

### 技术栈

**后端**
- FastAPI 0.104.1 - 异步 Web 框架
- SQLAlchemy 2.0.23 - 异步 ORM
- Qdrant Client 1.7.0 - 向量数据库客户端
- OpenAI SDK 1.12.0+ - GPT-4 和 Embeddings
- Python-JOSE 3.3.0 - JWT 认证
- Passlib + Bcrypt - 密码加密
- SlowAPI 0.1.9 - 请求限流
- Tenacity 8.2.3 - 重试机制

**前端**
- Next.js 14.0.4 - React 框架
- TypeScript 5.3.3 - 类型安全
- TailwindCSS 3.3.6 - 样式框架
- Zustand 4.4.7 - 状态管理
- next-intl 4.4.0 - 国际化
- React Markdown 10.1.0 - Markdown 渲染
- Axios 1.6.2 - HTTP 客户端

**存储**
- PostgreSQL (生产环境) / SQLite (开发环境)
- Qdrant Cloud - 向量数据库
- 本地文件系统 - 文档存储（支持 Railway Volumes）

---

## 后端架构

### 目录结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── api/                  # API 路由层
│   │   ├── auth.py          # 认证相关
│   │   ├── chat.py          # 问答接口
│   │   ├── documents.py     # 文档管理
│   │   ├── conversations.py # 对话管理
│   │   ├── token_usage.py   # Token 统计
│   │   ├── api_keys.py      # API Key 加密管理
│   │   └── admin.py         # 管理员接口
│   ├── core/                 # 核心配置
│   │   ├── config.py        # 环境变量配置
│   │   └── constants.py     # 系统常量
│   ├── db/                   # 数据库层
│   │   ├── database.py      # 数据库连接管理
│   │   └── models.py        # SQLAlchemy 模型
│   ├── models/               # 数据模型
│   │   └── schemas.py       # Pydantic 模型
│   ├── services/             # 业务服务层
│   │   ├── openai_service.py      # OpenAI 服务
│   │   ├── qdrant_service.py      # Qdrant 向量服务
│   │   ├── rag_service.py         # RAG 服务
│   │   ├── local_storage_service.py # 本地存储服务
│   │   ├── token_usage_service.py   # Token 统计服务
│   │   ├── cache_service.py         # 缓存服务
│   │   ├── api_key_manager.py      # API Key 管理
│   │   └── prompts.py              # Prompt 模板
│   ├── utils/                # 工具函数
│   │   ├── auth.py          # JWT 认证工具
│   │   ├── document_parser.py # 文档解析器
│   │   ├── file_validator.py  # 文件验证器
│   │   ├── sanitizer.py      # 输入清理器
│   │   ├── language_detector.py # 语言检测
│   │   └── retry.py          # 重试机制
│   └── middleware/          # 中间件
│       ├── rate_limit.py    # 请求限流
│       └── monitoring.py    # API 监控
├── storage/                  # 文件存储目录
└── requirements.txt          # Python 依赖
```

### API 路由层

#### 认证模块 (`api/auth.py`)

- `POST /api/v1/auth/login` - 用户登录，返回 JWT Token
- `POST /api/v1/auth/register` - 用户注册（仅开发环境）
- `GET /api/v1/auth/me` - 获取当前用户信息

**认证流程：**
1. 用户提交邮箱和密码
2. 验证密码（Bcrypt 哈希比对）
3. 生成 JWT Token（包含 user_id, email, role）
4. 返回 Token 给前端

#### 问答模块 (`api/chat.py`)

- `POST /api/v1/chat/stream` - 流式问答接口（SSE）

**RAG 问答流程：**
1. 接收用户问题，验证 Token 和 Token 使用限制
2. 生成问题向量嵌入（OpenAI Embeddings API）
3. 根据问题长度智能调整检索参数
4. 在 Qdrant 中检索相似文档（向量相似度搜索）
5. 优化上下文（限制 Token 数，去重）
6. 构建提示词（包含上下文和问题）
7. 流式生成回答（OpenAI GPT-4 API，SSE 实时返回）
8. 保存对话历史到数据库
9. 记录 Token 使用量

**智能检索策略：**
- 短问题（≤6字符）：limit=20, threshold=0.3
- 普通问题：limit=10, threshold=0.5
- 降级检索：如果结果不足，降低阈值重试

#### 文档管理模块 (`api/documents.py`)

- `POST /api/v1/documents/upload` - 上传文档（最大 50MB）
- `GET /api/v1/documents/list` - 获取当前用户的文档列表
- `GET /api/v1/documents/{file_id}/preview` - 预览文档
- `GET /api/v1/documents/{file_id}/download` - 下载文档
- `DELETE /api/v1/documents/{file_id}` - 删除文档

**文档处理流程：**
1. 文件验证（类型、大小、文件名清理）
2. 保存到本地存储（UUID 文件 ID）
3. 根据文件类型解析内容：
   - PDF: PyPDF2
   - Word: python-docx
   - Excel: openpyxl
   - TXT/MD: 文本解析
4. 文本分块（Chunking）：
   - 默认块大小：1000 字符
   - 重叠：200 字符
   - 智能切分（优先在段落、句子边界）
5. 生成向量嵌入（OpenAI Embeddings API）
6. 存储向量到 Qdrant（包含元数据）
7. 保存文档元数据到数据库
8. 记录 Token 使用量

#### 对话管理模块 (`api/conversations.py`)

- `GET /api/v1/conversations` - 获取当前用户的对话列表
- `GET /api/v1/conversations/{conversation_id}/messages` - 获取对话消息
- `DELETE /api/v1/conversations/{conversation_id}` - 删除对话

#### Token 统计模块 (`api/token_usage.py`)

- `GET /api/v1/token-usage/stats` - 获取当前用户的 Token 使用统计

**Token 限制：**
- 每日限制：100K tokens/用户
- 每月限制：2M tokens/用户
- 单次请求限制：50K tokens

#### API Key 管理模块 (`api/api_keys.py`)

- `POST /api/v1/api-keys/encrypt` - 加密 API Key
- `POST /api/v1/api-keys/decrypt` - 解密 API Key
- `POST /api/v1/api-keys/rotate` - 轮换 API Key

**加密方式：** Fernet (对称加密)

#### 管理员模块 (`api/admin.py`)

- `GET /api/v1/admin/documents` - 获取所有文档（管理员）
- `GET /api/v1/admin/documents/stats` - 文档统计
- `DELETE /api/v1/admin/documents/{file_id}` - 删除任意文档
- `GET /api/v1/admin/users` - 获取所有用户
- `GET /api/v1/admin/users/stats` - 用户统计

### 核心配置

#### `core/config.py`

使用 Pydantic Settings 管理环境变量

**关键配置项：**
- `MODE` - 运行模式（development/production）
- `OPENAI_API_KEY` - OpenAI API 密钥
- `OPENAI_MODEL` - GPT 模型（默认：gpt-4-turbo-preview）
- `OPENAI_EMBEDDING_MODEL` - Embedding 模型（默认：text-embedding-3-large）
- `QDRANT_URL` / `QDRANT_API_KEY` - Qdrant 配置
- `QDRANT_COLLECTION_NAME` - 集合名称（默认：knowledge_base）
- `JWT_SECRET_KEY` - JWT 密钥（生产环境必须修改）
- `JWT_EXPIRATION_HOURS` - Token 过期时间（默认：24小时）
- `DATABASE_URL` - 数据库连接字符串
- `LOCAL_STORAGE_PATH` - 本地存储路径（默认：./storage）
- `REDIS_URL` - Redis 缓存（可选）
- `CORS_ORIGINS` - CORS 允许的来源
- `ALLOWED_HOSTS` - 允许的主机（生产环境）

**生产环境安全检查：**
- 检测默认 JWT_SECRET_KEY，如果是默认值则抛出异常

#### `core/constants.py`

系统常量定义

**RateLimitConfig** - API 限流配置
- `GLOBAL_RATE_LIMIT` - 全局限流：100/minute
- `AUTH_RATE_LIMIT` - 认证限流：5/minute
- `CHAT_RATE_LIMIT` - 问答限流：30/minute
- `UPLOAD_RATE_LIMIT` - 上传限流：10/minute
- `DOCUMENT_RATE_LIMIT` - 文档列表限流：60/minute

**TokenLimitConfig** - Token 限制配置
- `DAILY_TOKEN_LIMIT_PER_USER` - 每日限制：100K tokens
- `MONTHLY_TOKEN_LIMIT_PER_USER` - 每月限制：2M tokens
- `MAX_TOKENS_PER_REQUEST` - 单次请求限制：50K tokens

**SearchConfig** - 向量检索配置
- `SHORT_QUERY_THRESHOLD` - 短查询阈值：6字符
- `SHORT_QUERY_LIMIT` - 短查询返回数量：20
- `NORMAL_QUERY_LIMIT` - 普通查询返回数量：10
- `FALLBACK_THRESHOLD_SCORE` - 降级检索阈值：0.2

**DocumentParserConfig** - 文档解析配置
- `DEFAULT_CHUNK_SIZE` - 默认块大小：1000字符
- `DEFAULT_OVERLAP` - 默认重叠：200字符

**ProcessingConfig** - 处理配置
- `MAX_CHUNKS_PER_FILE` - 每个文件最大块数：5
- `MAX_CONTEXT_DOCS` - 最大上下文文档数：5

**CacheConfig** - 缓存配置
- `EMBEDDING_CACHE_TTL` - Embedding 缓存时间：24小时
- `SEARCH_RESULT_CACHE_TTL` - 检索结果缓存：1小时
- `ENABLE_CACHE` - 是否启用缓存：True

### 数据库层

#### 数据模型 (`db/models.py`)

**User（用户）**
```python
- id: Integer (主键)
- email: String(255) (唯一索引)
- hashed_password: String(255)
- full_name: String(255) (可选)
- is_active: Boolean (默认 True)
- role: String(20) (user | admin)
- created_at: DateTime
- updated_at: DateTime
```

**Document（文档）**
```python
- id: Integer (主键)
- file_id: String(255) (唯一索引)
- filename: String(255)
- file_type: String(100)
- file_size: Integer
- user_id: Integer (外键 -> users.id)
- status: String(50) (completed | processing | failed)
- chunks_count: Integer (文档块数量)
- created_at: DateTime
- updated_at: DateTime
```

**Conversation（对话）**
```python
- id: Integer (主键)
- conversation_id: String(255) (唯一索引)
- user_id: Integer (外键 -> users.id)
- title: String(255) (可选)
- created_at: DateTime
- updated_at: DateTime
```

**Message（消息）**
```python
- id: Integer (主键)
- conversation_id: Integer (外键 -> conversations.id)
- role: String(20) (user | assistant)
- content: Text
- sources: Text (JSON 格式，可选)
- created_at: DateTime
```

**TokenUsage（Token 使用量）**
```python
- id: Integer (主键)
- user_id: Integer (外键 -> users.id, 索引)
- usage_date: DateTime (索引，用于按日统计)
- prompt_tokens: Integer
- completion_tokens: Integer
- total_tokens: Integer
- endpoint: String(100) (API 端点)
- created_at: DateTime
```

**数据库连接管理 (`db/database.py`)**
- 使用 SQLAlchemy AsyncIO
- 自动创建表结构
- 连接池管理
- 异步会话管理

### 业务服务层

#### OpenAI 服务 (`services/openai_service.py`)

**主要方法：**
- `generate_embeddings()` - 生成向量嵌入
  - 支持批量处理
  - 自动重试（指数退避）
  - 缓存支持
  - 返回 Token 使用量

- `stream_answer()` - 流式生成回答
  - SSE 格式返回
  - 实时 Token 统计
  - 错误处理

- `optimize_context_for_speed()` - 优化上下文
  - 限制 Token 数
  - 保留最重要的文档块

**特性：**
- 自动重试机制（Tenacity）
- Embedding 缓存（24小时）
- Token 统计和记录

#### Qdrant 服务 (`services/qdrant_service.py`)

**主要方法：**
- `add_documents()` - 添加文档向量
  - 自动创建集合（如果不存在）
  - 创建 Payload 索引（file_id, filename, source）
  - 批量插入

- `search()` - 向量检索
  - 智能缓存
  - 去重（相同内容）
  - 文件级去重（每个文件最多5个块）
  - 关键词匹配优先级
  - 重排序（精确匹配 > 关键词匹配 > 向量相似度）

- `delete_documents()` - 删除文档向量
  - 按 file_id 或 filename 删除
  - 清除相关缓存

- `get_all_documents()` - 获取所有文档元数据

**特性：**
- 自动创建集合和索引
- 连接重试机制
- 操作重试机制
- 搜索结果缓存（1小时）

#### RAG 服务 (`services/rag_service.py`)

整合 embedding、检索、生成的完整流程

**主要方法：**
- `process_query()` - 非流式查询处理
- `stream_query()` - 流式查询处理

**流程：**
1. 生成问题向量嵌入
2. 智能确定检索参数（基于问题长度）
3. 向量检索相似文档
4. 降级检索（如果结果不足）
5. 生成回答（流式或非流式）
6. 提取文档来源
7. 返回答案、来源和性能指标

#### 本地存储服务 (`services/local_storage_service.py`)

**主要方法：**
- `upload_file()` - 保存文件（UUID 文件 ID）
- `download_file()` - 读取文件
- `delete_file()` - 删除文件
- `file_exists()` - 检查文件是否存在
- `get_file_size()` - 获取文件大小

**特性：**
- UUID 文件 ID（避免文件名冲突）
- 自动创建存储目录
- Railway Volumes 支持

#### Token 统计服务 (`services/token_usage_service.py`)

**主要方法：**
- `record_usage()` - 记录 Token 使用量
- `get_daily_usage()` - 获取每日使用量
- `get_monthly_usage()` - 获取每月使用量
- `check_token_limit()` - 检查是否超过限制
- `get_usage_stats()` - 获取使用统计

**统计维度：**
- 按用户统计
- 按日期统计
- 按月份统计
- 按端点统计

#### 缓存服务 (`services/cache_service.py`)

**主要方法：**
- `get()` - 获取缓存
- `set()` - 设置缓存
- `clear()` - 清除缓存

**特性：**
- Redis 优先（如果配置）
- 内存缓存回退
- 自动过期

#### API Key 管理服务 (`services/api_key_manager.py`)

**主要方法：**
- `encrypt_api_key()` - 加密 API Key
- `decrypt_api_key()` - 解密 API Key
- `rotate_api_key()` - 轮换 API Key

**加密方式：** Fernet 对称加密

### 工具函数

#### 文档解析器 (`utils/document_parser.py`)

**支持的格式：**
- PDF - PyPDF2
- Word - python-docx（支持表格）
- Excel - openpyxl（支持多工作表）
- TXT - 文本解析（UTF-8/GBK）
- Markdown - 结构化解析（保留标题层级）

**分块策略：**
- 默认块大小：1000 字符
- 重叠：200 字符
- 智能切分：
  1. 优先在段落边界（双换行）
  2. 其次在句子边界（标点符号）
  3. 最后在单词边界（空格）

#### 文件验证器 (`utils/file_validator.py`)

- `validate_file()` - 验证文件类型和扩展名
- `validate_file_size()` - 验证文件大小（最大 50MB）

**允许的文件类型：**
- PDF: `.pdf`
- Word: `.docx`, `.doc`
- Excel: `.xlsx`, `.xls`
- 文本: `.txt`, `.md`

#### JWT 认证 (`utils/auth.py`)

- `create_access_token()` - 创建 JWT Token
- `get_current_user()` - 获取当前用户（依赖注入）
- `get_current_admin()` - 获取管理员（依赖注入）
- `verify_password()` - 验证密码
- `get_password_hash()` - 生成密码哈希

**Token 内容：**
- `sub` - 用户邮箱
- `user_id` - 用户 ID
- `role` - 用户角色
- `exp` - 过期时间

#### 输入清理器 (`utils/sanitizer.py`)

- `sanitize_filename()` - 清理文件名（防止路径遍历）
- `sanitize_email()` - 清理邮箱
- `sanitize_question()` - 清理问题文本
- `validate_xss_safe()` - XSS 检测

#### 重试机制 (`utils/retry.py`)

**OpenAI API 重试：**
- 最大重试次数：3
- 等待时间：2-60秒（指数退避）
- 可重试异常：RateLimitError, APIConnectionError, APITimeoutError, 5xx 错误

**Qdrant 连接重试：**
- 最大重试次数：5
- 等待时间：1-30秒（指数退避）

**Qdrant 操作重试：**
- 最大重试次数：3
- 等待时间：1-20秒（指数退避）

### 中间件

#### 限流中间件 (`middleware/rate_limit.py`)

基于 SlowAPI 实现

**限流规则：**
- 全局：100 请求/分钟
- 认证：5 请求/分钟（防止暴力破解）
- 问答：30 请求/分钟（AI 资源消耗大）
- 上传：10 请求/分钟（文件处理消耗资源）
- 文档列表：60 请求/分钟

**限流响应：**
- HTTP 429 Too Many Requests
- 错误消息：`"请求过于频繁，请稍后再试"`

#### 监控中间件 (`middleware/monitoring.py`)

**监控指标：**
- 请求数量（按端点统计）
- 错误数量（按端点统计）
- 响应时间（平均、最小、最大）
- 错误率

**统计窗口：** 1分钟

**API 端点：**
- `GET /api/v1/metrics` - 获取监控指标

---

## 前端架构

### 目录结构

```
frontend/
├── app/                      # Next.js App Router
│   ├── layout.tsx           # 根布局
│   ├── page.tsx             # 主页
│   └── [locale]/            # 国际化路由
│       ├── layout.tsx       # 本地化布局
│       └── page.tsx         # 本地化主页
├── components/              # React 组件
│   ├── ChatInterface.tsx    # 主聊天界面
│   ├── AdminPanel.tsx       # 管理后台
│   ├── ConversationHistory.tsx # 对话历史
│   ├── LoginForm.tsx        # 登录表单
│   └── UserProfile.tsx      # 用户资料
├── lib/                     # 工具库
│   ├── api.ts              # API 客户端
│   ├── adminApi.ts         # 管理员 API
│   ├── auth.ts             # 认证工具
│   └── translations.ts    # 翻译工具
├── store/                   # 状态管理
│   └── authStore.ts        # 认证状态（Zustand）
├── messages/                # 国际化消息
│   ├── en-US.json          # 英文
│   └── zh-CN.json          # 中文
├── middleware.ts            # Next.js 中间件
├── i18n.ts                 # 国际化配置
└── package.json            # 依赖配置
```

### 核心组件

#### ChatInterface (`components/ChatInterface.tsx`)

主聊天界面组件

**功能：**
- 问答输入框
- 消息展示（Markdown 渲染）
- 流式输出（SSE）
- 文档来源展示
- 对话历史侧边栏
- 管理后台入口（管理员）
- 用户资料入口

**状态管理：**
- `messages` - 消息列表
- `input` - 输入内容
- `loading` - 加载状态
- `streaming` - 流式输出状态
- `conversationId` - 当前对话 ID

#### AdminPanel (`components/AdminPanel.tsx`)

管理后台弹窗组件

**功能：**
- 仪表盘（文档统计、用户统计）
- 文档管理（上传、删除、搜索、下载）
- 用户管理（查看用户列表、统计）
- 自动刷新（每30秒）

**标签页：**
- Dashboard - 统计概览
- Documents - 文档管理
- Users - 用户管理

#### ConversationHistory (`components/ConversationHistory.tsx`)

对话历史组件

**功能：**
- 对话列表展示
- 加载对话消息
- 删除对话
- 切换对话

#### LoginForm (`components/LoginForm.tsx`)

登录/注册表单组件

**功能：**
- 邮箱和密码输入
- 表单验证
- 登录/注册切换
- 错误提示

### API 客户端

#### `lib/api.ts`

后端 API 封装

**chatAPI：**
- `stream()` - 流式问答（SSE）

**documentsAPI：**
- `upload()` - 上传文档
- `list()` - 获取文档列表
- `preview()` - 预览文档 URL
- `download()` - 下载文档
- `delete()` - 删除文档

**conversationsAPI：**
- `list()` - 获取对话列表
- `getMessages()` - 获取对话消息
- `delete()` - 删除对话

**tokenUsageAPI：**
- `getStats()` - 获取 Token 统计

#### `lib/adminApi.ts`

管理员 API 封装

- `getAllDocuments()` - 获取所有文档
- `deleteDocument()` - 删除文档
- `getDocumentStats()` - 文档统计
- `getAllUsers()` - 获取所有用户
- `getUserStats()` - 用户统计

#### `lib/auth.ts`

认证工具

- `isAdmin()` - 判断是否管理员
- JWT Token 解析
- Token 存储（localStorage）

### 状态管理

#### `store/authStore.ts`

使用 Zustand 管理认证状态

**状态：**
- `user` - 当前用户信息
- `token` - JWT Token

**方法：**
- `login()` - 登录
- `logout()` - 登出
- `register()` - 注册
- `setUser()` - 设置用户信息

### 国际化

#### `i18n.ts` 和 `messages/`

使用 next-intl 实现国际化

**支持语言：**
- 中文（zh-CN）
- 英文（en-US）

**功能：**
- 自动语言检测
- 语言切换
- 翻译函数 `t()`

---

## 数据流

### 问答流程

```
用户输入问题
  ↓
前端验证（非空、长度）
  ↓
POST /api/v1/chat/stream
  ↓
JWT 认证（验证 Token）
  ↓
Token 限制检查（预估 Token 数）
  ↓
生成问题向量嵌入（OpenAI Embeddings API）
  ↓
记录 Embedding Token 使用量
  ↓
智能确定检索参数（基于问题长度）
  ↓
向量检索（Qdrant）
  ├─ 检查缓存
  ├─ 向量相似度搜索
  ├─ 去重（相同内容、文件级）
  ├─ 关键词匹配优先级
  └─ 重排序
  ↓
优化上下文（限制 Token 数）
  ↓
构建提示词（包含上下文和问题）
  ↓
流式生成回答（OpenAI GPT-4 API）
  ↓
SSE 实时返回给前端
  ↓
保存对话历史（数据库）
  ↓
记录生成 Token 使用量
```

### 文档上传流程

```
用户选择文件
  ↓
前端验证（类型、大小）
  ↓
POST /api/v1/documents/upload
  ↓
JWT 认证
  ↓
后端验证（文件验证器）
  ├─ 文件类型检查
  ├─ 文件大小检查（最大 50MB）
  └─ 文件名清理（防止路径遍历）
  ↓
保存到本地存储（storage/）
  ├─ 生成 UUID 文件 ID
  └─ 保存文件内容
  ↓
解析文档内容（DocumentParser）
  ├─ PDF → PyPDF2
  ├─ Word → python-docx
  ├─ Excel → openpyxl
  └─ TXT/MD → 文本解析
  ↓
文本分块（Chunking）
  ├─ 默认块大小：1000 字符
  ├─ 重叠：200 字符
  └─ 智能切分（段落/句子边界）
  ↓
生成向量嵌入（OpenAI Embeddings API）
  ├─ 批量处理
  ├─ 缓存检查
  └─ 记录 Token 使用量
  ↓
存储向量到 Qdrant
  ├─ 自动创建集合（如果不存在）
  ├─ 创建 Payload 索引
  └─ 批量插入
  ↓
保存文档元数据（数据库）
  ├─ file_id
  ├─ filename
  ├─ file_type
  ├─ file_size
  ├─ user_id
  └─ chunks_count
  ↓
返回成功响应
```

---

## 安全机制

### 认证与授权

**JWT Token 认证**
- 无状态认证
- Token 包含：user_id, email, role
- Token 过期时间：24小时（可配置）
- 密码加密：Bcrypt（成本因子：12）

**角色权限**
- `admin` - 管理员权限
  - 查看所有文档
  - 删除任意文档
  - 查看所有用户
- `user` - 普通用户权限
  - 只能管理自己的文档

### 数据验证

**输入验证**
- Pydantic 模型验证
- 邮箱格式验证
- 密码强度验证（至少8字符，包含数字和字母）
- 问题长度限制（最大10000字符）

**文件验证**
- 文件类型白名单
- 文件大小限制（最大 50MB）
- 文件名清理（防止路径遍历攻击）
- 扩展名验证

**XSS 防护**
- 输入清理（sanitizer）
- XSS 检测（validate_xss_safe）

### API 安全

**请求限流**
- 防止 API 滥用
- 按端点配置不同限流规则
- 认证接口限流更严格（防止暴力破解）

**CORS 配置**
- 开发环境：允许 localhost 多个端口
- 生产环境：仅允许配置的前端域名

**Token 限制**
- 每日使用量限制：100K tokens/用户
- 每月使用量限制：2M tokens/用户
- 单次请求限制：50K tokens

**生产环境安全检查**
- 检测默认 JWT_SECRET_KEY
- TrustedHostMiddleware（生产环境）
- 禁用 API 文档（生产环境）

---

## 部署架构

### Railway 部署

```
GitHub Repository
  ↓ (自动部署)
Railway Platform
  ├── Backend Service
  │   ├── FastAPI 应用
  │   ├── Dockerfile 构建
  │   ├── Volume 挂载 (/app/backend/storage)
  │   └── 健康检查 (/health)
  ├── PostgreSQL Service
  │   └── 自动配置 DATABASE_URL
  └── Redis Service (可选)
      └── 自动配置 REDIS_URL
  ↓
Vercel (前端部署)
  └── Next.js 应用
      └── 环境变量 NEXT_PUBLIC_API_URL
```

### 环境变量配置

**必需配置：**
```env
MODE=production
OPENAI_API_KEY=sk-...
QDRANT_URL=https://...
QDRANT_API_KEY=...
JWT_SECRET_KEY=... (使用 scripts/generate_jwt_secret.py 生成)
FRONTEND_URL=https://...
```

**自动配置（Railway）：**
```env
DATABASE_URL=postgresql://... (Railway PostgreSQL)
REDIS_URL=redis://... (如果添加 Redis 服务)
PORT=8000 (Railway 自动分配)
```

### Volume 配置

**挂载路径：** `/app/backend/storage`
**最小大小：** 5GB
**用途：** 存储上传的文档文件

### 健康检查

**端点：** `GET /health`
**响应：** `{"status": "healthy", "mode": "production"}`
**超时：** 100秒

---

## 性能优化

### 缓存策略

**Embedding 缓存**
- 缓存时间：24小时
- 键：文本内容哈希
- 减少重复的 Embedding API 调用

**检索结果缓存**
- 缓存时间：1小时
- 键：问题向量哈希 + 检索参数
- 相同问题短时间内直接返回

**缓存实现**
- Redis 优先（如果配置）
- 内存缓存回退
- 自动过期

### 数据库优化

**索引**
- `users.email` - 唯一索引
- `documents.file_id` - 唯一索引
- `conversations.conversation_id` - 唯一索引
- `token_usage.user_id` - 索引
- `token_usage.usage_date` - 索引

**异步操作**
- SQLAlchemy AsyncIO
- 异步数据库连接
- 连接池复用

**查询优化**
- 使用 select() 明确指定字段
- 避免 N+1 查询
- 批量操作

### API 优化

**流式响应**
- SSE 实时返回
- 提升用户体验
- 减少等待时间

**上下文裁剪**
- 限制上下文 Token 数（2500 tokens）
- 保留最重要的文档块
- 加快生成速度

**动态参数**
- 根据问题长度调整检索参数
- 短问题使用更宽松的检索策略
- 减少不必要的检索

**去重优化**
- 内容去重（相同文本）
- 文件级去重（每个文件最多5个块）
- 减少重复内容

---

## 错误处理

### 重试机制

**OpenAI API 重试**
- 最大重试次数：3
- 等待时间：2-60秒（指数退避）
- 可重试异常：
  - RateLimitError（限流）
  - APIConnectionError（连接错误）
  - APITimeoutError（超时）
  - APIError（5xx 错误）

**Qdrant 连接重试**
- 最大重试次数：5
- 等待时间：1-30秒（指数退避）
- 可重试异常：
  - ConnectionError
  - TimeoutError
  - HTTPError

**Qdrant 操作重试**
- 最大重试次数：3
- 等待时间：1-20秒（指数退避）

### 降级策略

**Redis 不可用**
- 自动回退到内存缓存
- 不影响核心功能

**检索失败**
- 降低阈值重试（降级检索）
- 返回空结果（友好提示）

**Token 超限**
- 友好错误提示
- 显示剩余额度

**文档解析失败**
- 记录错误日志
- 返回错误响应
- 不中断服务

### 日志记录

**日志级别：**
- INFO - 正常操作日志
- WARNING - 警告信息
- ERROR - 错误信息（带堆栈）

**日志内容：**
- 请求路径和方法
- 响应时间
- 错误详情
- Token 使用量
- 用户操作

**生产环境：**
- CloudWatch 日志（如果配置）
- 日志组：`knowledgehub-logs`

---

## 开发规范

### 代码风格

**Python：**
- PEP 8
- 函数文档字符串（简洁）
- 类型注解（Type Hints）

**TypeScript：**
- ESLint + Prettier
- 严格类型检查
- 函数文档注释

### 提交规范

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `refactor:` 代码重构
- `chore:` 构建/工具变更
- `style:` 代码格式调整
- `test:` 测试相关

### 测试要求

- 核心功能单元测试
- API 端点集成测试
- 关键路径手动测试

---

**最后更新：** 2025-11-05  
**版本：** 1.0.0
