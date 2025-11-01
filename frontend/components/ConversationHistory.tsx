'use client'

import { useState, useEffect } from 'react'
import { conversationsAPI, Conversation } from '@/lib/api'
import { useTranslations } from '@/lib/translations'
import { MessageSquare, Trash2, Loader2, Plus, ChevronLeft, ChevronRight } from 'lucide-react'

interface ConversationHistoryProps {
  currentConversationId: string | null
  onSelectConversation: (conversationId: string) => void
  onNewConversation: () => void
  refreshTrigger?: number
}

export default function ConversationHistory({
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  refreshTrigger,
}: ConversationHistoryProps) {
  const { t, locale } = useTranslations()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [isCollapsed, setIsCollapsed] = useState(false)

  // 格式化时间为洛杉矶时区
  const formatLosAngelesTime = (dateString: string) => {
    try {
      // FastAPI 返回的 datetime 通常是 ISO 8601 格式
      // 数据库存储的是 timezone-aware datetime (UTC)
      // 如果字符串没有时区标识（以Z结尾或包含时区偏移），添加 'Z' 表示 UTC
      let normalizedDateString = dateString.trim()
      
      // 检查是否已经包含时区信息
      const hasTimezone = normalizedDateString.endsWith('Z') || 
                          normalizedDateString.includes('+') || 
                          (normalizedDateString.includes('-') && normalizedDateString.match(/[+-]\d{2}:\d{2}$/))
      
      if (!hasTimezone && normalizedDateString.includes('T')) {
        // 如果没有时区信息但包含 T，添加 Z 表示 UTC
        normalizedDateString = normalizedDateString + (normalizedDateString.endsWith('T') ? '00:00:00Z' : 'Z')
      } else if (!hasTimezone && !normalizedDateString.includes('T')) {
        // 如果只有日期，添加时间部分
        normalizedDateString = normalizedDateString + 'T00:00:00Z'
      }
      
      const date = new Date(normalizedDateString)
      
      // 验证日期是否有效
      if (isNaN(date.getTime())) {
        console.warn('Invalid date string:', dateString, 'normalized:', normalizedDateString)
        return dateString
      }
      
      // 转换为洛杉矶时区
      return date.toLocaleString(locale === 'zh-CN' ? 'zh-CN' : 'en-US', {
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'America/Los_Angeles',
        hour12: locale === 'en-US', // 英文使用12小时制，中文使用24小时制
      })
    } catch (error) {
      console.error('Error formatting date:', dateString, error)
      return dateString
    }
  }

  const loadConversations = async () => {
    try {
      setLoading(true)
      const data = await conversationsAPI.list()
      setConversations(data)
    } catch (error) {
      console.error('加载对话列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConversations()
  }, [refreshTrigger])

  const handleDelete = async (e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation()
    if (!confirm(t('conversation.deleteConfirm'))) return

    try {
      setDeletingId(conversationId)
      await conversationsAPI.delete(conversationId)
      setConversations((prev) => prev.filter((c) => c.conversation_id !== conversationId))
      if (currentConversationId === conversationId) {
        onNewConversation()
      }
    } catch (error) {
      console.error('删除对话失败:', error)
      alert(t('conversation.deleteFailed'))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className={`relative bg-gray-50 border-r border-gray-200 flex flex-col h-full transition-all duration-300 ${
      isCollapsed ? 'w-0 md:w-16' : 'w-72'
    }`}>
      {/* 折叠/展开按钮 */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-6 z-10 w-6 h-6 bg-white border border-gray-200 rounded-full flex items-center justify-center hover:bg-gray-50 transition-colors shadow-sm"
        title={isCollapsed ? t('conversation.expandSidebar') : t('conversation.collapseSidebar')}
      >
        {isCollapsed ? (
          <ChevronRight size={14} className="text-gray-600" />
        ) : (
          <ChevronLeft size={14} className="text-gray-600" />
        )}
      </button>

      {/* 内容区域 */}
      <div className={`flex-1 flex flex-col overflow-hidden ${isCollapsed ? 'opacity-0' : 'opacity-100'} transition-opacity duration-300`}>
        <div className="p-4">
          <button
            onClick={onNewConversation}
            className="w-full px-4 py-3 bg-black hover:bg-gray-800 text-white rounded-xl transition-all text-sm font-medium flex items-center justify-center gap-2"
          >
            <Plus size={18} />
            {t('conversation.newConversation')}
          </button>
        </div>

        {/* Chats 标题 */}
        <div className="px-6 py-2">
          <h3 className="text-sm font-medium text-gray-500 tracking-wide">
            Chats
          </h3>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-8 text-center">
              <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="w-6 h-6 text-gray-400" />
              </div>
              <p className="text-gray-500 text-sm">{t('conversation.noConversations')}</p>
            </div>
          ) : (
            <div className="p-3 space-y-1">
              {conversations.map((conv) => (
                <div
                  key={conv.conversation_id}
                  onClick={() => onSelectConversation(conv.conversation_id)}
                  className={`group relative p-4 rounded-xl cursor-pointer transition-all ${
                    currentConversationId === conv.conversation_id
                      ? 'bg-white border border-gray-200 shadow-sm'
                      : 'hover:bg-white border border-transparent'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate mb-1">
                        {conv.title || t('conversation.newConversation')}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatLosAngelesTime(conv.updated_at)}
                      </p>
                    </div>
                    <button
                      onClick={(e) => handleDelete(e, conv.conversation_id)}
                      disabled={deletingId === conv.conversation_id}
                      className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-50 rounded-lg transition-all"
                      title={t('common.delete')}
                    >
                      {deletingId === conv.conversation_id ? (
                        <Loader2 className="w-4 h-4 animate-spin text-red-500" />
                      ) : (
                        <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-500" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 折叠状态下的迷你视图 */}
      {isCollapsed && (
        <div className="hidden md:flex flex-col items-center py-4 gap-3">
          <button
            onClick={onNewConversation}
            className="p-3 bg-black hover:bg-gray-800 text-white rounded-xl transition-all"
            title={t('conversation.newConversation')}
          >
            <Plus size={18} />
          </button>
          <div className="flex-1 flex flex-col items-center gap-2 overflow-y-auto py-2">
            {conversations.slice(0, 5).map((conv) => (
              <button
                key={conv.conversation_id}
                onClick={() => onSelectConversation(conv.conversation_id)}
                className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
                  currentConversationId === conv.conversation_id
                    ? 'bg-black text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
                title={conv.title || t('conversation.newConversation')}
              >
                <MessageSquare size={16} />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
