# AI Knowledge Hub

AI 知识库系统，基于 RAG（检索增强生成）技术的智能问答平台

## ✨ 核心特性

- 🤖 **高性能 RAG 引擎** - 并行处理 + Rerank + 向量优化，精准快速
- 📄 **多格式文档支持** - PDF、Word、Excel、TXT、Markdown
- 🎯 **智能检索** - 向量相似度 + 关键词匹配 + GPT-4o-mini 重排序
- 👥 **企业级权限** - JWT 认证 + 角色管理 + Token 配额
- 📊 **数据分析** - Token 使用统计 + 对话历史追踪
- 🔐 **生产级安全** - 请求限流 + 加密存储 + CORS 保护

## 🚀 快速开始

### 本地开发

#### 1. 克隆项目

```bash
git clone <repository-url>
cd abc-ai-knowledgehub
```

#### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
# 必需配置
OPENAI_API_KEY=sk-your-openai-api-key
QDRANT_URL=https://your-cluster-id.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
JWT_SECRET_KEY=$(python scripts/generate_jwt_secret.py)

# 可选配置（开发环境使用默认值）
MODE=development
DATABASE_URL=sqlite+aiosqlite:///./knowledgehub.db  # 开发环境默认 SQLite
FRONTEND_URL=http://localhost:3000

# S3 存储配置（生产环境必需）
STORAGE_TYPE=s3  # local 或 s3
AWS_REGION=us-west-1
S3_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key  # 如果使用 IAM Role 可省略
AWS_SECRET_ACCESS_KEY=your-secret-key  # 如果使用 IAM Role 可省略
```

**生成 JWT Secret Key：**

```bash
python scripts/generate_jwt_secret.py
```

#### 3. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 初始化数据库（创建管理员账号）
python scripts/init_db.py

# 启动服务
uvicorn app.main:app --reload --port 8000
```

**默认管理员账号：**

- 邮箱：`admin@abc.com`
- 密码：`admin123`

#### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

## 🧠 RAG 架构详解

### 核心流程

```
用户问题
  ↓
【并行处理】Embedding 生成 + 关键词提取
  ↓
【向量检索】Qdrant 检索 Top 10（HNSW 算法，ef_search=128）
  ↓
【智能重排】GPT-4o-mini Rerank → Top 3
  ↓
【流式生成】GPT-4 实时返回答案（SSE）
  ↓
保存对话 + Token 统计
```

### 1. 文档处理与向量化

**文本分块**
- 块大小：1000 字符，重叠 200 字符
- 智能切分：优先在段落、句子边界
- 元数据：文件名、类型、上传时间、chunk 索引

**向量嵌入**
- 模型：OpenAI `text-embedding-3-small`（1536 维）
- 缓存：Redis 24h TTL
- 存储：Qdrant 向量数据库

### 2. 检索技术

**并行处理**
```python
# Embedding 生成 + 关键词提取同步执行
asyncio.gather(
    generate_embedding(question),
    extract_keywords(question, max_keywords=3)
)
```

**向量检索**
```python
# HNSW 算法，ef_search=128
qdrant_service.search(
    query_embedding=embedding,
    limit=10,
    score_threshold=0.5,
    ef_search=128
)
```

**Rerank 重排序**
```python
# GPT-4o-mini 从 10 个候选中选出最相关 3 个
reranked_docs = openai_service.rerank_documents(
    question=question,
    documents=top_10_docs,
    top_k=3
)
```

### 3. 检索策略

**向量相似度**
- 算法：HNSW（分层可导航小世界图）
- 阈值：动态调整（短问题 0.3，长问题 0.5）
- 降级：无结果时降至 0.2

**关键词增强**
- GPT-4o-mini 提取 3 个核心关键词
- 精确匹配 +15%，部分匹配 +10%

**去重排序**
- 内容去重（相似度 > 95%）
- 文件级去重（每文件最多 5 个片段）
- 综合排序（向量分数 + 关键词加成）

### 4. 答案生成

**模型**
- 主模型：GPT-4（生成答案）
- 辅助：GPT-4o-mini（提取关键词 + Rerank）
- 参数：temperature=0.7，max_context=2500 tokens

**流式输出**
- SSE 协议，逐 token 推送
- 实时显示，完成后返回来源文档

### 5. 性能指标

