# 项目架构文档

ABC AI Knowledge Hub 企业级知识库系统的技术架构说明

## 📋 目录结构

```
abc-ai-knowledgehub/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── main.py         # 应用入口
│   │   ├── api/            # API 路由
│   │   ├── core/           # 配置和常量
│   │   ├── db/             # 数据库模型
│   │   ├── models/         # Pydantic 模型
│   │   ├── services/       # 业务逻辑
│   │   ├── utils/          # 工具函数
│   │   └── middleware/     # 中间件
│   ├── storage/            # 本地文件存储
│   └── requirements.txt
├── frontend/               # Next.js 前端
│   ├── app/               # 页面路由
│   ├── components/        # React 组件
│   ├── lib/               # API 客户端
│   └── store/             # 状态管理
├── scripts/               # 工具脚本
└── documents/             # 文档目录
```

## 🏗️ 技术架构

### 整体架构

```
┌─────────────┐
│   浏览器     │
└──────┬──────┘
       │ HTTP/WebSocket
┌──────▼──────────────────┐
│   Next.js 前端          │
│  - React 组件           │
│  - Zustand 状态管理     │
│  - TailwindCSS 样式     │
└──────┬──────────────────┘
       │ REST API / SSE
┌──────▼──────────────────┐
│   FastAPI 后端          │
│  - JWT 认证             │
│  - RAG 问答引擎         │
│  - 文档处理管道         │
└──┬───┬───┬───┬──────────┘
   │   │   │   │
   │   │   │   └──────────┐
   │   │   │              │
┌──▼───▼───▼───▼──────┐  │
│  数据存储层          │  │
│  - PostgreSQL/SQLite│  │
│  - Qdrant 向量库    │  │
│  - 本地文件存储     │  │
│  - Redis 缓存       │  │
└─────────────────────┘  │
                         │
                    ┌────▼────┐
                    │ OpenAI  │
                    │  API    │
                    └─────────┘
```

## 🔧 后端架构

### API 路由层

#### 认证模块 (`api/auth.py`)

- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/register` - 用户注册（仅开发环境）
- `GET /api/v1/auth/me` - 获取当前用户信息

#### 问答模块 (`api/chat.py`)

- `POST /api/v1/chat/stream` - 流式问答（SSE）

**RAG 问答流程：**

1. 接收用户问题
2. 生成问题向量嵌入（OpenAI Embeddings）
3. 向量检索相关文档（Qdrant）
4. 构建上下文提示词
5. 流式生成回答（OpenAI GPT-4）
6. 保存对话历史

#### 文档管理模块 (`api/documents.py`)

- `POST /api/v1/documents/upload` - 上传文档
- `GET /api/v1/documents/list` - 文档列表
- `GET /api/v1/documents/{id}/preview` - 预览文档
- `GET /api/v1/documents/{id}/download` - 下载文档
- `DELETE /api/v1/documents/{id}` - 删除文档

**文档处理流程：**

1. 文件验证（类型、大小）
2. 保存到本地存储
3. 解析文档内容（PDF/Word/Excel/TXT）
4. 文本分块（Chunk）
5. 生成向量嵌入
6. 存储到 Qdrant
7. 保存元数据到数据库

#### 对话管理模块 (`api/conversations.py`)

- `GET /api/v1/conversations` - 对话列表
- `GET /api/v1/conversations/{id}/messages` - 对话消息
- `DELETE /api/v1/conversations/{id}` - 删除对话

#### 管理员模块 (`api/admin.py`)

- `GET /api/v1/admin/documents` - 所有文档（管理员）
- `GET /api/v1/admin/documents/stats` - 文档统计
- `DELETE /api/v1/admin/documents/{id}` - 删除任意文档
- `GET /api/v1/admin/users` - 所有用户
- `GET /api/v1/admin/users/stats` - 用户统计

### 核心配置

#### `core/config.py`

环境变量管理（使用 Pydantic Settings）

**关键配置：**

- `MODE` - 运行模式（development/production）
- `OPENAI_API_KEY` - OpenAI API 密钥
- `QDRANT_URL` / `QDRANT_API_KEY` - Qdrant 配置
- `JWT_SECRET_KEY` - JWT 密钥
- `DATABASE_URL` - 数据库连接
- `REDIS_URL` - Redis 缓存（可选）

#### `core/constants.py`

系统常量定义

- `RateLimitConfig` - API 限流配置
- `TokenLimitConfig` - Token 限制配置
- `SearchConfig` - 向量检索配置
- `DocumentParserConfig` - 文档解析配置
- `AIConfig` - AI 模型配置

### 数据库层

#### 数据模型 (`db/models.py`)

**User（用户）**

- `id`, `email`, `hashed_password`, `full_name`, `role`, `is_active`, `created_at`

**Document（文档）**

- `id`, `file_id`, `filename`, `file_type`, `file_size`, `user_id`, `chunks_count`, `status`, `created_at`

**Conversation（对话）**

- `id`, `conversation_id`, `user_id`, `title`, `created_at`, `updated_at`

**Message（消息）**

- `id`, `conversation_id`, `role`, `content`, `sources`, `created_at`

**TokenUsage（Token 使用量）**

- `id`, `user_id`, `endpoint`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `created_at`

### 业务服务层

#### OpenAI 服务 (`services/openai_service.py`)

- `generate_embeddings()` - 生成向量嵌入
- `generate_completion_stream()` - 流式生成回答
- `optimize_context_for_speed()` - 优化上下文

**特性：**

- 自动重试机制
- 缓存支持
- Token 统计

#### Qdrant 服务 (`services/qdrant_service.py`)

- `add_documents()` - 添加文档向量
- `search()` - 向量检索
- `delete_documents()` - 删除文档向量
- `get_all_documents()` - 获取所有文档

**特性：**

- 自动创建集合
- 连接重试
- 分组聚合

#### 本地存储服务 (`services/local_storage_service.py`)

- `upload_file()` - 保存文件
- `download_file()` - 读取文件
- `delete_file()` - 删除文件

**特性：**

- UUID 文件 ID
- 目录自动创建
- Railway Volumes 支持

#### 缓存服务 (`services/cache_service.py`)

- `get()` / `set()` - 缓存操作
- 自动回退（Redis → 内存）

#### Token 统计服务 (`services/token_usage_service.py`)

- `record_usage()` - 记录使用量
- `check_token_limit()` - 检查限制
- `get_usage_stats()` - 获取统计

### 工具函数

#### 文档解析器 (`utils/document_parser.py`)

- `parse_pdf()` - 解析 PDF
- `parse_docx()` - 解析 Word
- `parse_excel()` - 解析 Excel
- `parse_text()` - 解析文本
- `chunk_text()` - 文本分块

#### 文件验证器 (`utils/file_validator.py`)

- `validate_file()` - 验证文件类型
- `validate_file_size()` - 验证文件大小

#### JWT 认证 (`utils/auth.py`)

- `create_access_token()` - 创建 JWT Token
- `get_current_user()` - 获取当前用户（依赖注入）
- `get_current_admin()` - 获取管理员（依赖注入）

### 中间件

#### 限流中间件 (`middleware/rate_limit.py`)

- 基于 SlowAPI
- 按端点配置不同限流规则

#### 监控中间件 (`middleware/monitoring.py`)

- 请求统计
- 响应时间监控
- 错误追踪

## 🎨 前端架构

### 页面结构

```
app/
├── page.tsx              # 主页（聊天界面）
├── layout.tsx            # 根布局
└── globals.css           # 全局样式
```

### 核心组件

#### `components/ChatInterface.tsx`

主聊天界面

- 问答输入
- 消息展示
- 流式输出
- 来源文档展示
- 管理后台入口（管理员）

#### `components/AdminPanel.tsx`

管理后台弹窗

- 仪表盘（统计）
- 文档管理（上传、删除、搜索）
- 用户管理（查看用户列表）

#### `components/LoginForm.tsx`

登录/注册表单

- JWT 认证
- 表单验证
- 错误处理

#### `components/ConversationHistory.tsx`

对话历史

- 对话列表
- 消息展示
- 删除对话

### API 客户端

#### `lib/api.ts`

后端 API 封装

- `chatAPI` - 问答接口
- `documentsAPI` - 文档接口
- `conversationsAPI` - 对话接口

#### `lib/adminApi.ts`

管理员 API 封装

- `getAdminDocuments()` - 获取所有文档
- `deleteDocument()` - 删除文档
- `getDocumentStats()` - 文档统计
- `getAllUsers()` - 获取所有用户

#### `lib/auth.ts`

认证工具

- `isAdmin()` - 判断是否管理员
- JWT Token 解析

### 状态管理

#### `store/authStore.ts`

用户认证状态（Zustand）

- `user` - 当前用户
- `token` - JWT Token
- `login()` - 登录
- `logout()` - 登出
- `register()` - 注册

## 🔐 安全机制

### 认证与授权

- **JWT Token** - 无状态认证
- **角色权限** - admin / user 两级权限
- **密码加密** - Bcrypt 哈希

### 数据验证

- **输入验证** - Pydantic 模型验证
- **文件验证** - 类型、大小、扩展名检查
- **文件名清理** - 防止路径遍历攻击

### API 安全

- **请求限流** - 防止 API 滥用
- **CORS 配置** - 跨域请求控制
- **Token 限制** - 每月使用量限制

## 📊 数据流

### 问答流程

```
用户输入
  ↓
