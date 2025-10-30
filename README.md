# ABC AI Knowledge Hub

企业级知识库系统 - 基于 OpenAI 大语言模型的智能问答平台

## 📋 项目概述

构建一个基于 OpenAI 大语言模型的企业级知识库系统，实现员工通过网页端（Next.js）访问公司内部知识内容，AI 根据企业资料和语义检索自动生成高质量答案。

## 🏗️ 技术栈

### 前端
- **框架**: Next.js 14 (React + Server Components)
- **UI**: TailwindCSS + shadcn/ui
- **状态管理**: Zustand
- **HTTP客户端**: Axios
- **部署**: Vercel

### 后端
- **框架**: FastAPI (Python)
- **向量数据库**: Qdrant Cloud
- **模型服务**: OpenAI API (GPT-4-Turbo / GPT-3.5-Turbo)
- **存储**: AWS S3
- **部署**: AWS EC2

### 基础设施
- **云平台**: AWS (EC2 + S3 + Route53 + CloudWatch)
- **认证**: JWT / AWS Cognito
- **安全**: HTTPS (ACM证书)

## 📁 项目结构

```
abc-ai-knowledgehub/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   └── utils/          # 工具函数
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # Next.js 前端
│   ├── app/                # Next.js App Router
│   ├── components/         # React 组件
│   ├── lib/                # 工具库
│   ├── public/             # 静态资源
│   └── package.json
├── .env.example            # 环境变量示例
├── .gitignore
└── README.md
```

## 🚀 快速开始

### 1. 环境配置

在项目根目录创建 `.env` 文件，参考以下配置：

```bash
# Mode: development | production
MODE=development

# Backend API
BACKEND_URL=http://localhost:8000
API_PREFIX=/api/v1

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Qdrant Configuration
QDRANT_URL=your_qdrant_cloud_url
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION_NAME=knowledge_base

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
S3_BUCKET_NAME=abc-knowledgehub-documents

# JWT Configuration
JWT_SECRET_KEY=your_jwt_secret_key_change_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000

# Logging
LOG_LEVEL=INFO
```

**注意**: 生产环境请确保 `MODE=production` 并配置正确的密钥和 URL。

### 2. 后端启动

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 前端启动

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

## 🔧 开发模式

项目使用 `MODE` 环境变量区分开发/生产模式：

- `MODE=development`: 开发模式，启用调试日志，使用本地服务
- `MODE=production`: 生产模式，优化配置，使用生产服务

## 📝 功能模块

- ✅ 用户认证（JWT）
- ✅ 知识库检索（RAG）
- ✅ AI 问答生成
- ✅ 文档上传与管理
- ✅ 向量存储与检索
- ✅ 日志监控

## 🔒 安全特性

- HTTPS 全站加密
- JWT 用户认证
- API Key 限制
- CORS 安全配置
- S3 权限控制
- CloudWatch 日志监控

## 📚 开发文档

详细开发需求请参考 `development.txt`

## 📄 License

Private - Internal Use Only

