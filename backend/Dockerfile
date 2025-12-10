# ---------- 构建阶段 ----------
FROM python:3.11-slim as builder

WORKDIR /build

RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt


# ---------- 运行阶段 ----------
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN useradd -m -u 1000 appuser

COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# ---- 复制项目文件 ----
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser storage ./storage
COPY --chown=appuser:appuser scripts ./scripts
COPY --chown=appuser:appuser requirements.txt ./requirements.txt

# ---- storage 权限 ----
RUN chown -R appuser:appuser /app/storage

USER appuser

EXPOSE 8000

# ---- 环境变量（关键！）----
ENV MODE=production
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "app.main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120"]
