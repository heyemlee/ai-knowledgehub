/**
 * 管理员 API
 */
import axios from 'axios'
import { toast } from '@/components/Toast'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const adminClient = axios.create({
  baseURL: `${API_URL}/api/v1/admin`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
adminClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
adminClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/'
    } else if (error.response?.status === 403) {
      toast.error('需要管理员权限')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

// 类型定义
export interface AdminDocument {
  file_id: string
  filename: string
  file_type: string
  file_size: number
  upload_time: string
  chunks_count: number
  status: string
  user_id: number
}

export interface AdminUser {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  role: string
  created_at: string
}

export interface DocumentStats {
  total_documents: number
  total_size_bytes: number
  total_size_mb: number
  users_stats: Array<{
    user_id: number
    document_count: number
    total_size: number
  }>
}

export interface UserStats {
  total_users: number
  active_users: number
  inactive_users: number
  admin_users: number
  regular_users: number
}

// API 方法
export const adminApi = {
  // 获取所有文档
  getAllDocuments: async (): Promise<AdminDocument[]> => {
    const response = await adminClient.get('/documents')
    return response.data
  },

  // 获取文档统计
  getDocumentStats: async (): Promise<DocumentStats> => {
    const response = await adminClient.get('/documents/stats')
    return response.data
  },

  // 删除文档
  deleteDocument: async (fileId: string): Promise<void> => {
    await adminClient.delete(`/documents/${fileId}`)
  },

  // 获取所有用户
  getAllUsers: async (): Promise<AdminUser[]> => {
    const response = await adminClient.get('/users')
    return response.data
  },

  // 获取用户统计
  getUserStats: async (): Promise<UserStats> => {
    const response = await adminClient.get('/users/stats')
    return response.data
  },
}

// 注册码相关类型和 API - Token 计量
export interface RegistrationCode {
  id: number
  code: string
  description: string | null
  is_active: boolean
  token_quota: number | null  // Token 配额
  tokens_used: number  // 已使用的 tokens
  tokens_per_registration: number  // 每次注册消耗的 tokens
  created_by: number
  created_at: string
  updated_at: string
}


export interface RegistrationCodeCreate {
  code: string
  description?: string
  token_quota?: number  // Token 配额
  tokens_per_registration?: number  // 每次注册分配的 tokens，默认 800000 (月度配额)
}

export interface RegistrationCodeUpdate {
  description?: string
  is_active?: boolean
  token_quota?: number
}

const regCodeClient = axios.create({
  baseURL: `${API_URL}/api/v1/registration-codes`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
regCodeClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
regCodeClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/'
    } else if (error.response?.status === 403) {
      toast.error('需要管理员权限')
    }
    return Promise.reject(error)
  }
)

export const registrationCodeApi = {
  // 获取所有注册码
  getAll: async (): Promise<RegistrationCode[]> => {
    const response = await regCodeClient.get('/')
    return response.data
  },

  // 创建注册码
  create: async (data: RegistrationCodeCreate): Promise<RegistrationCode> => {
    const response = await regCodeClient.post('/', data)
    return response.data
  },

  // 更新注册码
  update: async (id: number, data: RegistrationCodeUpdate): Promise<RegistrationCode> => {
    const response = await regCodeClient.put(`/${id}`, data)
    return response.data
  },

  // 删除注册码
  delete: async (id: number): Promise<void> => {
    await regCodeClient.delete(`/${id}`)
  },
}








