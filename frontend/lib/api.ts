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

export interface RegisterRequest {
  email: string
  password: string
  full_name?: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface UserResponse {
  id: number
  email: string
  full_name?: string
  is_active: boolean
  created_at?: string
}

export interface ChatRequest {
  question: string
  conversation_id?: string
  max_tokens?: number
  temperature?: number
  locale?: string  // 用户语言
}

export interface ChatResponse {
  answer: string
  sources: Array<{
    content: string
    metadata: Record<string, any>
  }>
  conversation_id: string
  tokens_used?: number
}

export const authAPI = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/login', data)
    return response.data
  },
  register: async (data: RegisterRequest): Promise<UserResponse> => {
    const response = await apiClient.post<UserResponse>('/auth/register', data)
    return response.data
  },
  getMe: async (): Promise<UserResponse> => {
    const response = await apiClient.get<UserResponse>('/auth/me')
    return response.data
  },
}

export const chatAPI = {
  stream: async function* (data: ChatRequest): AsyncGenerator<{ content: string; done: boolean; sources?: any[]; conversation_id?: string; error?: boolean }> {
    const token = localStorage.getItem('access_token')
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    const response = await fetch(`${API_URL}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    
    if (!reader) {
      throw new Error('No reader available')
    }
    
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonStr = line.slice(6)
            if (jsonStr.trim()) {
              const parsed = JSON.parse(jsonStr)
              yield parsed
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e)
          }
        }
      }
    }
    
    if (buffer.startsWith('data: ')) {
      try {
        const jsonStr = buffer.slice(6)
        if (jsonStr.trim()) {
          const parsed = JSON.parse(jsonStr)
          yield parsed
        }
      } catch (e) {
        console.error('Failed to parse final SSE data:', e)
      }
    }
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
  preview: (fileId: string): string => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    return `${API_URL}/api/v1/documents/${fileId}/preview`
  },
  download: (fileId: string): string => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    return `${API_URL}/api/v1/documents/${fileId}/download`
  },
  delete: async (fileId: string) => {
    const response = await apiClient.delete(`/documents/${fileId}`)
    return response.data
  },
}

export interface Conversation {
  id: number
  conversation_id: string
  title?: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  role: string
  content: string
  sources?: string
  created_at: string
}

export const conversationsAPI = {
  list: async (): Promise<Conversation[]> => {
    const response = await apiClient.get<Conversation[]>('/conversations/')
    return response.data
  },
  getMessages: async (conversationId: string): Promise<Message[]> => {
    const response = await apiClient.get<Message[]>(`/conversations/${conversationId}/messages`)
    return response.data
  },
  delete: async (conversationId: string) => {
    const response = await apiClient.delete(`/conversations/${conversationId}`)
    return response.data
  },
}

export interface TokenUsageStats {
  daily_usage: number
  daily_limit: number
  daily_remaining: number
  monthly_usage: number
  monthly_limit: number
  monthly_remaining: number
}

export const tokenUsageAPI = {
  getStats: async (): Promise<TokenUsageStats> => {
    const response = await apiClient.get<TokenUsageStats>('/token-usage/stats')
    return response.data
  },
}

export default apiClient

