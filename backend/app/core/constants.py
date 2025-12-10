class SearchConfig:

    # 短查询判断阈值（字符数）
    SHORT_QUERY_THRESHOLD = 6
    
    # 短查询配置
    SHORT_QUERY_LIMIT = 20
    SHORT_QUERY_THRESHOLD_SCORE = 0.3
    
    # 普通查询配置
    NORMAL_QUERY_LIMIT = 10
    NORMAL_QUERY_THRESHOLD_SCORE = 0.5
    
    # 降级检索配置
    FALLBACK_THRESHOLD_SCORE = 0.2
    FALLBACK_LIMIT = 20
    
    # 无阈值检索配置
    NO_THRESHOLD_LIMIT = 30
    
    # 扩大检索倍数（用于关键词匹配）
    EXPANDED_SEARCH_MULTIPLIER = 3
    
    # 相似度提升配置
    EXACT_MATCH_BOOST = 0.15
    EXACT_MATCH_MAX_SCORE = 0.80
    KEYWORD_MATCH_BOOST = 0.10
    KEYWORD_MATCH_MAX_SCORE = 0.75


class DocumentParserConfig:
    # 文本切分默认配置
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_OVERLAP = 200
    
    # 切分位置判断阈值
    NEWLINE_THRESHOLD = 0.7  # 换行符位置阈值（70%）
    PUNCTUATION_THRESHOLD = 0.8  # 标点符号位置阈值（80%）
    SENTENCE_PUNCTUATION_THRESHOLD = 0.7  # 句子标点位置阈值（70%）
    MIN_SPLIT_RATIO = 0.5  # 最小切分比例（50%）
    
    # 结构化信息分隔符
    STRUCTURED_SEPARATORS = ['：', ':', '；', ';']
    SENTENCE_SEPARATORS = ['。', '！', '？', '.', '!', '?']


class AIConfig:
    # 关键词提取配置
    KEYWORD_EXTRACTION_TEMPERATURE = 0.3
    KEYWORD_EXTRACTION_MAX_TOKENS = 50
    KEYWORD_EXTRACTION_MAX_KEYWORDS = 3
    
    # 默认问答配置
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1000


class RerankConfig:
    # Rerank 功能配置
    ENABLE_RERANK = True  # 是否启用 Rerank
    INITIAL_RETRIEVAL_LIMIT = 10  # 初始检索数量
    FINAL_TOP_K = 3  # Rerank 后最终返回数量
    RERANK_MODEL = "gpt-4o-mini"  # 使用的 Rerank 模型
    RERANK_TEMPERATURE = 0.3  # Rerank 时的温度参数
    RERANK_MAX_TOKENS = 500  # Rerank 响应的最大 token 数


class QdrantConfig:
    # 默认检索配置
    DEFAULT_SEARCH_LIMIT = 5
    DEFAULT_SCORE_THRESHOLD = 0.6
    
    # HNSW 搜索参数优化
    HNSW_EF_SEARCH = 128
    
    # 删除操作限制
    MAX_DELETE_POINTS = 10000


class ProcessingConfig:
    # 文档去重配置
    MAX_CHUNKS_PER_FILE = 5
    MAX_CONTEXT_DOCS = 5  # 保留不包含关键词的文档数量


class RateLimitConfig:
    # 全局限流（每分钟请求数）
    GLOBAL_RATE_LIMIT = "100/minute"
    
    # 认证相关接口限流（防止暴力破解）
    AUTH_RATE_LIMIT = "5/minute"
    
    # 问答接口限流（AI 资源消耗大）
    CHAT_RATE_LIMIT = "30/minute"
    
    # 文档上传限流（文件处理消耗资源）
    UPLOAD_RATE_LIMIT = "10/minute"
    
    # 文档列表/预览限流
    DOCUMENT_RATE_LIMIT = "60/minute"
    
    # 限流错误消息
    RATE_LIMIT_MESSAGE = "请求过于频繁，请稍后再试"


class TokenLimitConfig:
    # 每个用户每日 token 限制（问答相关）
    DAILY_TOKEN_LIMIT_PER_USER = 100000  # 100K tokens/天
    
    # 每个用户每月 token 限制
    MONTHLY_TOKEN_LIMIT_PER_USER = 2000000  # 2M tokens/月
    
    # 单次请求最大 token 限制（防止异常大的请求）
    MAX_TOKENS_PER_REQUEST = 50000  # 50K tokens/次
    
    # Token 限制错误消息
    TOKEN_LIMIT_EXCEEDED_MESSAGE = "已达到 OpenAI Token 使用量限制，请稍后再试或联系管理员"


class FileValidationConfig:
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt', '.md'}
    
    # 允许的 MIME 类型
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'text/plain',
        'text/markdown',
    }
    
    # 文件大小限制（字节）
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    # 扩展名到 MIME 类型的映射
    EXTENSION_MIME_MAP = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
    }


class RetryConfig:
    # OpenAI API 重试配置
    OPENAI_MAX_ATTEMPTS = 3  # 最大重试次数
    OPENAI_MIN_WAIT = 2  # 最小等待时间（秒）
    OPENAI_MAX_WAIT = 60  # 最大等待时间（秒）
    
    # Qdrant 连接重试配置
    QDRANT_CONNECTION_MAX_ATTEMPTS = 5  # 连接重试最大次数
    QDRANT_CONNECTION_MIN_WAIT = 1  # 连接重试最小等待时间（秒）
    QDRANT_CONNECTION_MAX_WAIT = 30  # 连接重试最大等待时间（秒）
    
    # Qdrant 操作重试配置
    QDRANT_OPERATION_MAX_ATTEMPTS = 3  # 操作重试最大次数
    QDRANT_OPERATION_MIN_WAIT = 1  # 操作重试最小等待时间（秒）
    QDRANT_OPERATION_MAX_WAIT = 20  # 操作重试最大等待时间（秒）


class CacheConfig:
    # Embedding 缓存时间（秒）- 24小时，因为相同文本的embedding通常不变
    EMBEDDING_CACHE_TTL = 86400
    
    SEARCH_RESULT_CACHE_TTL = 3600
    
    ANSWER_CACHE_TTL = 1800
    
    ENABLE_CACHE = True
    
    EMBEDDING_CACHE_PREFIX = "embedding"
    SEARCH_CACHE_PREFIX = "search"
    ANSWER_CACHE_PREFIX = "answer"


class ImageConfig:
    """图片处理配置"""
    
    # 缩略图尺寸（宽, 高）
    THUMBNAIL_MAX_SIZE = (300, 300)
    
    # 智能缩略图生成阈值
    # 只有当原图满足以下条件时才生成缩略图：
    # 1. 尺寸大于缩略图尺寸
    # 2. 文件大小大于此阈值（KB）
    THUMBNAIL_SIZE_THRESHOLD_KB = 200  # 200KB
    
    # 缩略图 JPEG 质量（1-100）
    THUMBNAIL_JPEG_QUALITY = 85
    
    # 是否启用智能缩略图（False = 总是生成缩略图）
    ENABLE_SMART_THUMBNAIL = True

