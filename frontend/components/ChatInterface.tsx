'use client'

import { useState, useRef, useEffect } from 'react'
import { chatAPI, ChatResponse, conversationsAPI, Message } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import ConversationHistory from './ConversationHistory'
import DocumentPreview from './DocumentPreview'
import UserProfile from './UserProfile'
import { Send, LogOut, Eye, User } from 'lucide-react'

export default function ChatInterface() {
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; sources?: any[] }>>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [refreshHistory, setRefreshHistory] = useState(0)
  const [previewDoc, setPreviewDoc] = useState<{ fileId: string; filename: string; fileType: string } | null>(null)
  const [showProfile, setShowProfile] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { logout, user } = useAuthStore()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingContent])

  const loadConversationMessages = async (convId: string) => {
    try {
      setLoadingMessages(true)
      const msgs = await conversationsAPI.getMessages(convId)
      const formattedMessages = msgs.map((msg: Message) => {
        let sources = undefined
        if (msg.sources) {
          try {
            sources = JSON.parse(msg.sources)
          } catch (e) {
            console.error('解析 sources 失败:', e)
          }
        }
        return {
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
          sources,
        }
      })
      setMessages(formattedMessages)
      setConversationId(convId)
    } catch (error) {
      console.error('加载对话消息失败:', error)
      alert('加载对话失败，请稍后重试')
    } finally {
      setLoadingMessages(false)
    }
  }

  const handleNewConversation = () => {
    setConversationId(null)
    setMessages([])
  }

  const handleSelectConversation = (convId: string) => {
    loadConversationMessages(convId)
  }

  const handleSend = async () => {
    if (!input.trim() || loading || streaming) return

    const userMessage = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setStreaming(true)
    setStreamingContent('')

    try {
      let fullAnswer = ''
      let finalSources: any[] | undefined = undefined
      let finalConversationId: string | null = null

      for await (const chunk of chatAPI.stream({
        question: userMessage,
        conversation_id: conversationId || undefined,
        temperature: 0.7,
        max_tokens: 1000,
      })) {
        if (chunk.error) {
          throw new Error(chunk.content)
        }

        if (chunk.content) {
          fullAnswer += chunk.content
          setStreamingContent(fullAnswer)
          setTimeout(() => scrollToBottom(), 0)
        }

        if (chunk.done) {
          if (chunk.sources) {
            finalSources = chunk.sources
          }
          if (chunk.conversation_id) {
            finalConversationId = chunk.conversation_id
          }
          break
        }
      }

      setConversationId(finalConversationId || conversationId)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: fullAnswer,
          sources: finalSources,
        },
      ])
      setStreamingContent('')
      setRefreshHistory((prev) => prev + 1)
    } catch (error: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `错误: ${error.message || '请求失败，请稍后重试'}`,
        },
      ])
      setStreamingContent('')
    } finally {
      setStreaming(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* 对话历史侧边栏 */}
      <ConversationHistory
        currentConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        refreshTrigger={refreshHistory}
      />

      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">ABC AI Knowledge Hub</h1>
            <p className="text-sm text-gray-500">智能问答平台</p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowProfile(true)}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              title="个人中心"
            >
              <User size={16} />
              <span className="hidden sm:inline">{user?.email}</span>
            </button>
            <button
              onClick={logout}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              title="退出登录"
            >
              <LogOut size={16} />
              <span className="hidden sm:inline">退出</span>
            </button>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-20">
            <p className="text-lg mb-2">👋 欢迎使用知识库系统</p>
            <p>请输入您的问题，AI 将基于企业知识库为您解答</p>
          </div>
          )}

          {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-3xl rounded-lg px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-800 shadow-sm border border-gray-200'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-xs font-semibold text-gray-500 mb-2">参考来源:</p>
                  <div className="space-y-1">
                    {msg.sources.map((source, i) => {
                      const filename = source.metadata?.filename || '未知文档'
                      const fileId = source.metadata?.file_id
                      return (
                        <div key={i} className="flex items-center justify-between text-xs text-gray-600 group">
                          <span>
                            • {filename}
                          </span>
                          {fileId && (
                            <button
                              onClick={() => setPreviewDoc({
                                fileId,
                                filename,
                                fileType: source.metadata?.file_type || ''
                              })}
                              className="opacity-0 group-hover:opacity-100 ml-2 p-1 hover:bg-gray-100 rounded transition-opacity"
                              title="预览文档"
                            >
                              <Eye size={14} />
                            </button>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
          ))}

          {streaming && streamingContent && (
            <div className="flex justify-start">
              <div className="max-w-3xl bg-white rounded-lg px-4 py-3 shadow-sm border border-gray-200">
                <p className="whitespace-pre-wrap">{streamingContent}</p>
                <span className="inline-block w-2 h-4 bg-blue-600 ml-1 animate-pulse"></span>
              </div>
            </div>
          )}

          {streaming && !streamingContent && (
            <div className="flex justify-start">
              <div className="bg-white rounded-lg px-4 py-3 shadow-sm border border-gray-200">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="bg-white border-t border-gray-200 px-6 py-4">
          <div className="flex items-end gap-4 max-w-4xl mx-auto">
          <div className="flex-1">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入您的问题..."
              rows={1}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              style={{ minHeight: '48px', maxHeight: '120px' }}
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading || streaming}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Send size={20} />
            {streaming ? '生成中...' : '发送'}
          </button>
          </div>
        </div>
      </div>

      {/* 文档预览弹窗 */}
      {previewDoc && (
        <DocumentPreview
          fileId={previewDoc.fileId}
          filename={previewDoc.filename}
          fileType={previewDoc.fileType}
          onClose={() => setPreviewDoc(null)}
        />
      )}

      {/* 个人中心弹窗 */}
      {showProfile && (
        <UserProfile onClose={() => setShowProfile(false)} />
      )}
    </div>
  )
}

