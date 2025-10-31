# ABC AI Knowledge Hub

企业级知识库系统 - 基于 OpenAI 大语言模型的智能问答平台

## 🚀 快速开始

### 环境配置

复制 `.env.example` 文件并重命名为 `.env`，然后填入你的配置信息：

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥和配置
```

### 启动服务

**后端**:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**前端**:

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

### 导入文档

```bash
# 1. 将文档放入 documents/ 目录
# 2. 运行批量导入脚本
python scripts/batch_import.py
```

## 📁 项目结构

```
abc-ai-knowledgehub/
├── backend/          # FastAPI 后端
├── frontend/         # Next.js 前端
├── documents/        # 文档目录（不会被git跟踪）
└── scripts/          # 工具脚本
```

## 🔧 技术栈

- **后端**: FastAPI + Python 3.11
- **前端**: Next.js 14 + TypeScript + TailwindCSS
- **向量数据库**: Qdrant Cloud
- **AI模型**: OpenAI GPT-4-Turbo + Embeddings
- **存储**: AWS S3
- **缓存**: Redis（可选）

## 📚 主要功能

- ✅ 用户认证（JWT）
- ✅ 文档上传与管理
- ✅ RAG 智能问答
- ✅ 对话历史记录
- ✅ Token 使用统计
- ✅ API Key 加密管理

## 📖 详细文档

- [架构文档](./ARCHITECTURE.md) - 代码组织架构详解
- [安全审计](./SECURITY_AUDIT.md) - 安全检查报告
- [开发指南](./SECURITY.md) - 安全功能说明

## 📄 License

Private - Internal Use Only
