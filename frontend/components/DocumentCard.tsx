'use client'

import { Download, Eye, FileText } from 'lucide-react'
import { toast } from './Toast'

interface DocumentReference {
    file_id: string
    filename: string
    title?: string
    summary?: string
    preview_url: string
    download_url: string
    relevance_score?: number
}

interface DocumentCardProps {
    document: DocumentReference
}

export default function DocumentCard({ document }: DocumentCardProps) {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    const handlePreview = async () => {
        try {
            // 使用认证 token 获取 PDF 文件
            const previewUrl = `${API_URL}${document.preview_url}`
            const response = await fetch(previewUrl, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            })

            if (!response.ok) throw new Error('Preview failed')

            const blob = await response.blob()
            const url = window.URL.createObjectURL(blob)
            // 在新标签页打开 blob URL
            window.open(url, '_blank')
        } catch (error) {
            console.error('Failed to preview document:', error)
            toast.error('Failed to preview document')
        }
    }

    const handleDownload = async () => {
        try {
            const downloadUrl = `${API_URL}${document.download_url}`
            const response = await fetch(downloadUrl, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            })

            if (!response.ok) throw new Error('Download failed')

            const blob = await response.blob()
            const url = window.URL.createObjectURL(blob)
            const a = window.document.createElement('a')
            a.href = url
            a.download = document.filename
            window.document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
            window.document.body.removeChild(a)

            toast.success('Document downloaded')
        } catch (error) {
            console.error('Failed to download document:', error)
            toast.error('Failed to download document')
        }
    }

    return (
        <div className="group bg-white border border-gray-200 rounded-xl p-4 hover:border-gray-400 hover:shadow-md transition-all">
            {/* 文档图标和标题 */}
            <div className="flex items-start gap-3 mb-3">
                <div className="flex-shrink-0 w-12 h-12 bg-red-50 rounded-lg flex items-center justify-center">
                    <FileText size={24} className="text-red-600" />
                </div>
                <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 truncate">
                        {document.title || document.filename}
                    </h3>
                    <p className="text-sm text-gray-500 truncate">
                        {document.filename}
                    </p>
                </div>
            </div>

            {/* 摘要 */}
            {document.summary && (
                <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                    {document.summary}
                </p>
            )}

            {/* 操作按钮 */}
            <div className="flex gap-2">
                <button
                    onClick={handlePreview}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors text-sm font-medium"
                >
                    <Eye size={16} />
                    Preview
                </button>
                <button
                    onClick={handleDownload}
                    className="flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
                >
                    <Download size={16} />
                    Download
                </button>
            </div>

            {/* 相关度（可选显示） */}
            {document.relevance_score && document.relevance_score > 0 && (
                <div className="mt-2 text-xs text-gray-400 text-right">
                    Relevance: {Math.round(document.relevance_score * 100)}%
                </div>
            )}
        </div>
    )
}
