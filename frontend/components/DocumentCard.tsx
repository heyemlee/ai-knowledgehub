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
        <div className="group bg-white border border-gray-200 rounded-xl p-3 hover:border-gray-400 hover:shadow-md transition-all">
            {/* 文档图标和文件名 */}
            <div className="flex items-center gap-3">
                <div className="flex-shrink-0 w-10 h-10 bg-red-50 rounded-lg flex items-center justify-center">
                    <FileText size={20} className="text-red-600" />
                </div>
                <h3 className="flex-1 font-medium text-gray-900 truncate text-sm">
                    {document.filename}
                </h3>
                {/* 操作按钮 */}
                <div className="flex gap-1">
                    <button
                        onClick={handlePreview}
                        className="p-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
                        title="Preview"
                    >
                        <Eye size={16} />
                    </button>
                    <button
                        onClick={handleDownload}
                        className="p-2 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                        title="Download"
                    >
                        <Download size={16} />
                    </button>
                </div>
            </div>
        </div>
    )
}
