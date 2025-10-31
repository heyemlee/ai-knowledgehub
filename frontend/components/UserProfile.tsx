'use client'

import { useState, useEffect } from 'react'
import { tokenUsageAPI, TokenUsageStats } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import { X, User, TrendingUp, Calendar, RefreshCw, Loader2 } from 'lucide-react'

interface UserProfileProps {
  onClose: () => void
}

export default function UserProfile({ onClose }: UserProfileProps) {
  const { user } = useAuthStore()
  const [stats, setStats] = useState<TokenUsageStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadStats = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await tokenUsageAPI.getStats()
      setStats(data)
    } catch (err: any) {
      console.error('加载使用量统计失败:', err)
      setError(err.response?.data?.detail || '加载失败，请稍后重试')
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
              <h2 className="text-xl font-semibold text-gray-800">个人中心</h2>
              <p className="text-sm text-gray-500">{user?.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadStats}
              disabled={loading}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title="刷新"
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
              title="关闭"
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
                重试
              </button>
            </div>
          ) : stats ? (
            <div className="space-y-6">
              {/* 每日使用量 */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-100">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-blue-600" />
                    <h3 className="text-lg font-semibold text-gray-800">今日使用量</h3>
                  </div>
                  <span className="text-sm text-gray-600">
                    {formatNumber(stats.daily_usage)} / {formatNumber(stats.daily_limit)} tokens
                  </span>
                </div>
                
                <div className="mb-2">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>已使用: {formatNumber(stats.daily_usage)}</span>
                    <span>剩余: {formatNumber(stats.daily_remaining)}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${getProgressColor(getPercentage(stats.daily_usage, stats.daily_limit))}`}
                      style={{ width: `${getPercentage(stats.daily_usage, stats.daily_limit)}%` }}
                    />
                  </div>
                </div>
                
                <p className="text-xs text-gray-500 mt-2">
                  使用率: {getPercentage(stats.daily_usage, stats.daily_limit).toFixed(1)}%
                </p>
              </div>

              {/* 每月使用量 */}
              <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-6 border border-purple-100">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-purple-600" />
                    <h3 className="text-lg font-semibold text-gray-800">本月使用量</h3>
                  </div>
                  <span className="text-sm text-gray-600">
                    {formatNumber(stats.monthly_usage)} / {formatNumber(stats.monthly_limit)} tokens
                  </span>
                </div>
                
                <div className="mb-2">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>已使用: {formatNumber(stats.monthly_usage)}</span>
                    <span>剩余: {formatNumber(stats.monthly_remaining)}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${getProgressColor(getPercentage(stats.monthly_usage, stats.monthly_limit))}`}
                      style={{ width: `${getPercentage(stats.monthly_usage, stats.monthly_limit)}%` }}
                    />
                  </div>
                </div>
                
                <p className="text-xs text-gray-500 mt-2">
                  使用率: {getPercentage(stats.monthly_usage, stats.monthly_limit).toFixed(1)}%
                </p>
              </div>

              {/* 使用说明 */}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <h4 className="text-sm font-semibold text-gray-700 mb-2">使用说明</h4>
                <ul className="text-xs text-gray-600 space-y-1">
                  <li>• 每日限制会在 00:00 UTC 重置</li>
                  <li>• 每月限制会在每月 1 日重置</li>
                  <li>• Token 使用量会根据您的问答请求实时更新</li>
                  <li>• 达到限制后需要等待重置或联系管理员</li>
                </ul>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}


