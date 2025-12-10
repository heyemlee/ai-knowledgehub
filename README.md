# AI Knowledge Hub

AI Knowledge Base System - An intelligent Q&A platform based on RAG (Retrieval Augmented Generation) technology

## ✨ Core Features

- 🤖 **High-Performance RAG Engine** - Parallel processing + Rerank + Vector optimization for precision and speed
- 🖼️ **Text and Image Response Support** - Intelligent image retrieval for rich text-image answers
- 🎯 **Smart Retrieval** - Vector similarity + Keyword matching + GPT-4o-mini reranking
- 👥 **Permissions** - JWT authentication + Role management + Token quotas
- 📊 **Data Analytics** - Token usage statistics + Conversation history tracking
- 🔐 **Production-Grade Security** - Rate limiting + Encrypted storage + CORS protection


## 🚀 Quick Start

### Local Development

#### 1. Clone the Project

```bash
git clone <repository-url>
cd abc-ai-knowledgehub
```

#### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Required Configuration
OPENAI_API_KEY=sk-your-openai-api-key
QDRANT_URL=https://your-cluster-id.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
JWT_SECRET_KEY=$(python scripts/generate_jwt_secret.py)

# Optional Configuration (development environment uses defaults)
MODE=development
DATABASE_URL=sqlite+aiosqlite:///./knowledgehub.db  # Development environment defaults to SQLite
FRONTEND_URL=http://localhost:3000

# S3 Storage Configuration (required for production)
STORAGE_TYPE=s3  # local or s3
AWS_REGION=us-west-1
S3_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key  # Can be omitted if using IAM Role
AWS_SECRET_ACCESS_KEY=your-secret-key  # Can be omitted if using IAM Role
```

**Generate JWT Secret Key:**

```bash
python scripts/generate_jwt_secret.py
```

#### 3. Start Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Initialize database (create admin account)
python scripts/init_db.py

# Start service
uvicorn app.main:app --reload --port 8000
```

**Default Admin Account:**

- Email: `admin@abc.com`
- Password: `admin123`

#### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000

## 🧠 RAG Architecture Details

### Core Workflow

```
User Question
  ↓
【Parallel Processing】Embedding Generation + Keyword Extraction
  ↓
【Vector Retrieval】Qdrant retrieves Top 10 (HNSW algorithm, ef_search=128)
  ↓
【Smart Reranking】GPT-4o-mini Rerank → Top 3
  ↓
【Streaming Generation】GPT-4 real-time answer streaming (SSE)
  ↓
Save conversation + Token statistics
```

### 1. Document Processing and Vectorization

**Text Chunking**
- Chunk size: 1000 characters, overlap 200 characters
- Smart splitting: Prioritizes paragraph and sentence boundaries
- Metadata: Filename, type, upload time, chunk index

**Vector Embedding**
- Model: OpenAI `text-embedding-3-small` (1536 dimensions)
- Cache: Redis 24h TTL
- Storage: Qdrant vector database

### 2. Retrieval Technology

**Parallel Processing**
```python
# Embedding generation + Keyword extraction executed in parallel
asyncio.gather(
    generate_embedding(question),
    extract_keywords(question, max_keywords=3)
)
```

**Vector Retrieval**
```python
# HNSW algorithm, ef_search=128
qdrant_service.search(
    query_embedding=embedding,
    limit=10,
    score_threshold=0.5,
    ef_search=128
)
```

**Rerank Reordering**
```python
# GPT-4o-mini selects the most relevant 3 from 10 candidates
reranked_docs = openai_service.rerank_documents(
    question=question,
    documents=top_10_docs,
    top_k=3
)
```

### 3. Retrieval Strategy

**Vector Similarity**
- Algorithm: HNSW (Hierarchical Navigable Small World)
- Threshold: Dynamic adjustment (short questions 0.3, long questions 0.5)
- Fallback:降级 to 0.2 when no results

**Keyword Enhancement**
- GPT-4o-mini extracts 3 core keywords
- Exact match +15%, partial match +10%

**Deduplication and Sorting**
- Content deduplication (similarity > 95%)
- File-level deduplication (max 5 segments per file)
- Comprehensive sorting (vector score + keyword bonus)

### 4. Answer Generation

**Model**
- Main model: GPT-4 (answer generation)
- Auxiliary: GPT-4o-mini (keyword extraction + Rerank)
- Parameters: temperature=0.7, max_context=2500 tokens

