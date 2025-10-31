'use client'

import { useState, useEffect } from 'react'
import { conversationsAPI, Conversation } from '@/lib/api'
import { MessageSquare, Trash2, Loader2 } from 'lucide-react'

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
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)

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
    if (!confirm('确定要删除这个对话吗？')) return

    try {
      setDeletingId(conversationId)
      await conversationsAPI.delete(conversationId)
      setConversations((prev) => prev.filter((c) => c.conversation_id !== conversationId))
      if (currentConversationId === conversationId) {
        onNewConversation()
      }
    } catch (error) {
      console.error('删除对话失败:', error)
      alert('删除失败，请稍后重试')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onNewConversation}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          + 新建对话
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">
            <MessageSquare className="w-8 h-8 mx-auto mb-2 text-gray-300" />
            <p>暂无对话记录</p>
          </div>
        ) : (
          <div className="p-2">
            {conversations.map((conv) => (
              <div
                key={conv.conversation_id}
                onClick={() => onSelectConversation(conv.conversation_id)}
                className={`group relative p-3 rounded-lg mb-1 cursor-pointer transition-colors ${
                  currentConversationId === conv.conversation_id
                    ? 'bg-blue-50 border border-blue-200'
                    : 'hover:bg-gray-50'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">
                      {conv.title || '新对话'}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(conv.updated_at).toLocaleDateString('zh-CN', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, conv.conversation_id)}
                    disabled={deletingId === conv.conversation_id}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded transition-opacity"
                    title="删除对话"
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
  )
}

