# Backend API - FastAPI

## 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 运行开发服务器

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 API 文档: http://localhost:8000/docs

## 环境变量

在项目根目录创建 `.env` 文件，配置必要的环境变量。

## Docker 部署

```bash
docker build -t abc-knowledgehub-backend .
docker run -p 8000:8000 --env-file .env abc-knowledgehub-backend
```

## API 端点

- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/register` - 用户注册（仅开发环境）
- `GET /api/v1/auth/me` - 获取当前用户信息
- `POST /api/v1/chat/ask` - 问答接口
- `POST /api/v1/chat/stream` - 流式问答接口
- `POST /api/v1/documents/upload` - 上传文档
- `GET /api/v1/documents/list` - 获取文档列表
- `DELETE /api/v1/documents/{file_id}` - 删除文档

