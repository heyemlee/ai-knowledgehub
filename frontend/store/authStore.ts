/**
 * 认证状态管理 (Zustand)
 */
import { create } from 'zustand'
import { authAPI } from '@/lib/api'

interface User {
  id: number
  email: string
  full_name?: string
  is_active: boolean
}

interface AuthState {
  isAuthenticated: boolean
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  checkAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  user: null,
  token: null,

  login: async (email: string, password: string) => {
    try {
      const response = await authAPI.login({ email, password })
      localStorage.setItem('access_token', response.access_token)
      
      // 获取用户信息
      const userData = await authAPI.getMe()
      
      set({
        isAuthenticated: true,
        user: userData,
        token: response.access_token,
      })
    } catch (error) {
      throw error
    }
  },

  register: async (email: string, password: string, fullName?: string) => {
    try {
      await authAPI.register({ email, password, full_name: fullName })
      // 注册成功后自动登录
      await useAuthStore.getState().login(email, password)
    } catch (error) {
      throw error
    }
  },

  logout: () => {
    localStorage.removeItem('access_token')
    set({
      isAuthenticated: false,
      user: null,
      token: null,
    })
  },

  checkAuth: () => {
    const token = localStorage.getItem('access_token')
    if (token) {
      // 验证 token 并获取用户信息
      authAPI.getMe()
        .then((userData) => {
          set({
            isAuthenticated: true,
            user: userData,
            token,
          })
        })
        .catch(() => {
          localStorage.removeItem('access_token')
          set({
            isAuthenticated: false,
            user: null,
            token: null,
          })
        })
    } else {
      set({
        isAuthenticated: false,
        user: null,
        token: null,
      })
    }
  },
}))

