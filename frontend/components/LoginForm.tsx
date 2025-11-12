'use client'

import { useState } from 'react'
import { useAuthStore } from '@/store/authStore'
import { useTranslations } from '@/lib/translations'

export default function LoginForm() {
  const { t } = useTranslations()
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
      console.error('认证错误:', err)
      
      let errorMessage = isRegister ? t('login.registerFailed') : t('login.loginFailed')
      
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail
        
        if (Array.isArray(detail)) {
          errorMessage = detail.map((item: any) => {
            const field = item.loc?.[1] || 'field'
            const msg = item.msg || t('login.validationFailed')
            return `${field}: ${msg}`
          }).join(', ')
        } 
        else if (typeof detail === 'string') {
          errorMessage = detail
        }
        else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail)
        }
      }
      
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-white p-4">
      <div className="w-full max-w-md">
        {/* Logo 和标题 */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold mb-3 text-black">
            ABC AI Hub
          </h1>
          <p className="text-gray-500 text-sm">
            {t('login.title')}
          </p>
        </div>

        {/* 登录卡片 */}
        <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-sm">
          {/* 登录/注册切换 */}
          <div className="flex gap-2 mb-8 p-1 bg-gray-50 rounded-xl">
            <button
              type="button"
              onClick={() => {
                setIsRegister(false)
                setError('')
              }}
              className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
                !isRegister
                  ? 'bg-white text-black shadow-sm'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              {t('login.login')}
            </button>
            <button
              type="button"
              onClick={() => {
                setIsRegister(true)
                setError('')
              }}
              className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
                isRegister
                  ? 'bg-white text-black shadow-sm'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              {t('login.register')}
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="p-4 bg-red-50 border border-red-200 text-red-600 rounded-xl text-sm">
                {error}
              </div>
            )}

            {isRegister && (
              <div>
                <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 mb-2">
                  {t('login.name')}
                  <span className="text-gray-400 text-xs ml-2">{t('login.nameOptional')}</span>
                </label>
                <input
                  id="fullName"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl focus:border-black focus:ring-2 focus:ring-black/5 transition-all outline-none text-gray-900 placeholder-gray-400"
                  placeholder={t('login.namePlaceholder')}
                />
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                {t('login.email')}
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl focus:border-black focus:ring-2 focus:ring-black/5 transition-all outline-none text-gray-900 placeholder-gray-400"
                placeholder={t('login.emailPlaceholder')}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                {t('login.password')}
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-xl focus:border-black focus:ring-2 focus:ring-black/5 transition-all outline-none text-gray-900 placeholder-gray-400"
                placeholder={t('login.passwordPlaceholder')}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-black hover:bg-gray-800 text-white font-medium rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.01] disabled:hover:scale-100"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  {isRegister ? t('login.registering') : t('login.loggingIn')}
                </span>
              ) : (
                isRegister ? t('login.register') : t('login.login')
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
