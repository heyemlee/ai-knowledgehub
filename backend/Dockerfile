# 多阶段构建：构建阶段
FROM python:3.11-slim as builder

WORKDIR /build

# 安装构建依赖（包含 Pillow 所需的图像库）
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖到用户目录
RUN pip install --no-cache-dir --user -r requirements.txt

# 生产阶段
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖和 curl（用于健康检查）
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# 从构建阶段复制 Python 依赖
COPY --from=builder /root/.local /home/appuser/.local

# 设置 PATH 环境变量
ENV PATH=/home/appuser/.local/bin:$PATH

# 只复制 app 目录（核心修复！）
COPY --chown=appuser:appuser app ./app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000

# 设置环境变量
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 使用 Gunicorn + Uvicorn workers 启动（生产模式）
CMD gunicorn app.main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT} \
    --timeout 120 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output
