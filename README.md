# ABC AI Knowledge Hub

企业级 AI 知识库系统 - 基于 RAG 技术的智能问答平台

## ✨ 核心特性

- 🤖 **智能问答** - 基于 OpenAI GPT-4 和 RAG 技术的精准回答
- 📄 **文档管理** - 支持 PDF、Word、Excel、TXT 等多种格式
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
cp .env.example .env

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

#### 5. 导入文档（可选）

使用管理后台上传，或批量导入：

```bash
# 将文档放入 documents/ 目录
# 运行批量导入脚本
python scripts/batch_import.py
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
│   ├── batch_import.py    # 批量导入文档
│   ├── update_documents.py # 更新文档
│   ├── init_db.py         # 初始化数据库
│   └── check_knowledge_base.py # 检查知识库
├── documents/             # 文档目录（本地）
└── .env                   # 环境变量（需创建）
```

## 🎮 使用指南

### 管理员功能

1. **登录管理后台**

   - 点击聊天界面右上角"管理后台"按钮
   - 或直接访问 `/admin`

2. **文档管理**

   - 上传新文档（支持拖拽）
   - 查看所有文档列表
   - 搜索和删除文档
   - 查看文档统计

3. **用户管理**
   - 查看所有注册用户
   - 查看用户统计信息

### 普通用户功能

1. **注册/登录**

   - 开发环境：支持用户注册
   - 生产环境：仅管理员邀请

2. **智能问答**
   - 输入问题，AI 基于知识库回答
   - 查看相关文档来源
   - 保存对话历史

## 🚢 部署到 Railway

### 一键部署

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)

### 手动部署步骤

1. **创建 Railway 项目**

   - 注册 [Railway](https://railway.app) 账号
   - 连接 GitHub 仓库

2. **添加 PostgreSQL 服务**

   - Railway 会自动配置 `DATABASE_URL`

3. **配置环境变量**

   ```env
   # 必需配置
   MODE=production
   OPENAI_API_KEY=your-openai-key
   QDRANT_URL=your-qdrant-url
   QDRANT_API_KEY=your-qdrant-key
   JWT_SECRET_KEY=your-generated-secret

   # PostgreSQL（自动配置）
   DATABASE_URL=${DATABASE_URL}
   ```

4. **配置 Volume（持久化存储）**

   - 挂载路径：`/app/backend/storage`
   - 大小：5GB+

5. **初始化数据库**

   - Railway 部署后，在 Railway Shell 中运行：

   ```bash
   cd backend && python scripts/init_db.py
   ```

6. **部署前端**
   - 推荐使用 Vercel 部署前端
   - 配置环境变量 `NEXT_PUBLIC_API_URL`

## 🛠️ 常用脚本

```bash
# 生成 JWT 密钥
python scripts/generate_jwt_secret.py

# 初始化数据库（创建管理员）
python scripts/init_db.py

# 批量导入文档
python scripts/batch_import.py

# 更新指定文档
python scripts/update_documents.py --file "document.pdf"

# 检查知识库状态
python scripts/check_knowledge_base.py

# 重置 Qdrant 向量库
python scripts/reset_qdrant_collection.py
```

## 🔐 安全配置

### 生产环境必须配置

1. **JWT Secret Key**

   ```bash
   python scripts/generate_jwt_secret.py
   # 复制输出的密钥到 .env 的 JWT_SECRET_KEY
   ```

2. **环境变量保护**

   - 永远不要提交 `.env` 文件到 Git
   - 使用强密码和复杂密钥
   - 定期轮换 API Keys

3. **数据库安全**
   - 生产环境使用 PostgreSQL
   - 启用 SSL 连接
   - 限制数据库访问权限