**Streaming Output**
- SSE protocol, token-by-token streaming
- Real-time display, source documents returned upon completion

### 5. Performance Metrics

**Response Time** (typical query)
- Parallel processing: ~1.0s
- Vector retrieval: ~0.5s
- Rerank: ~0.3s
- Answer generation: ~0.7s
- **Total: ~2.5s**

**Accuracy**
- Vector recall: 85-90%
- Post-Rerank precision: 95%+
- Keyword enhancement coverage: +20%

## 🏗️ Technology Stack

### Backend
- **Framework**: FastAPI (async high-performance)
- **ORM**: SQLAlchemy (supports SQLite + PostgreSQL)
- **Vector DB**: Qdrant Cloud (HNSW index)
- **AI**: OpenAI GPT-4 + GPT-4o-mini + Embeddings
- **Authentication**: JWT + Bcrypt
- **Cache**: Redis (Embedding + retrieval results)
- **Rate Limiting**: SlowAPI (100req/min global, 30req/min Q&A)
- **Retry**: Tenacity (exponential backoff)
- **Logging**: CloudWatch Logs

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS
- **State Management**: Zustand
- **Real-time Communication**: SSE (Server-Sent Events)

### Infrastructure
- **Development Environment**: SQLite + Local file storage
- **Production Environment**:
  - **Compute**: AWS ECS Fargate (Docker containers)
  - **Database**: AWS RDS PostgreSQL
  - **File Storage**: AWS S3 (persistent storage)
  - **Vector DB**: Qdrant Cloud (independent deployment)
  - **Load Balancing**: AWS ALB
  - **Configuration Management**: AWS Secrets Manager
  - **Frontend Deployment**: Vercel (global CDN)
  - **CI/CD**: GitHub Actions

### Database Design
- **User**: User information (email, password hash, role)
- **Document**: Document metadata (file ID, name, size, uploader)
- **Conversation**: Conversation sessions (user ID, title)
- **Message**: Message records (question, answer, source documents)
- **TokenUsage**: Token usage statistics (daily/monthly quotas)

## 🚢 Deployment Guide

### AWS ECS Deployment

**Prerequisites**
1. AWS Resources: ECS cluster, ECR repository, RDS PostgreSQL, ALB, S3 Bucket
2. AWS Secrets Manager configuration:
   - `knowledgehub/database-url` - PostgreSQL connection string
   - `knowledgehub/openai-api-key` - OpenAI API key
   - `knowledgehub/qdrant-url` - Qdrant cluster URL
   - `knowledgehub/qdrant-api-key` - Qdrant API key
   - `knowledgehub/jwt-secret` - JWT secret
   - `knowledgehub/frontend-url` - Vercel domain
   - `knowledgehub/s3-bucket-name` - S3 Bucket name
   - `knowledgehub/aws-access-key` - (Optional) AWS Access Key
   - `knowledgehub/aws-secret-key` - (Optional) AWS Secret Key

**GitHub Actions Auto Deployment**
```bash
# Configure GitHub Secrets
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY

# Push to main branch for auto deployment
git push origin main
```

**Initialize Database**
```bash
aws ecs run-task \
  --cluster knowledgehub-cluster \
  --task-definition knowledgehub-backend \
  --overrides '{"containerOverrides":[{"name":"backend","command":["python","scripts/init_db.py"]}]}'
```

### Vercel Frontend Deployment

1. Connect GitHub repository to Vercel
2. Configure environment variables:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-api.com
   ```
3. Root Directory: `frontend`
4. Auto deployment (triggered by push)

## 📁 Project Structure

```
abc-ai-knowledgehub/
├── backend/
│   ├── app/
│   │   ├── api/           # REST API endpoints
│   │   ├── services/      # RAG, OpenAI, Qdrant services
│   │   ├── db/            # Database models
│   │   ├── core/          # Configuration and constants
│   │   └── utils/         # Utility functions
│   └── Dockerfile
├── frontend/
│   ├── app/               # Next.js pages
│   ├── components/        # React components
│   └── lib/               # API client
├── scripts/               # Utility scripts
└── .github/workflows/     # CI/CD
```


## 🎮 User Guide

**Administrator**
- Login to admin panel (top right button)
- Upload/manage documents
- Upload/manage images (with tags and descriptions)
- View user statistics

**Regular User**
- Register/login account
- Intelligent Q&A (supports text-image answers)
- View source documents and related images


## 📝 License

MIT License
