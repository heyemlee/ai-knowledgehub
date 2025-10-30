/**
 * API 客户端
 */
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 - 添加 token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 处理错误
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token 过期，清除本地存储
      localStorage.removeItem('access_token')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface ChatRequest {
  question: string
  conversation_id?: string
  max_tokens?: number
  temperature?: number
}

export interface ChatResponse {
  answer: string
  sources: Array<{
    content: string
    metadata: Record<string, any>
    score: number
  }>
  conversation_id: string
  tokens_used?: number
}

export const authAPI = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/login', data)
    return response.data
  },
  register: async (data: LoginRequest) => {
    const response = await apiClient.post('/auth/register', data)
    return response.data
  },
  getMe: async () => {
    const response = await apiClient.get('/auth/me')
    return response.data
  },
}

export const chatAPI = {
  ask: async (data: ChatRequest): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>('/chat/ask', data)
    return response.data
  },
  stream: async (data: ChatRequest) => {
    const response = await apiClient.post('/chat/stream', data, {
      responseType: 'stream',
    })
    return response.data
  },
}

export const documentsAPI = {
  upload: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
  list: async () => {
    const response = await apiClient.get('/documents/list')
    return response.data
  },
  delete: async (fileId: string) => {
    const response = await apiClient.delete(`/documents/${fileId}`)
    return response.data
  },
}

export default apiClient

