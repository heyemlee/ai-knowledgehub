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

```bash
# 复制环境变量模板
cp railway.env.example .env

# 编辑 .env 文件，填入必需的配置
# - OPENAI_API_KEY: OpenAI API 密钥
# - QDRANT_URL: Qdrant Cloud URL
# - QDRANT_API_KEY: Qdrant API Key
# - JWT_SECRET_KEY: 使用 python scripts/generate_jwt_secret.py 生成
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

默认管理员账号：

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

- **本地文件存储** - 文档持久化（支持 Railway Volumes）
- **SQLite** - 开发环境数据库
- **PostgreSQL** - 生产环境数据库（Railway 自动配置）

## 📁 项目结构

```
abc-ai-knowledgehub/
├── backend/                 # 后端 API
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置
│   │   ├── db/             # 数据库模型
│   │   ├── models/         # Pydantic 模型
│   │   ├── services/       # 业务服务
│   │   └── utils/          # 工具函数
│   ├── storage/            # 本地文件存储
│   └── requirements.txt
├── frontend/               # 前端应用
│   ├── app/               # Next.js App Router
│   ├── components/        # React 组件
│   ├── lib/               # 工具库
│   └── store/             # 状态管理
├── scripts/               # 工具脚本
│   ├── init_db.py         # 初始化数据库
│   ├── check_knowledge_base.py # 检查知识库
│   ├── generate_jwt_secret.py # 生成JWT密钥
│   └── reset_qdrant_collection.py # 重置Qdrant集合
└── .env                   # 环境变量（需创建）
```

## 🎮 使用指南

### 管理员功能

1. **登录管理后台** - 点击聊天界面右上角"管理后台"按钮
2. **文档管理** - 上传、查看、搜索、删除文档
3. **用户管理** - 查看所有注册用户和统计信息

### 普通用户功能

1. **注册/登录** - 开发环境支持用户注册，生产环境需管理员邀请
2. **智能问答** - 输入问题，AI 基于知识库回答，查看相关文档来源

## 🚢 部署到 Railway

### 一键部署

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)

### 手动部署步骤

1. **创建 Railway 项目** - 注册账号并连接 GitHub 仓库
2. **添加 PostgreSQL 服务** - Railway 会自动配置 `DATABASE_URL`
3. **配置环境变量** - 设置 `MODE`, `OPENAI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `JWT_SECRET_KEY`
4. **配置 Volume** - 挂载路径 `/app/backend/storage`，大小 5GB+
5. **初始化数据库** - 在 Railway Shell 中运行 `cd backend && python scripts/init_db.py`
6. **部署前端** - 推荐使用 Vercel，配置环境变量 `NEXT_PUBLIC_API_URL`

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

## 🔐 安全配置

### 生产环境必须配置

1. **JWT Secret Key** - 使用 `python scripts/generate_jwt_secret.py` 生成强随机密钥
2. **环境变量保护** - 永远不要提交 `.env` 文件到 Git
3. **数据库安全** - 生产环境使用 PostgreSQL，启用 SSL 连接

## 📚 详细文档

- [架构文档](./ARCHITECTURE.md) - 详细的技术架构说明
- [待办事项](./TODO.md) - 功能清单和开发计划

## 📝 License

MIT License
