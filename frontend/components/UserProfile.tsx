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
      console.error('Failed to load usage statistics:', err)
      setError(err.response?.data?.detail || 'Failed to load, please try again later')
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
              <h2 className="text-xl font-semibold text-gray-800">Personal Center</h2>
              <p className="text-sm text-gray-500">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Usage Stats */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-800">Usage Statistics</h3>
              <button
                onClick={loadStats}
                disabled={loading}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-600 rounded-lg text-sm">
                {error}
              </div>
            )}

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              </div>
            ) : stats ? (
              <div className="space-y-6">
                {/* Daily Usage */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Calendar className="w-5 h-5 text-blue-600" />
                    <h4 className="font-medium text-gray-800">Daily Usage</h4>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">Used</span>
                        <span className="font-medium">{formatNumber(stats.daily_usage)}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`${getProgressColor(getPercentage(stats.daily_usage, stats.daily_limit))} h-2 rounded-full transition-all duration-300`}
                          style={{ width: `${getPercentage(stats.daily_usage, stats.daily_limit)}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>{formatNumber(stats.daily_usage)}</span>
                        <span>Limit: {formatNumber(stats.daily_limit)}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Monthly Usage */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp className="w-5 h-5 text-green-600" />
                    <h4 className="font-medium text-gray-800">Monthly Usage</h4>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">Used</span>
                        <span className="font-medium">{formatNumber(stats.monthly_usage)}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`${getProgressColor(getPercentage(stats.monthly_usage, stats.monthly_limit))} h-2 rounded-full transition-all duration-300`}
                          style={{ width: `${getPercentage(stats.monthly_usage, stats.monthly_limit)}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>{formatNumber(stats.monthly_usage)}</span>
                        <span>Limit: {formatNumber(stats.monthly_limit)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                No usage data available
              </div>
            )}
          </div>

          {/* Instructions */}
          <div className="bg-blue-50 rounded-lg p-4">
            <h4 className="font-medium text-gray-800 mb-3">Instructions</h4>
            <ul className="text-sm text-gray-600 space-y-2">
              <li>• Daily limit resets at 00:00 UTC</li>
              <li>• Monthly limit resets on the 1st of each month</li>
              <li>• Token usage updates in real-time with your Q&A requests</li>
              <li>• Contact administrator when limit is reached or wait for reset</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}