**响应时间**（典型查询）
- 并行处理：~1.0s
- 向量检索：~0.5s
- Rerank：~0.3s
- 答案生成：~0.7s
- **总计：~2.5s**

**准确度**
- 向量召回率：85-90%
- Rerank 后精准度：95%+
- 关键词增强覆盖：+20%

## 🏗️ 技术栈

### 后端
- **框架**：FastAPI（异步高性能）
- **ORM**：SQLAlchemy（支持 SQLite + PostgreSQL）
- **向量库**：Qdrant Cloud（HNSW 索引）
- **AI**：OpenAI GPT-4 + GPT-4o-mini + Embeddings
- **认证**：JWT + Bcrypt
- **缓存**：Redis（Embedding + 检索结果）
- **限流**：SlowAPI（100req/min 全局，30req/min 问答）
- **重试**：Tenacity（指数退避）
- **日志**：CloudWatch Logs

### 前端
- **框架**：Next.js 14（App Router）
- **语言**：TypeScript
- **样式**：TailwindCSS
- **状态管理**：Zustand
- **实时通信**：SSE（Server-Sent Events）

### 基础设施
- **开发环境**：SQLite + 本地文件存储
- **生产环境**：
  - **计算**：AWS ECS Fargate（Docker 容器）
  - **数据库**：AWS RDS PostgreSQL
  - **文件存储**：AWS S3（持久化存储）
  - **向量库**：Qdrant Cloud（独立部署）
  - **负载均衡**：AWS ALB
  - **配置管理**：AWS Secrets Manager
  - **前端部署**：Vercel（全球 CDN）
  - **CI/CD**：GitHub Actions

### 数据库设计
- **User**：用户信息（邮箱、密码哈希、角色）
- **Document**：文档元数据（文件 ID、名称、大小、上传者）
- **Conversation**：对话会话（用户 ID、标题）
- **Message**：消息记录（问题、答案、来源文档）
- **TokenUsage**：Token 使用统计（每日/每月配额）

## 🚢 部署指南

### AWS ECS 部署

**前置准备**
1. AWS 资源：ECS 集群、ECR 仓库、RDS PostgreSQL、ALB、S3 Bucket
2. AWS Secrets Manager 配置：
   - `knowledgehub/database-url` - PostgreSQL 连接字符串
   - `knowledgehub/openai-api-key` - OpenAI API 密钥
   - `knowledgehub/qdrant-url` - Qdrant 集群 URL
   - `knowledgehub/qdrant-api-key` - Qdrant API 密钥
   - `knowledgehub/jwt-secret` - JWT 密钥
   - `knowledgehub/frontend-url` - Vercel 域名
   - `knowledgehub/s3-bucket-name` - S3 Bucket 名称
   - `knowledgehub/aws-access-key` - (可选) AWS Access Key
   - `knowledgehub/aws-secret-key` - (可选) AWS Secret Key

**GitHub Actions 自动部署**
```bash
# 配置 GitHub Secrets
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY

# 推送到 main 分支自动部署
git push origin main
```

**初始化数据库**
```bash
aws ecs run-task \
  --cluster knowledgehub-cluster \
  --task-definition knowledgehub-backend \
  --overrides '{"containerOverrides":[{"name":"backend","command":["python","scripts/init_db.py"]}]}'
```

### Vercel 前端部署

1. 连接 GitHub 仓库到 Vercel
2. 配置环境变量：
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-api.com
   ```
3. Root Directory：`frontend`
4. 自动部署（推送触发）

## 📁 项目结构

```
abc-ai-knowledgehub/
├── backend/
│   ├── app/
│   │   ├── api/           # REST API 端点
│   │   ├── services/      # RAG、OpenAI、Qdrant 服务
│   │   ├── db/            # 数据库模型
│   │   ├── core/          # 配置和常量
│   │   └── utils/         # 工具函数
│   └── Dockerfile
├── frontend/
│   ├── app/               # Next.js 页面
│   ├── components/        # React 组件
│   └── lib/               # API 客户端
├── scripts/               # 工具脚本
└── .github/workflows/     # CI/CD
```


## 🎮 使用指南

**管理员**
- 登录管理后台（右上角按钮）
- 上传/管理文档
- 查看用户统计

**普通用户**
- 注册/登录账号
- 智能问答
- 查看来源文档


## 📝 License

MIT License
