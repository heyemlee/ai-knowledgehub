# ABC AI Knowledge Hub

企业级 AI 知识库系统 - 基于 RAG 技术的智能问答平台

## ✨ 核心特性

- 🤖 **智能问答** - 基于 OpenAI GPT-4 和 RAG 技术的精准回答
- 📄 **文档管理** - 支持 PDF、Word、Excel、TXT、Markdown 等多种格式
- 👥 **用户管理** - JWT 认证 + 角色权限（管理员/普通用户）
- 🎛️ **管理后台** - 可视化管理文档和用户
- 📊 **统计分析** - Token 使用统计和对话历史
- 🔐 **安全可靠** - API Key 加密存储 + 请求限流

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- OpenAI API Key
- Qdrant Cloud 账号（免费）

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

#### 5. 上传文档

使用管理后台上传文档（点击右上角"管理后台"按钮）。

## 🚢 AWS 云端部署

### 前置准备

1. **AWS 资源** - ECS 集群、ECR 仓库、RDS PostgreSQL、ALB 等（参考 [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md)）
2. **AWS Secrets Manager** - 配置以下 secrets：
   - `knowledgehub/database-url` - PostgreSQL 连接字符串
   - `knowledgehub/openai-api-key` - OpenAI API 密钥
   - `knowledgehub/qdrant-url` - Qdrant 集群 URL
   - `knowledgehub/qdrant-api-key` - Qdrant API 密钥
   - `knowledgehub/jwt-secret` - JWT 密钥（使用 `python scripts/generate_jwt_secret.py` 生成）
   - `knowledgehub/frontend-url` - 前端域名（Vercel 部署后填入，例如：`https://your-project.vercel.app`）
   - `knowledgehub/backend-url` - 后端 API 域名（ALB 地址）

参考 `aws.env.example` 了解完整配置。

> **注意：** 如果前端部署在 Vercel，`knowledgehub/frontend-url` 应设置为 Vercel 提供的域名，以确保 CORS 配置正确。

### GitHub Actions 自动部署

项目已配置 GitHub Actions 工作流，推送到 `main` 分支时自动部署到 AWS ECS。

#### 配置 GitHub Secrets

在 GitHub 仓库设置中添加以下 Secrets：

- `AWS_ACCESS_KEY_ID` - AWS 访问密钥 ID
- `AWS_SECRET_ACCESS_KEY` - AWS 访问密钥

#### 工作流说明

- **触发条件**：推送到 `main` 分支
- **部署流程**：
  1. 构建 Docker 镜像
  2. 推送到 Amazon ECR
  3. 更新 ECS 服务（强制新部署）
  4. 验证服务状态

#### 手动部署

如需手动部署，可使用部署脚本：

```bash
./scripts/deploy-to-aws.sh build    # 构建并推送镜像
./scripts/deploy-to-aws.sh deploy   # 触发 ECS 部署
./scripts/deploy-to-aws.sh all      # 执行完整流程
```

### 初始化数据库

部署后需要初始化数据库（创建管理员账号）：

```bash
# 通过 ECS 任务运行初始化脚本
aws ecs run-task \
  --cluster knowledgehub-cluster \
  --task-definition knowledgehub-backend \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --overrides '{
    "containerOverrides": [{
      "name": "backend",
      "command": ["python", "scripts/init_db.py"]
    }]
  }'
```

详细部署指南请参考 [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md)

## 🌐 Vercel 前端部署

### 前置准备