前端验证
  ↓
POST /api/v1/chat/stream
  ↓
JWT 认证 & Token 限制检查
  ↓
生成问题向量（OpenAI Embeddings）
  ↓
向量检索（Qdrant）
  ↓
构建提示词 + 上下文
  ↓
流式生成回答（OpenAI GPT-4）
  ↓
SSE 实时返回给前端
  ↓
保存对话历史到数据库
  ↓
记录 Token 使用量
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
  ↓
保存到本地存储（storage/）
  ↓
解析文档内容（DocumentParser）
  ↓
文本分块（Chunking）
  ↓
生成向量嵌入（OpenAI Embeddings）
  ↓
存储向量（Qdrant）
  ↓
保存元数据（PostgreSQL/SQLite）
  ↓
返回成功响应
```

## 🚀 部署架构

### Railway 部署

```
GitHub Repo
  ↓ 自动部署
Railway
  ├── Backend Service
  │   ├── FastAPI 应用
  │   └── Volume (/app/backend/storage)
  ├── PostgreSQL
  └── Redis（可选）
  ↓
Vercel（前端）
  └── Next.js 应用
```

### 环境变量

**必需：**

- `MODE=production`
- `OPENAI_API_KEY`
- `QDRANT_URL` / `QDRANT_API_KEY`
- `JWT_SECRET_KEY`

**自动配置：**

- `DATABASE_URL` - Railway PostgreSQL
- `REDIS_URL` - Railway Redis

## 🛠️ 工具脚本

### `scripts/init_db.py`

初始化数据库，创建默认管理员账号

### `scripts/batch_import.py`

批量导入 `documents/` 目录下的文档

### `scripts/update_documents.py`

更新指定文档到向量库

### `scripts/check_knowledge_base.py`

检查 Qdrant 向量库状态

### `scripts/generate_jwt_secret.py`

生成强随机 JWT 密钥

### `scripts/reset_qdrant_collection.py`

重置 Qdrant 集合

## 📈 性能优化

### 缓存策略

- **Embedding 缓存** - 相同文本不重复生成向量
- **检索结果缓存** - 相同问题短时间内直接返回

### 数据库优化

- **索引** - email, file_id, conversation_id 等
- **异步操作** - SQLAlchemy AsyncIO
- **连接池** - 复用数据库连接

### API 优化

- **流式响应** - SSE 实时返回，提升体验
- **上下文裁剪** - 限制上下文 Token 数，加快生成
- **动态参数** - 根据问题长度调整检索参数

## 🐛 错误处理

### 重试机制

- **OpenAI API** - 指数退避重试
- **Qdrant 连接** - 自动重连
- **网络请求** - 自动重试

### 日志记录

- **INFO** - 正常操作日志
- **WARNING** - 警告信息
- **ERROR** - 错误信息（带堆栈）

### 降级策略

- **Redis 不可用** → 回退到内存缓存
- **检索失败** → 降低阈值重试
- **Token 超限** → 友好提示

## 📝 开发规范

### 代码风格

- Python: PEP 8 + Black
- TypeScript: ESLint + Prettier
- 函数文档字符串（简洁明了）

### 提交规范

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `refactor:` 代码重构
- `chore:` 构建/工具变更

### 测试要求

- 核心功能单元测试
- API 端点集成测试
- 关键路径手动测试

---

**最后更新**: 2025-10-31  
**版本**: 1.0.0
