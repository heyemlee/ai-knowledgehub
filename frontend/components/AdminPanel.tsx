'use client'

import { useEffect, useState } from 'react'
import { adminApi, AdminDocument, AdminUser, DocumentStats, UserStats } from '@/lib/adminApi'
import { documentsAPI } from '@/lib/api'
import { useTranslations } from '@/lib/translations'
import { X, Upload, Trash2, Users, FileText, Download } from 'lucide-react'

interface AdminPanelProps {
  isOpen: boolean
  onClose: () => void
}

type Tab = 'dashboard' | 'documents' | 'users'

export default function AdminPanel({ isOpen, onClose }: AdminPanelProps) {
  const { t, locale } = useTranslations()
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')
  const [documents, setDocuments] = useState<AdminDocument[]>([])
  const [users, setUsers] = useState<AdminUser[]>([])
  const [documentStats, setDocumentStats] = useState<DocumentStats | null>(null)
  const [userStats, setUserStats] = useState<UserStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [uploading, setUploading] = useState(false)

  // 格式化时间为洛杉矶时区
  const formatLosAngelesDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString(locale === 'zh-CN' ? 'zh-CN' : 'en-US', {
      timeZone: 'America/Los_Angeles',
    })
  }

  useEffect(() => {
    if (isOpen) {
      fetchData()
    }
  }, [isOpen, activeTab])

  const fetchData = async () => {
    setLoading(true)
    try {
      if (activeTab === 'dashboard') {
        const [docs, usrs] = await Promise.all([
          adminApi.getDocumentStats(),
          adminApi.getUserStats(),
        ])
        setDocumentStats(docs)
        setUserStats(usrs)
      } else if (activeTab === 'documents') {
        const docs = await adminApi.getAllDocuments()
        setDocuments(docs)
      } else if (activeTab === 'users') {
        const usrs = await adminApi.getAllUsers()
        setUsers(usrs)
      }
    } catch (error) {
      console.error('获取数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (file.size > 50 * 1024 * 1024) {
      alert(t('admin.fileTooLarge'))
      return
    }

    const allowedTypes = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt']
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!allowedTypes.includes(fileExt)) {
      alert(t('admin.unsupportedFileType', { types: allowedTypes.join(', ') }))
      return
    }

    setUploading(true)
    try {
      await documentsAPI.upload(file)
      alert(t('admin.uploadSuccess'))
      fetchData()
      e.target.value = ''
    } catch (error: any) {
      console.error('上传失败:', error)
      alert(t('admin.uploadFailed', { error: error.response?.data?.detail || error.message }))
    } finally {
      setUploading(false)
    }
  }

  const handleDownload = async (fileId: string, filename: string) => {
    try {
      const response = await documentsAPI.download(fileId)
      const blob = new Blob([response])
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('下载失败:', error)
      alert(t('admin.downloadFailed'))
    }
  }

  const handleDelete = async (fileId: string, filename: string) => {
    if (!confirm(t('admin.deleteConfirm', { filename }))) {
      return
    }

    try {
      await adminApi.deleteDocument(fileId)
      alert(t('admin.deleteSuccess'))
      fetchData()
    } catch (error) {
      console.error('删除失败:', error)
      alert(t('admin.deleteFailed'))
    }
  }

  const filteredDocuments = documents.filter(doc =>
    doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* 遮罩 */}
      <div 
        className="absolute inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />
      
      {/* 弹窗 */}
      <div className="absolute inset-4 md:inset-8 bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col">
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center space-x-4">
            <h2 className="text-2xl font-bold text-black">{t('admin.title')}</h2>
            <div className="flex space-x-2">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === 'dashboard'
                    ? 'bg-black text-white'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {t('admin.dashboard')}
              </button>
              <button
                onClick={() => setActiveTab('documents')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === 'documents'
                    ? 'bg-black text-white'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {t('admin.documentManagement')}
              </button>
              <button
                onClick={() => setActiveTab('users')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === 'users'
                    ? 'bg-black text-white'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                {t('admin.userManagement')}
              </button>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-gray-600">{t('common.loading')}</div>
            </div>
          ) : (
            <>
              {/* 仪表盘 */}
              {activeTab === 'dashboard' && (
                <div className="space-y-6">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <StatCard
                      title={t('admin.totalUsers')}
                      value={userStats?.total_users || 0}
                    />
                    <StatCard
                      title={t('admin.totalDocuments')}
                      value={documentStats?.total_documents || 0}
                    />
                    <StatCard
                      title={t('admin.storageUsage')}
                      value={`${documentStats?.total_size_mb.toFixed(1) || 0} MB`}
                    />
                    <StatCard
                      title={t('admin.activeUsers')}
                      value={userStats?.active_users || 0}
                    />
                  </div>
                </div>
              )}

              {/* 文档管理 */}
              {activeTab === 'documents' && (
                <div className="space-y-4">
                  {/* 工具栏 */}
                  <div className="flex items-center justify-between">
                    <input
                      type="text"
                      placeholder={t('admin.searchDocuments')}
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="flex-1 max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    />
                    <div>
                      <input
                        type="file"
                        id="admin-file-upload"
                        className="hidden"
                        accept=".pdf,.docx,.doc,.xlsx,.xls,.txt"
                        onChange={handleFileUpload}
                        disabled={uploading}
                      />
                      <label
                        htmlFor="admin-file-upload"
                        className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white ${
                          uploading ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 cursor-pointer'
                        } transition-colors`}
                      >
                        <Upload size={16} />
                        {uploading ? t('admin.uploading') : t('admin.uploadDocument')}
                      </label>
                    </div>
                  </div>

                  {/* 文档列表 */}
                  {filteredDocuments.length === 0 ? (
                    <div className="bg-gray-50 rounded-lg p-12 text-center">
                      <p className="text-gray-600 mb-4">
                        {searchTerm ? t('admin.noMatchingDocuments') : t('admin.noDocuments')}
                      </p>
                      {!searchTerm && (
                        <label
                          htmlFor="admin-file-upload"
                          className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer transition-colors"
                        >
                          <Upload size={18} />
                          {t('admin.startUpload')}
                        </label>
                      )}
                    </div>
                  ) : (
                    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('admin.filename')}</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('admin.size')}</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('admin.chunks')}</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('admin.uploadTime')}</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('admin.actions')}</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {filteredDocuments.map((doc) => (
                            <tr key={doc.file_id} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate">
                                {doc.filename}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-500">
                                {(doc.file_size / 1024 / 1024).toFixed(2)} MB
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-500">
                                {doc.chunks_count}
                              </td>
                              <td className="px-4 py-3 text-sm text-gray-500">
                                {formatLosAngelesDate(doc.upload_time)}
                              </td>
                              <td className="px-4 py-3 text-sm">
                                <div className="flex items-center gap-3">
                                  <button
                                    onClick={() => handleDownload(doc.file_id, doc.filename)}
                                    className="text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
                                  >
                                    <Download size={14} />
                                    {t('admin.download')}
                                  </button>
                                  <button
                                    onClick={() => handleDelete(doc.file_id, doc.filename)}
                                    className="text-red-600 hover:text-red-800 inline-flex items-center gap-1"
                                  >
                                    <Trash2 size={14} />
                                    {t('admin.delete')}
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <p className="text-sm text-gray-500">
                    {t('admin.showingDocuments', { count: filteredDocuments.length, total: documents.length })}
                  </p>
                </div>
              )}

              {/* 用户管理 */}
              {activeTab === 'users' && (
                <div className="space-y-4">
                  <p className="text-sm text-gray-600">{t('admin.totalUsersCount', { count: users.length })}</p>
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('admin.userEmail')}</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('admin.userName')}</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('admin.userRole')}</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('admin.userStatus')}</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('admin.userCreatedAt')}</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {users.map((user) => (
                          <tr key={user.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm text-gray-900">{user.email}</td>
                            <td className="px-4 py-3 text-sm text-gray-500">{user.full_name || '-'}</td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-1 text-xs rounded-full ${
                                user.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'
                              }`}>
                                {user.role === 'admin' ? t('admin.roleAdmin') : t('admin.roleUser')}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-1 text-xs rounded-full ${
                                user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                              }`}>
                                {user.is_active ? t('admin.statusActive') : t('admin.statusInactive')}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500">
                              {formatLosAngelesDate(user.created_at)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value }: {
  title: string
  value: string | number
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 hover:border-gray-300 transition-colors">
      <p className="text-sm text-gray-500 mb-2">{title}</p>
      <p className="text-3xl font-bold text-black">{value}</p>
    </div>
  )
}

