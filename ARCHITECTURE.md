# ABC AI Knowledge Hub - 架构文档

## 整体架构

### 系统架构图

```
┌─────────────┐
│   浏览器     │
└──────┬──────┘
       │ HTTP/SSE
┌──────▼──────────────────┐
│   Next.js 前端 (Vercel) │
│  - React + TypeScript   │
│  - Zustand 状态管理     │
└──────┬──────────────────┘
       │ REST API / SSE
┌──────▼──────────────────┐
│   FastAPI 后端 (AWS)    │
│  - JWT 认证             │
│  - RAG 问答引擎         │
│  - 请求限流             │
└──┬───┬───┬───┬──────────┘
   │   │   │   │
┌──▼───▼───▼───▼──────┐
│  数据存储层          │
│  - PostgreSQL/RDS   │
│  - Qdrant 向量库    │
│  - S3 文件存储      │
└─────────────────────┘
         │
    ┌────▼────┐
    │ OpenAI  │
    └─────────┘
```

### 技术栈

**后端**

- FastAPI - 异步 Web 框架
- SQLAlchemy - 异步 ORM
- Qdrant - 向量数据库
- OpenAI SDK - GPT-4 + Embeddings
- JWT 认证 + Bcrypt 密码加密

**前端**

- Next.js 14 - React 框架
- TypeScript - 类型安全
- TailwindCSS - 样式框架
- Zustand - 状态管理

**存储**

- PostgreSQL (生产) / SQLite (开发)
- Qdrant Cloud - 向量数据库
- AWS S3 - 文件存储

---

## 后端架构

### 目录结构

```
backend/
├── app/
│   ├── api/          # API 路由（auth, chat, documents, admin等）
│   ├── core/         # 配置和常量
│   ├── db/           # 数据库模型
│   ├── services/     # 业务服务（RAG, OpenAI, Qdrant等）
│   ├── utils/        # 工具函数
│   └── middleware/   # 限流、监控中间件
└── storage/          # 文件存储
```

### API 端点

**认证**

- `POST /api/v1/auth/login` - 登录
- `POST /api/v1/auth/register` - 注册（仅开发环境）
- `GET /api/v1/auth/me` - 获取当前用户

**问答**

- `POST /api/v1/chat/stream` - 流式问答（SSE）

**文档管理**

- `POST /api/v1/documents/upload` - 上传文档（最大50MB）
- `GET /api/v1/documents/list` - 文档列表
- `DELETE /api/v1/documents/{file_id}` - 删除文档

**管理员**

- `GET /api/v1/admin/documents` - 所有文档
- `GET /api/v1/admin/users` - 所有用户

### 核心服务

**RAG 服务**

- 生成问题向量嵌入
- 智能检索（根据问题长度调整参数）
- 向量相似度搜索 + 关键词匹配
- 上下文优化和去重
- 流式生成回答

**文档处理**

- 支持 PDF、Word、Excel、TXT、Markdown
- 文本分块（1000字符/块，200字符重叠）
- 生成向量嵌入并存储到 Qdrant

**数据模型**

- User（用户）
- Document（文档）
- Conversation（对话）
- Message（消息）
- TokenUsage（Token使用统计）

---

## 前端架构

### 目录结构

```
frontend/
├── app/              # Next.js App Router
├── components/       # React 组件
│   ├── ChatInterface.tsx
│   ├── AdminPanel.tsx
│   └── LoginForm.tsx
├── lib/             # API 客户端
└── store/           # Zustand 状态管理
```

### 核心组件

- **ChatInterface** - 主聊天界面，支持流式输出（SSE）
- **AdminPanel** - 管理后台（文档管理、用户管理）
- **LoginForm** - 登录/注册表单

### API 客户端

使用 `NEXT_PUBLIC_API_URL` 环境变量配置后端地址，支持：

- REST API 调用（Axios）
- SSE 流式响应（Fetch API）

---

## 数据流

### 问答流程

```
用户问题
  ↓
前端验证 → POST /api/v1/chat/stream
  ↓
JWT 认证 + Token 限制检查
  ↓
生成问题向量嵌入（OpenAI）
  ↓
向量检索（Qdrant）
  ├─ 智能参数调整
  ├─ 去重和重排序
  └─ 上下文优化
  ↓
流式生成回答（OpenAI GPT-4）
  ↓
SSE 实时返回前端
  ↓
保存对话历史 + 记录 Token 使用量
```

### 文档上传流程

```
文件上传
  ↓
文件验证（类型、大小）
  ↓
保存到存储（UUID文件ID）
  ↓
解析文档内容（PDF/Word/Excel/TXT）
  ↓
文本分块（1000字符/块）
  ↓
生成向量嵌入（OpenAI）
  ↓
存储到 Qdrant + 保存元数据到数据库
```

---

## 安全机制

### 认证与授权

- JWT Token 认证（24小时过期）
- Bcrypt 密码加密（成本因子12）
- 角色权限（admin/user）

### API 安全

- 请求限流：全局100/分钟，认证5/分钟，问答30/分钟
- CORS 配置：生产环境仅允许配置的前端域名
- Token 限制：每日100K，每月2M tokens/用户
- 生产环境安全检查：检测默认 JWT_SECRET_KEY

### 数据验证

- 文件类型白名单、大小限制（50MB）
- 输入清理（防止XSS、路径遍历）
- Pydantic 模型验证

---

## 部署架构

### 架构概览

```
GitHub Repository
  ↓ (Push to main)
GitHub Actions CI/CD
  ├── 构建 Docker 镜像
  ├── 推送到 ECR
  └── 更新 ECS 服务
  ↓
AWS ECS Fargate (后端)
  ├── FastAPI 应用
  ├── Secrets Manager 集成
  └── CloudWatch 日志
  ↓
Application Load Balancer
  ↓
Route 53 DNS

Vercel (前端)
  ├── Next.js 应用
  └── 环境变量 NEXT_PUBLIC_API_URL
```

### 配置管理

**AWS Secrets Manager**（敏感配置）

- `knowledgehub/database-url`
- `knowledgehub/openai-api-key`
- `knowledgehub/qdrant-url`
- `knowledgehub/jwt-secret`
- `knowledgehub/frontend-url`（Vercel域名）

**ECS 任务定义**（非敏感配置）

- `MODE=production`
- `PORT=8000`
- `LOG_LEVEL=INFO`

**Vercel 环境变量**

- `NEXT_PUBLIC_API_URL` - AWS 后端地址

### GitHub Actions

**触发条件**：推送到 `main` 分支

**部署流程**：

1. Checkout 源代码
2. 配置 AWS 凭证（GitHub Secrets）
3. 登录 ECR
4. 构建并推送 Docker 镜像
5. 触发 ECS 服务更新

---

## 性能优化

### 缓存策略

- Embedding 缓存：24小时（减少重复 API 调用）
- 检索结果缓存：1小时（相同问题快速返回）
- Redis 优先，内存缓存回退

### 数据库优化

- 关键字段索引（email, file_id, user_id等）
- 异步操作（SQLAlchemy AsyncIO）
- 连接池复用

### API 优化

- 流式响应（SSE）提升用户体验
- 上下文裁剪（限制2500 tokens）
- 智能检索参数（根据问题长度调整）
- 去重优化（内容去重 + 文件级去重）
