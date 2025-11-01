'use client'

import { useState, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { tokenUsageAPI, TokenUsageStats } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import { useTranslations } from '@/lib/translations'
import { X, User, TrendingUp, Calendar, RefreshCw, Loader2, Languages } from 'lucide-react'

interface UserProfileProps {
  onClose: () => void
}

export default function UserProfile({ onClose }: UserProfileProps) {
  const { user } = useAuthStore()
  const router = useRouter()
  const pathname = usePathname()
  const { t, locale: currentLocale } = useTranslations()
  const [stats, setStats] = useState<TokenUsageStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showLanguageMenu, setShowLanguageMenu] = useState(false)

  // 切换语言
  const switchLanguage = (locale: 'zh-CN' | 'en-US') => {
    if (locale === currentLocale) {
      setShowLanguageMenu(false)
      return
    }
    const segments = pathname.split('/')
    // 移除当前的 locale，保留其余路径
    const remainingPath = segments.slice(2).join('/')
    const newPath = `/${locale}${remainingPath ? '/' + remainingPath : ''}`
    setShowLanguageMenu(false)
    router.push(newPath)
    // 刷新页面以确保所有组件重新渲染
    router.refresh()
  }

  // 点击外部关闭菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (!target.closest('.language-switcher-container')) {
        setShowLanguageMenu(false)
      }
    }

    if (showLanguageMenu) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [showLanguageMenu])

  const loadStats = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await tokenUsageAPI.getStats()
      setStats(data)
    } catch (err: any) {
      console.error('加载使用量统计失败:', err)
      setError(err.response?.data?.detail || t('profile.loadError'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
  }, [])

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(2)}M`
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`
    }
    return num.toLocaleString()
  }

  const getPercentage = (used: number, limit: number) => {
    return Math.min((used / limit) * 100, 100)
  }

  const getProgressColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500'
    if (percentage >= 70) return 'bg-yellow-500'
    return 'bg-blue-500'
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <User className="w-6 h-6 text-blue-600" />
            <div>
              <h2 className="text-xl font-semibold text-gray-800">{t('profile.personalCenter')}</h2>
              <p className="text-sm text-gray-500">{user?.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Language Switcher */}
            <div className="relative language-switcher-container">
              <button
                onClick={() => setShowLanguageMenu(!showLanguageMenu)}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                title={currentLocale === 'zh-CN' ? 'Language' : '语言'}
              >
                <Languages className="w-5 h-5" />
              </button>
              {showLanguageMenu && (
                <div className="absolute right-0 top-full mt-2 bg-white rounded-lg shadow-lg border border-gray-200 py-1 min-w-[120px] z-10">
                  <button
                    onClick={() => switchLanguage('en-US')}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-100 transition-colors ${
                      currentLocale === 'en-US' ? 'bg-blue-50 text-blue-600 font-medium' : 'text-gray-700'
                    }`}
                  >
                    English
                  </button>
                  <button
                    onClick={() => switchLanguage('zh-CN')}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-100 transition-colors ${
                      currentLocale === 'zh-CN' ? 'bg-blue-50 text-blue-600 font-medium' : 'text-gray-700'
                    }`}
                  >
                    中文
                  </button>
                </div>
              )}
            </div>
            <button
              onClick={loadStats}
              disabled={loading}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title={t('common.refresh')}
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <RefreshCw className="w-5 h-5" />
              )}
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title={t('common.close')}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && !stats ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            </div>
          ) : error ? (
            <div className="text-center py-20">
              <p className="text-red-500 mb-4">{error}</p>
              <button
                onClick={loadStats}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                {t('common.retry')}
              </button>
            </div>
          ) : stats ? (
            <div className="space-y-6">
              {/* 每日使用量 */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-100">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-blue-600" />
                    <h3 className="text-lg font-semibold text-gray-800">{t('profile.dailyUsage')}</h3>
                  </div>
                  <span className="text-sm text-gray-600">
                    {formatNumber(stats.daily_usage)} / {formatNumber(stats.daily_limit)} tokens
                  </span>
                </div>
                
                <div className="mb-2">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>{t('profile.used')}: {formatNumber(stats.daily_usage)}</span>
                    <span>{t('profile.remaining')}: {formatNumber(stats.daily_remaining)}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${getProgressColor(getPercentage(stats.daily_usage, stats.daily_limit))}`}
                      style={{ width: `${getPercentage(stats.daily_usage, stats.daily_limit)}%` }}
                    />
                  </div>
                </div>
                
                <p className="text-xs text-gray-500 mt-2">
                  {t('profile.usageRate')}: {getPercentage(stats.daily_usage, stats.daily_limit).toFixed(1)}%
                </p>
              </div>

              {/* 每月使用量 */}
              <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-6 border border-purple-100">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-purple-600" />
                    <h3 className="text-lg font-semibold text-gray-800">{t('profile.monthlyUsage')}</h3>
                  </div>
                  <span className="text-sm text-gray-600">
                    {formatNumber(stats.monthly_usage)} / {formatNumber(stats.monthly_limit)} tokens
                  </span>
                </div>
                
                <div className="mb-2">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>{t('profile.used')}: {formatNumber(stats.monthly_usage)}</span>
                    <span>{t('profile.remaining')}: {formatNumber(stats.monthly_remaining)}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${getProgressColor(getPercentage(stats.monthly_usage, stats.monthly_limit))}`}
                      style={{ width: `${getPercentage(stats.monthly_usage, stats.monthly_limit)}%` }}
                    />
                  </div>
                </div>
                
                <p className="text-xs text-gray-500 mt-2">
                  {t('profile.usageRate')}: {getPercentage(stats.monthly_usage, stats.monthly_limit).toFixed(1)}%
                </p>
              </div>

              {/* 使用说明 */}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <h4 className="text-sm font-semibold text-gray-700 mb-2">{t('profile.instructions')}</h4>
                <ul className="text-xs text-gray-600 space-y-1">
                  <li>• {t('profile.instruction1')}</li>
                  <li>• {t('profile.instruction2')}</li>
                  <li>• {t('profile.instruction3')}</li>
                  <li>• {t('profile.instruction4')}</li>
                </ul>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}