1. **Vercel 账号** - 注册 [Vercel](https://vercel.com) 账号（免费）
2. **GitHub 仓库** - 确保前端代码已推送到 GitHub
3. **AWS 后端已部署** - 确保后端 API 已在 AWS 上正常运行

### 部署步骤

#### 1. 连接 GitHub 仓库到 Vercel

1. 登录 [Vercel Dashboard](https://vercel.com/dashboard)
2. 点击 **"Add New Project"**
3. 选择你的 GitHub 仓库
4. 配置项目设置：
   - **Framework Preset:** Next.js
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`（自动检测）
   - **Output Directory:** `.next`（自动检测）

#### 2. 配置环境变量

在 Vercel 项目设置中添加以下环境变量：

**必需配置：**

- `NEXT_PUBLIC_API_URL` - AWS 后端 API 地址（例如：`https://api.yourdomain.com`）

**可选配置：**

- `NEXT_PUBLIC_MODE` - 运行模式（`production`）

**配置步骤：**

1. 在 Vercel 项目页面，进入 **Settings** → **Environment Variables**
2. 添加环境变量：
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-api-domain.com
   ```
3. 选择环境（Production、Preview、Development）
4. 点击 **Save**

#### 3. 部署

1. 点击 **Deploy** 按钮
2. Vercel 会自动构建并部署前端应用
3. 部署完成后，Vercel 会提供一个域名（例如：`your-project.vercel.app`）

#### 4. 配置 AWS 后端 CORS

确保 AWS 后端的 CORS 配置允许 Vercel 域名访问：

1. **更新 AWS Secrets Manager** 中的 `knowledgehub/frontend-url`：

   ```bash
   aws secretsmanager update-secret \
     --secret-id knowledgehub/frontend-url \
     --secret-string "https://your-project.vercel.app" \
     --region us-west-1
   ```

2. **重启 ECS 服务** 使配置生效：
   ```bash
   aws ecs update-service \
     --cluster knowledgehub-cluster \
     --service knowledgehub-task-service-4vffj6ar \
     --force-new-deployment \
     --region us-west-1
   ```

#### 5. 自定义域名（可选）

1. 在 Vercel 项目页面，进入 **Settings** → **Domains**
2. 添加你的自定义域名（例如：`app.yourdomain.com`）
3. 按照提示配置 DNS 记录
4. 更新 `NEXT_PUBLIC_API_URL` 和 AWS Secrets Manager 中的 `frontend-url` 为新域名



### 部署架构

```
GitHub Repository
  ↓ (Push to main)
Vercel CI/CD
  ├── 自动构建 Next.js
  ├── 部署到 Vercel Edge Network
  └── 提供 HTTPS 域名
  ↓
用户浏览器
  ↓ (API 请求)
AWS ALB → ECS Fargate (后端 API)
```

## 🏗️ 技术栈

### 后端

- **FastAPI** - 现代化 Python Web 框架
- **SQLAlchemy** - 异步 ORM（支持 SQLite/PostgreSQL）
- **Qdrant** - 向量数据库
- **OpenAI** - GPT-4 + Embeddings
- **JWT** - 用户认证

### 前端

- **Next.js 14** - React 框架
- **TypeScript** - 类型安全
- **TailwindCSS** - 样式框架
- **Zustand** - 状态管理

### 存储

- **SQLite** - 开发环境数据库
- **PostgreSQL** - 生产环境数据库（AWS RDS）
- **本地文件存储** - 开发环境文档存储
- **S3/EFS** - AWS 生产环境文件存储

## 📁 项目结构

```
abc-ai-knowledgehub/
├── backend/                 # 后端 API
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── db/             # 数据库模型
│   │   ├── services/       # 业务服务
│   │   └── utils/          # 工具函数
│   └── Dockerfile          # Docker 镜像定义
├── frontend/               # 前端应用
│   ├── app/               # Next.js App Router
│   ├── components/        # React 组件
│   └── lib/               # 工具库
├── scripts/               # 工具脚本
│   ├── init_db.py         # 初始化数据库
│   ├── generate_jwt_secret.py # 生成JWT密钥
│   └── deploy-to-aws.sh   # AWS部署脚本
├── aws/                   # AWS 配置
│   └── task-definition.json # ECS 任务定义
└── .github/workflows/     # GitHub Actions
    └── deploy.yml         # 自动部署工作流
```

## 🛠️ 常用脚本

```bash
# 生成 JWT 密钥
python scripts/generate_jwt_secret.py

# 初始化数据库（创建管理员）
python scripts/init_db.py

# 检查知识库状态
python scripts/check_knowledge_base.py

# 重置 Qdrant 向量库
python scripts/reset_qdrant_collection.py
```

## 🎮 使用指南

### 管理员功能

1. **登录管理后台** - 点击聊天界面右上角"管理后台"按钮
2. **文档管理** - 上传、查看、搜索、删除文档
3. **用户管理** - 查看所有注册用户和统计信息

### 普通用户功能

1. **注册/登录** - 开发环境支持用户注册，生产环境需管理员邀请
2. **智能问答** - 输入问题，AI 基于知识库回答，查看相关文档来源

## 🔐 安全配置

### 生产环境必须配置

1. **JWT Secret Key** - 使用 `python scripts/generate_jwt_secret.py` 生成强随机密钥
2. **环境变量保护** - 永远不要提交 `.env` 文件到 Git
3. **数据库安全** - 生产环境使用 PostgreSQL，启用 SSL 连接
4. **AWS Secrets Manager** - 使用 AWS Secrets Manager 存储敏感信息，不要硬编码

## 📝 License

MIT License
