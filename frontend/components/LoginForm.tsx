'use client'

import { useState } from 'react'
import { useAuthStore } from '@/store/authStore'

export default function LoginForm() {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const login = useAuthStore((state) => state.login)
  const register = useAuthStore((state) => state.register)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isRegister) {
        await register(email, password, fullName || undefined)
      } else {
        await login(email, password)
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 
        (isRegister ? '注册失败，请检查输入信息' : '登录失败，请检查邮箱和密码')
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-lg">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-800">
          ABC AI Knowledge Hub
        </h1>
        <h2 className="text-xl font-semibold text-center mb-6 text-gray-600">
          企业知识库系统
        </h2>

        {/* 登录/注册切换 */}
        <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
          <button
            type="button"
            onClick={() => {
              setIsRegister(false)
              setError('')
            }}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              !isRegister
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            登录
          </button>
          <button
            type="button"
            onClick={() => {
              setIsRegister(true)
              setError('')
            }}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              isRegister
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            注册
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded">
              {error}
            </div>
          )}

          {isRegister && (
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 mb-2">
                姓名（可选）
              </label>
              <input
                id="fullName"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="您的姓名"
              />
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
              邮箱
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="your@email.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
              密码
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (isRegister ? '注册中...' : '登录中...') : (isRegister ? '注册' : '登录')}
          </button>
        </form>

        {!isRegister && (
          <div className="mt-6 text-center text-sm text-gray-500">
            <p>默认账号: admin@abc.com / admin123</p>
          </div>
        )}
      </div>
    </div>
  )
}

