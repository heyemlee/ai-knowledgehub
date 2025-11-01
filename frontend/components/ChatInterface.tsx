'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { chatAPI, ChatResponse, conversationsAPI, Message } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import { isAdmin } from '@/lib/auth'
import { useTranslations } from '@/lib/translations'
import ConversationHistory from './ConversationHistory'
import UserProfile from './UserProfile'
import AdminPanel from './AdminPanel'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, LogOut, User, Settings } from 'lucide-react'

export default function ChatInterface() {
  const { t } = useTranslations()
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; sources?: any[] }>>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [refreshHistory, setRefreshHistory] = useState(0)
  const [showProfile, setShowProfile] = useState(false)
  const [showAdmin, setShowAdmin] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { logout, user } = useAuthStore()
  const router = useRouter()

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
      alert(t('chat.loadingError'))
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
        }

        if (chunk.sources) {
          finalSources = chunk.sources
        }

        if (chunk.conversation_id) {
          finalConversationId = chunk.conversation_id
          if (!conversationId) {
            setConversationId(chunk.conversation_id)
          }
        }
      }

      setStreamingContent('')
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: fullAnswer,
          sources: finalSources,
        },
      ])
      setRefreshHistory((prev) => prev + 1)
    } catch (error: any) {
      console.error('聊天错误:', error)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `错误: ${error.message || t('chat.errorMessage')}`,
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
    <div className="flex h-screen bg-white">
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
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-black">ABC AI Hub</h1>
          </div>
          <div className="flex items-center gap-2">
            {isAdmin() && (
              <button
                onClick={() => setShowAdmin(true)}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-black text-white hover:bg-gray-800 rounded-lg transition-colors"
              >
                <Settings size={16} />
                <span className="hidden sm:inline">{t('chat.admin')}</span>
              </button>
            )}
            <button
              onClick={() => setShowProfile(true)}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <User size={16} />
              <span className="hidden sm:inline text-xs">{user?.email}</span>
            </button>
            <button
              onClick={logout}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-8 space-y-6">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-2xl mx-auto">
                <div className="mb-8">
                  <div className="w-16 h-16 bg-black rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                  </div>
                </div>
                <h2 className="text-3xl font-bold mb-3 text-black">
                  {t('chat.whatDoYouWant')}
                </h2>
                <p className="text-gray-500 text-base">
                  {t('chat.assistantDescription')}
                </p>
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} message-slide-in`}
            >
              <div
                className={`max-w-3xl rounded-2xl px-5 py-4 ${
                  msg.role === 'user'
                    ? 'bg-black text-white'
                    : 'bg-gray-50 text-gray-900 border border-gray-100'
                }`}
              >
                {msg.role === 'user' ? (
                  <p className="whitespace-pre-wrap leading-relaxed text-[15px]">{msg.content}</p>
                ) : (
                  <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-900 prose-strong:text-gray-900 prose-li:text-gray-900">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          ))}

          {streaming && !streamingContent && (
            <div className="flex justify-start message-slide-in">
              <div className="max-w-3xl rounded-2xl px-5 py-4 bg-gray-50 border border-gray-100 flex items-center justify-center min-h-[60px]">
                <div className="w-3 h-3 bg-black rounded-full animate-pulse-scale"></div>
              </div>
            </div>
          )}

          {streaming && streamingContent && (
            <div className="flex justify-start message-slide-in">
              <div className="max-w-3xl rounded-2xl px-5 py-4 bg-gray-50 text-gray-900 border border-gray-100">
                <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-900 prose-strong:text-gray-900 prose-li:text-gray-900">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingContent}</ReactMarkdown>
                </div>
                <div className="flex items-center gap-2 mt-3">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 bg-white p-4 md:p-6">
          <div className="max-w-4xl mx-auto">
            <div className="relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={t('chat.placeholder')}
                disabled={streaming}
                className="w-full px-5 py-4 pr-14 bg-white border border-gray-200 rounded-2xl focus:border-black focus:ring-2 focus:ring-black/5 transition-all outline-none text-gray-900 placeholder-gray-400 resize-none"
                rows={1}
                style={{
                  minHeight: '56px',
                  maxHeight: '200px',
                }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || streaming}
                className="absolute right-3 bottom-3 p-3 bg-black hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-xl transition-all hover:scale-105 disabled:hover:scale-100"
              >
                {streaming ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Send size={18} />
                )}
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-3 text-center">
              {t('chat.disclaimer')}
            </p>
          </div>
        </div>
      </div>

      {/* Modals */}
      {showProfile && <UserProfile onClose={() => setShowProfile(false)} />}
      {showAdmin && <AdminPanel isOpen={showAdmin} onClose={() => setShowAdmin(false)} />}
    </div>
  )
}
