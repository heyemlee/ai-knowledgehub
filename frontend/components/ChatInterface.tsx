'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { chatAPI, ChatResponse, conversationsAPI, Message } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import { isAdmin } from '@/lib/auth'
import ConversationHistory from './ConversationHistory'
import UserProfile from './UserProfile'
import AdminPanel from './AdminPanel'
import DocumentCard from './DocumentCard'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, LogOut, User, Settings, Menu, Copy, Check, Download } from 'lucide-react'
import { toast } from './Toast'

export default function ChatInterface() {
  const [messages, setMessages] = useState<Array<{
    role: 'user' | 'assistant';
    content: string;
    sources?: any[];
    images?: any[];  // 图片列表
    documents?: any[];  // 新增：匹配的文档列表
  }>>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [refreshHistory, setRefreshHistory] = useState(0)
  const [showProfile, setShowProfile] = useState(false)
  const [showAdmin, setShowAdmin] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
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
      toast.error('Failed to load conversation, please try again later')
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
      let finalImages: any[] | undefined = undefined
      let finalDocuments: any[] | undefined = undefined  // 新增：文档数据
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

        // 新增：接收图片数据
        if (chunk.images) {
          finalImages = chunk.images
        }

        // 新增：接收文档数据
        if (chunk.documents) {
          finalDocuments = chunk.documents
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
          images: finalImages,
          documents: finalDocuments,  // 新增：保存文档数据
        },
      ])
      setRefreshHistory((prev) => prev + 1)
    } catch (error: any) {
      console.error('聊天错误:', error)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${error.message || 'Request failed, please try again later'}`,
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

  const handleCopyMessage = async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedIndex(index)
      toast.success('Copied to clipboard')
      setTimeout(() => setCopiedIndex(null), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
      toast.error('Failed to copy')
    }
  }

  const handleDownloadImage = async (imageId: number, filename: string) => {
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const imageUrl = `${API_URL}/api/v1/images/${imageId}/file`

      // 下载图片
      const response = await fetch(imageUrl, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      })

      if (!response.ok) throw new Error('Download failed')

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename || `image_${imageId}.jpg`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      toast.success('Image downloaded')
    } catch (error) {
      console.error('Failed to download image:', error)
      toast.error('Failed to download image')
    }
  }

  return (
    <div className="fixed inset-0 flex bg-white overflow-hidden">
      {/* 对话历史侧边栏 */}
      <ConversationHistory
        currentConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        refreshTrigger={refreshHistory}
        isOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
      />

      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col w-full">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-4 md:px-6 py-3 md:py-4 flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-2 -ml-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              <Menu size={24} />
            </button>
            <h1 className="text-xl md:text-2xl font-bold text-black">ABC AI Hub</h1>
          </div>
          <div className="flex items-center gap-2">
            {isAdmin() && (
              <button
                onClick={() => setShowAdmin(true)}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-black text-white hover:bg-gray-800 rounded-lg transition-colors"
              >
                <Settings size={16} />
                <span className="hidden sm:inline">Admin</span>
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
        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-4 md:py-8 space-y-4 md:space-y-6">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-2xl mx-auto w-full">
                <div className="mb-8">
                  <div className="w-16 h-16 bg-black rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                  </div>
                </div>
                <h2 className="text-3xl font-bold mb-3 text-black">
                  What do you want to know?
                </h2>
                <p className="text-gray-500 text-base">
                  AI intelligent answer assistant
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
                className={`max-w-3xl rounded-2xl ${msg.role === 'user'
                  ? 'bg-black text-white px-3 py-2 md:px-5 md:py-4'
                  : 'text-gray-900 px-0 py-0'
                  }`}
              >
                {msg.role === 'user' ? (
                  <p className="whitespace-pre-wrap leading-relaxed text-[15px]">{msg.content}</p>
                ) : (
                  <div className="relative group">
                    <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-900 prose-strong:text-gray-900 prose-li:text-gray-900">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>

                    {/* 复制按钮 */}
                    <button
                      onClick={() => handleCopyMessage(msg.content, idx)}
                      className="absolute -top-2 -right-2 p-2 bg-white border border-gray-200 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-gray-50 transition-all shadow-sm"
                      title="Copy message"
                    >
                      {copiedIndex === idx ? (
                        <Check size={16} className="text-green-600" />
                      ) : (
                        <Copy size={16} className="text-gray-600" />
                      )}
                    </button>

                    {/* 新增：显示匹配的文档 */}
                    {msg.documents && msg.documents.length > 0 && (
                      <div className="mt-4 space-y-3">
                        <p className="text-sm text-gray-600 font-medium">Related Documents:</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {msg.documents.map((doc: any, docIdx: number) => (
                            <DocumentCard key={docIdx} document={doc} />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 显示图片 */}
                    {msg.images && msg.images.length > 0 && (
                      <div className="mt-4 space-y-3">
                        <p className="text-sm text-gray-600 font-medium">Related Images:</p>
                        <div className="flex flex-wrap gap-4">
                          {msg.images.map((image: any, imgIdx: number) => {
                            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
                            const imageUrl = `${API_URL}/api/v1/images/${image.id}/file`

                            return (
                              <div key={imgIdx} className="group/image relative rounded-lg border border-gray-200 hover:border-gray-400 transition-all overflow-hidden bg-gray-50">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  src={imageUrl}
                                  alt={image.description || 'Related Image'}
                                  className="max-w-full max-h-96 object-contain cursor-pointer group-hover/image:opacity-90 transition-opacity"
                                  onClick={() => window.open(imageUrl, '_blank')}
                                  loading="lazy"
                                />

                                {/* 下载按钮 */}
                                <button
                                  onClick={() => handleDownloadImage(image.id, image.filename || image.original_filename)}
                                  className="absolute top-2 right-2 p-2 bg-white/90 backdrop-blur-sm border border-gray-200 rounded-lg opacity-0 group-hover/image:opacity-100 hover:bg-white transition-all shadow-sm"
                                  title="Download image"
                                >
                                  <Download size={16} className="text-gray-600" />
                                </button>

                                {image.description && (
                                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent text-white text-xs p-3 opacity-0 group-hover/image:opacity-100 transition-opacity">
                                    <p className="line-clamp-2">{image.description}</p>
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {streaming && !streamingContent && (
            <div className="flex justify-start message-slide-in">
              <div className="max-w-3xl rounded-2xl px-3 py-2 md:px-5 md:py-4 bg-gray-50 border border-gray-100 flex items-center justify-center min-h-[40px]">
                <div className="w-3 h-3 bg-black rounded-full animate-pulse-scale"></div>
              </div>
            </div>
          )}

          {streaming && streamingContent && (
            <div className="flex justify-start message-slide-in">
              <div className="max-w-3xl rounded-2xl px-0 py-0 text-gray-900">
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
        <div className="border-t border-gray-200 bg-white p-2 md:p-6 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
          <div className="max-w-4xl mx-auto">
            <div className="relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="What do you want to know?"
                disabled={streaming}
                className="w-full px-3 md:px-5 py-2 md:py-4 pr-10 md:pr-14 bg-white border border-gray-200 rounded-2xl focus:border-black focus:ring-2 focus:ring-black/5 transition-all outline-none text-gray-900 placeholder-gray-400 resize-none text-base"
                rows={1}
                style={{
                  minHeight: '40px',
                  maxHeight: '200px',
                }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || streaming}
                className="absolute right-2 bottom-2.5 md:right-3 md:bottom-3 p-2 md:p-3 bg-black hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-xl transition-all hover:scale-105 disabled:hover:scale-100"
              >
                {streaming ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Send size={18} />
                )}
              </button>
            </div>

          </div>
        </div>
      </div>

      {/* Modals */}
      {showProfile && <UserProfile onClose={() => setShowProfile(false)} />}
      {showAdmin && <AdminPanel isOpen={showAdmin} onClose={() => setShowAdmin(false)} />}
    </div>
  )
}
