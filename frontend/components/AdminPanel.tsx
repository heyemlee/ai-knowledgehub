'use client'

import { useEffect, useState } from 'react'
import { adminApi, AdminDocument, AdminUser, DocumentStats, UserStats } from '@/lib/adminApi'
import { documentsAPI } from '@/lib/api'
import { X, Upload, Trash2, Users, FileText, Download, Image } from 'lucide-react'
import { toast } from './Toast'
import { confirm } from './ConfirmDialog'
import ImageManagement from './ImageManagement'


interface AdminPanelProps {
  isOpen: boolean
  onClose: () => void
}

type Tab = 'dashboard' | 'documents' | 'images' | 'users'


export default function AdminPanel({ isOpen, onClose }: AdminPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')
  const [documents, setDocuments] = useState<AdminDocument[]>([])
  const [users, setUsers] = useState<AdminUser[]>([])
  const [documentStats, setDocumentStats] = useState<DocumentStats | null>(null)
  const [userStats, setUserStats] = useState<UserStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [uploading, setUploading] = useState(false)

  const formatLosAngelesDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      timeZone: 'America/Los_Angeles',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    if (bytes === 0) return '0 Bytes'
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Check file size (50MB limit)
    if (file.size > 50 * 1024 * 1024) {
      toast.error('File size cannot exceed 50MB')
      return
    }

    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()
    const allowedTypes = ['.pdf', '.doc', '.docx', '.txt', '.md']

    if (!allowedTypes.includes(fileExt)) {
      toast.error(`Unsupported file type. Supported: ${allowedTypes.join(', ')}`)
      return
    }

    try {
      setUploading(true)
      await documentsAPI.upload(file)
      toast.success('Upload successful!')
      await loadDocuments()
    } catch (error: any) {
      console.error('Upload failed:', error)
      toast.error(`Upload failed: ${error.response?.data?.detail || error.message}`)
    } finally {
      setUploading(false)
    }
  }

  const handleDownload = async (documentId: string, filename: string) => {
    try {
      const blob = await documentsAPI.downloadFile(documentId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error: any) {
      console.error('Download failed:', error)
      toast.error('Download failed')
    }
  }

  const handleDelete = async (documentId: string, filename: string) => {
    const confirmed = await confirm(`Are you sure you want to delete "${filename}"?\n\nThis will delete both the file and vector data, and cannot be recovered!`, {
      title: 'Delete',
      confirmText: 'Delete',
      cancelText: 'Cancel',
    })

    if (!confirmed) return

    try {
      await documentsAPI.delete(documentId)
      toast.success('Delete successful')
      await loadDocuments()
    } catch (error: any) {
      console.error('Delete failed:', error)
      toast.error('Delete failed')
    }
  }

  const loadDocuments = async () => {
    try {
      const docs = await adminApi.getAllDocuments()
      setDocuments(docs)
    } catch (error: any) {
      console.error('Failed to load documents:', error)
      toast.error('Failed to load data')
    }
  }

  const loadUsers = async () => {
    try {
      const [userList, stats] = await Promise.all([
        adminApi.getAllUsers(),
        adminApi.getUserStats()
      ])
      setUsers(userList)
      setUserStats(stats)
    } catch (error: any) {
      console.error('Failed to load users:', error)
      toast.error('Failed to load data')
    }
  }

  const loadStats = async () => {
    try {
      const [docStats, userStatsData] = await Promise.all([
        adminApi.getDocumentStats(),
        adminApi.getUserStats()
      ])
      setDocumentStats(docStats)
      setUserStats(userStatsData)
    } catch (error: any) {
      console.error('Failed to load stats:', error)
      toast.error('Failed to load data')
    }
  }

  useEffect(() => {
    if (!isOpen) return

    setLoading(true)
    const loadTabData = async () => {
      switch (activeTab) {
        case 'documents':
          await loadDocuments()
          break
        case 'users':
          await loadUsers()
          break
        case 'dashboard':
          await loadStats()
          break
      }
      setLoading(false)
    }

    loadTabData()
  }, [isOpen, activeTab])

  const filteredDocuments = documents.filter(doc =>
    doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-black">Admin Panel</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-6 py-3 text-sm font-medium transition-colors ${activeTab === 'dashboard'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-500 hover:text-gray-700'
              }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => setActiveTab('documents')}
            className={`px-6 py-3 text-sm font-medium transition-colors ${activeTab === 'documents'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-500 hover:text-gray-700'
              }`}
          >
            Document Management
          </button>
          <button
            onClick={() => setActiveTab('images')}
            className={`px-6 py-3 text-sm font-medium transition-colors ${activeTab === 'images'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-500 hover:text-gray-700'
              }`}
          >
            Image Management
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`px-6 py-3 text-sm font-medium transition-colors ${activeTab === 'users'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-500 hover:text-gray-700'
              }`}
          >
            User Management
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-gray-600">Loading...</div>
            </div>
          ) : (
            <>
              {activeTab === 'dashboard' && documentStats && userStats && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                  <div className="bg-blue-50 rounded-lg p-6" title="Total Users">
                    <div className="flex items-center">
                      <Users className="w-8 h-8 text-blue-600 mr-3" />
                      <div>
                        <p className="text-sm text-blue-600 font-medium">Total Users</p>
                        <p className="text-2xl font-bold text-blue-900">{userStats.total_users}</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-green-50 rounded-lg p-6" title="Total Documents">
                    <div className="flex items-center">
                      <FileText className="w-8 h-8 text-green-600 mr-3" />
                      <div>
                        <p className="text-sm text-green-600 font-medium">Total Documents</p>
                        <p className="text-2xl font-bold text-green-900">{documentStats.total_documents}</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-6" title="Storage Usage">
                    <div className="flex items-center">
                      <FileText className="w-8 h-8 text-purple-600 mr-3" />
                      <div>
                        <p className="text-sm text-purple-600 font-medium">Storage Usage</p>
                        <p className="text-2xl font-bold text-purple-900">{formatFileSize(documentStats.total_size_bytes)}</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-orange-50 rounded-lg p-6" title="Active Users">
                    <div className="flex items-center">
                      <Users className="w-8 h-8 text-orange-600 mr-3" />
                      <div>
                        <p className="text-sm text-orange-600 font-medium">Active Users</p>
                        <p className="text-2xl font-bold text-orange-900">{userStats.active_users}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'documents' && (
                <div>
                  <div className="flex justify-between items-center mb-6">
                    <input
                      type="text"
                      placeholder="Search documents..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                    />
                    <label className="cursor-pointer px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                      <input
                        type="file"
                        onChange={handleFileUpload}
                        className="hidden"
                        accept=".pdf,.doc,.docx,.txt,.md"
                        disabled={uploading}
                      />
                      {uploading ? 'Uploading...' : 'Upload Document'}
                    </label>
                  </div>

                  {filteredDocuments.length === 0 ? (
                    <div className="text-center py-12">
                      <div className="text-gray-500">
                        {searchTerm ? 'No matching documents found' : 'No documents'}
                      </div>
                      <div className="text-sm text-gray-400 mt-2">
                        {searchTerm ? 'Try different search terms' : 'Start by uploading your first document'}
                      </div>
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-gray-200">
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Filename</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Size</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Chunks</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Upload Time</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredDocuments.map((doc) => (
                            <tr key={doc.file_id} className="border-b border-gray-100 hover:bg-gray-50">
                              <td className="px-4 py-3">
                                <div className="font-medium text-gray-900 truncate max-w-xs">{doc.filename}</div>
                              </td>
                              <td className="px-4 py-3 text-gray-600">{formatFileSize(doc.file_size)}</td>
                              <td className="px-4 py-3 text-gray-600">{doc.chunks_count}</td>
                              <td className="px-4 py-3 text-gray-600">{formatLosAngelesDate(doc.upload_time)}</td>
                              <td className="px-4 py-3">
                                <div className="flex space-x-2">
                                  <button
                                    onClick={() => handleDownload(doc.file_id, doc.filename)}
                                    className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                                    title="Download"
                                  >
                                    <Download className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() => handleDelete(doc.file_id, doc.filename)}
                                    className="p-1 text-red-600 hover:bg-red-50 rounded"
                                    title="Delete"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <div className="mt-4 text-sm text-gray-600">
                        Showing {filteredDocuments.length} / {documents.length} documents
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'images' && (
                <ImageManagement isOpen={activeTab === 'images'} />
              )}

              {activeTab === 'users' && (
                <div>
                  <div className="mb-6">
                    <p className="text-sm text-gray-600">Total {users.length} users</p>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created At</th>
                        </tr>
                      </thead>
                      <tbody>
                        {users.map((user) => (
                          <tr key={user.id} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="px-4 py-3">
                              <div className="font-medium text-gray-900">{user.email}</div>
                            </td>
                            <td className="px-4 py-3 text-gray-600">{user.full_name || '-'}</td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-1 text-xs rounded-full ${user.role === 'admin'
                                ? 'bg-purple-100 text-purple-800'
                                : 'bg-gray-100 text-gray-800'
                                }`}>
                                {user.role === 'admin' ? 'Admin' : 'User'}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`px-2 py-1 text-xs rounded-full ${user.is_active
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                                }`}>
                                {user.is_active ? 'Active' : 'Inactive'}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-gray-600">{formatLosAngelesDate(user.created_at)}</td>
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