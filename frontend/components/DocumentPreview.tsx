'use client'

import { useState, useEffect } from 'react'
import { X, Download, FileText } from 'lucide-react'

interface DocumentPreviewProps {
  fileId: string
  filename: string
  fileType: string
  onClose: () => void
}

export default function DocumentPreview({
  fileId,
  filename,
  fileType,
  onClose,
}: DocumentPreviewProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const previewUrl = `/api/v1/documents/${fileId}/preview`
  const downloadUrl = `/api/v1/documents/${fileId}/download`
  
  const fileExtension = filename.split('.').pop()?.toLowerCase() || ''
  const isPdf = fileExtension === 'pdf'
  const isText = fileExtension === 'txt'
  const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(fileExtension)

  useEffect(() => {
    setLoading(true)
    setError(null)
  }, [fileId])

  const handleDownload = () => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const token = localStorage.getItem('access_token')
    const url = `${API_URL}${downloadUrl}`
    
    fetch(url, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      })
      .catch((err) => {
        console.error('下载失败:', err)
        alert('下载失败，请稍后重试')
      })
  }

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const token = localStorage.getItem('access_token')
  
  // 创建带认证的预览 URL
  // 由于 iframe 和 img 无法直接设置 Authorization header，
  // 我们需要先通过 fetch 获取内容，然后创建 blob URL
  const [previewBlobUrl, setPreviewBlobUrl] = useState<string | null>(null)
  
  useEffect(() => {
    if (!fileId) return
    
    let currentBlobUrl: string | null = null
    
    const loadPreview = async () => {
      try {
        setLoading(true)
        setError(null)
        const url = `${API_URL}${previewUrl}`
        const response = await fetch(url, {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        })
        
        if (!response.ok) {
          throw new Error('加载预览失败')
        }
        
        const blob = await response.blob()
        const blobUrl = URL.createObjectURL(blob)
        currentBlobUrl = blobUrl
        setPreviewBlobUrl(blobUrl)
        setLoading(false)
      } catch (err) {
        setError('预览加载失败')
        setLoading(false)
      }
    }
    
    loadPreview()
    
    return () => {
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl)
      }
    }
  }, [fileId, token, previewUrl])
  
  const fullPreviewUrl = previewBlobUrl || `${API_URL}${previewUrl}`

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-gray-600" />
            <h2 className="text-lg font-semibold text-gray-800 truncate max-w-md">
              {filename}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              title="下载文档"
            >
              <Download size={16} />
              下载
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
        <div className="flex-1 overflow-auto p-4 relative">
          {isPdf && previewBlobUrl ? (
            <iframe
              src={previewBlobUrl}
              className="w-full h-full min-h-[600px] border-0"
              title={filename}
            />
          ) : isText && previewBlobUrl ? (
            <iframe
              src={previewBlobUrl}
              className="w-full h-full min-h-[400px] border border-gray-200 rounded"
              title={filename}
            />
          ) : isImage && previewBlobUrl ? (
            <div className="flex items-center justify-center">
              <img
                src={previewBlobUrl}
                alt={filename}
                className="max-w-full max-h-[70vh] object-contain"
              />
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <FileText className="w-16 h-16 mb-4 text-gray-300" />
              <p className="text-lg mb-2">不支持在线预览</p>
              <p className="text-sm">文件类型: {fileType}</p>
            </div>
          )}

          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90">
              <div className="text-center">
                <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                <p className="text-sm text-gray-600">加载中...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center h-full text-red-500">
              <p className="text-lg">{error}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

