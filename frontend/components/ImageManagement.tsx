'use client'

import { useState, useEffect } from 'react'
import { Upload, Trash2, Image as ImageIcon, Package, Download, CheckCircle, XCircle } from 'lucide-react'
import { toast } from './Toast'
import { confirm } from './ConfirmDialog'
import apiClient from '@/lib/api'

interface ImageTag {
    id: number
    name: string
    created_at: string
}

interface ImageData {
    id: number
    file_id: string
    filename: string
    original_filename: string
    file_size: number
    mime_type: string
    storage_path: string
    thumbnail_path: string | null
    description: string | null
    alt_text: string | null
    user_id: number
    tags: ImageTag[]
    created_at: string
    updated_at: string
}

interface BatchUploadResult {
    filename: string
    success: boolean
    error?: string
    image_id?: number
}

interface BatchUploadResponse {
    total: number
    success_count: number
    failed_count: number
    results: BatchUploadResult[]
}

interface ImageManagementProps {
    isOpen: boolean
}

export default function ImageManagement({ isOpen }: ImageManagementProps) {
    const [images, setImages] = useState<ImageData[]>([])
    const [loading, setLoading] = useState(false)
    const [uploading, setUploading] = useState(false)
    const [batchUploading, setBatchUploading] = useState(false)
    const [selectedImage, setSelectedImage] = useState<File | null>(null)
    const [description, setDescription] = useState('')
    const [showUploadForm, setShowUploadForm] = useState(false)
    const [showBatchUploadForm, setShowBatchUploadForm] = useState(false)
    const [batchResults, setBatchResults] = useState<BatchUploadResponse | null>(null)

    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    const loadImages = async () => {
        try {
            const response = await apiClient.get('/images?page=1&page_size=100')
            setImages(response.data.images)
        } catch (error: any) {
            console.error('Failed to load images:', error)
            toast.error('Failed to load images')
        }
    }

    useEffect(() => {
        if (isOpen) {
            setLoading(true)
            loadImages().finally(() => setLoading(false))
        }
    }, [isOpen])

    // 单图上传
    const handleImageUpload = async () => {
        if (!selectedImage) {
            toast.error('Please select an image')
            return
        }

        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if (!allowedTypes.includes(selectedImage.type)) {
            toast.error('Unsupported image format. Supported: JPEG, PNG, GIF, WebP')
            return
        }

        if (selectedImage.size > 10 * 1024 * 1024) {
            toast.error('Image size cannot exceed 10MB')
            return
        }

        if (!description || !description.trim()) {
            toast.error('Please enter a description for the image')
            return
        }

        try {
            setUploading(true)
            const formData = new FormData()
            formData.append('file', selectedImage)
            formData.append('description', description.trim())

            await apiClient.post('/images/upload', formData)

            toast.success('Image uploaded successfully!')
            setSelectedImage(null)
            setDescription('')
            setShowUploadForm(false)
            await loadImages()
        } catch (error: any) {
            console.error('Upload failed:', error)
            toast.error(error.response?.data?.detail || 'Upload failed')
        } finally {
            setUploading(false)
        }
    }

    // 批量上传 (ZIP)
    const handleBatchUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        if (!file.name.toLowerCase().endsWith('.zip')) {
            toast.error('Please upload a ZIP file')
            return
        }

        if (file.size > 100 * 1024 * 1024) {
            toast.error('ZIP file size cannot exceed 100MB')
            return
        }

        try {
            setBatchUploading(true)
            setBatchResults(null)

            const formData = new FormData()
            formData.append('file', file)

            const response = await apiClient.post('/images/batch', formData)
            const result: BatchUploadResponse = response.data

            setBatchResults(result)

            if (result.failed_count === 0) {
                toast.success(`Successfully uploaded ${result.success_count} images!`)
            } else {
                toast.warning(`Uploaded ${result.success_count} images, ${result.failed_count} failed`)
            }

            await loadImages()
        } catch (error: any) {
            console.error('Batch upload failed:', error)
            toast.error(error.response?.data?.detail || 'Batch upload failed')
        } finally {
            setBatchUploading(false)
            // 重置 input
            e.target.value = ''
        }
    }

    // 下载 CSV 模板
    const handleDownloadTemplate = async () => {
        try {
            const response = await apiClient.get('/images/batch/template', {
                responseType: 'blob'
            })
            const url = window.URL.createObjectURL(new Blob([response.data]))
            const link = document.createElement('a')
            link.href = url
            link.setAttribute('download', 'images_template.csv')
            document.body.appendChild(link)
            link.click()
            link.remove()
            window.URL.revokeObjectURL(url)
        } catch (error: any) {
            console.error('Download template failed:', error)
            toast.error('Failed to download template')
        }
    }

    const handleDeleteImage = async (imageId: number, filename: string) => {
        const confirmed = await confirm(
            `Are you sure you want to delete "${filename}"?\n\nThis action cannot be undone!`,
            {
                title: 'Delete Image',
                confirmText: 'Delete',
                cancelText: 'Cancel',
            }
        )

        if (!confirmed) return

        try {
            await apiClient.delete(`/images/${imageId}`)
            toast.success('Image deleted successfully')
            await loadImages()
        } catch (error: any) {
            console.error('Delete failed:', error)
            toast.error('Failed to delete image')
        }
    }

    const formatFileSize = (bytes: number) => {
        const sizes = ['Bytes', 'KB', 'MB', 'GB']
        if (bytes === 0) return '0 Bytes'
        const i = Math.floor(Math.log(bytes) / Math.log(1024))
        return Math.round((bytes / Math.pow(1024, i)) * 100) / 100 + ' ' + sizes[i]
    }

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString('en-US', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        })
    }

    if (!isOpen) return null

    return (
        <div>
            {/* Header Actions */}
            <div className="flex justify-between items-center mb-6">
                <div className="flex gap-3">
                    <button
                        onClick={() => {
                            setShowUploadForm(!showUploadForm)
                            setShowBatchUploadForm(false)
                        }}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                    >
                        <Upload className="w-4 h-4" />
                        Upload Image
                    </button>
                    <button
                        onClick={() => {
                            setShowBatchUploadForm(!showBatchUploadForm)
                            setShowUploadForm(false)
                        }}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                    >
                        <Package className="w-4 h-4" />
                        Batch Upload (ZIP)
                    </button>
                </div>
            </div>

            {/* Single Image Upload Form */}
            {showUploadForm && (
                <div className="bg-gray-50 rounded-lg p-6 mb-6">
                    <h3 className="text-lg font-semibold mb-4">Upload Single Image</h3>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Image File *
                            </label>
                            <input
                                type="file"
                                accept="image/jpeg,image/png,image/gif,image/webp"
                                onChange={(e) => setSelectedImage(e.target.files?.[0] || null)}
                                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Supported formats: JPEG, PNG, GIF, WebP (Max 10MB)
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Description *
                            </label>
                            <textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="Describe the image content in detail. This description will be used to match user questions."
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                                rows={4}
                                required
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                💡 Tip: Include keywords that users might search for
                            </p>
                        </div>

                        <div className="flex gap-2">
                            <button
                                onClick={handleImageUpload}
                                disabled={!selectedImage || !description.trim() || uploading}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {uploading ? 'Uploading...' : 'Upload'}
                            </button>
                            <button
                                onClick={() => {
                                    setShowUploadForm(false)
                                    setSelectedImage(null)
                                    setDescription('')
                                }}
                                className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Batch Upload Form */}
            {showBatchUploadForm && (
                <div className="bg-green-50 rounded-lg p-6 mb-6">
                    <h3 className="text-lg font-semibold mb-4">Batch Upload (ZIP + CSV)</h3>
                    <div className="space-y-4">
                        <div className="bg-white rounded-lg p-4 border border-green-200">
                            <h4 className="font-medium mb-2">📦 How to use:</h4>
                            <ol className="text-sm text-gray-600 space-y-1 list-decimal list-inside">
                                <li>Create a ZIP file containing your images</li>
                                <li>Add an <code className="bg-gray-100 px-1 rounded">images.csv</code> file with descriptions</li>
                                <li>CSV format: <code className="bg-gray-100 px-1 rounded">filename,description</code></li>
                                <li>Upload the ZIP file</li>
                            </ol>
                            <button
                                onClick={handleDownloadTemplate}
                                className="mt-3 text-sm text-green-600 hover:text-green-700 flex items-center gap-1"
                            >
                                <Download className="w-4 h-4" />
                                Download CSV Template
                            </button>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                ZIP File *
                            </label>
                            <input
                                type="file"
                                accept=".zip"
                                onChange={handleBatchUpload}
                                disabled={batchUploading}
                                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100 disabled:opacity-50"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Max 100MB. Images without CSV entry will use filename as description.
                            </p>
                        </div>

                        {batchUploading && (
                            <div className="flex items-center gap-2 text-green-600">
                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-green-600"></div>
                                <span>Processing ZIP file...</span>
                            </div>
                        )}

                        {/* Batch Upload Results */}
                        {batchResults && (
                            <div className="bg-white rounded-lg p-4 border border-gray-200">
                                <h4 className="font-medium mb-3">Upload Results</h4>
                                <div className="flex gap-4 mb-3">
                                    <span className="text-sm">
                                        Total: <strong>{batchResults.total}</strong>
                                    </span>
                                    <span className="text-sm text-green-600">
                                        ✓ Success: <strong>{batchResults.success_count}</strong>
                                    </span>
                                    {batchResults.failed_count > 0 && (
                                        <span className="text-sm text-red-600">
                                            ✗ Failed: <strong>{batchResults.failed_count}</strong>
                                        </span>
                                    )}
                                </div>
                                <div className="max-h-40 overflow-y-auto">
                                    {batchResults.results.map((result, idx) => (
                                        <div
                                            key={idx}
                                            className={`flex items-center gap-2 py-1 text-sm ${result.success ? 'text-green-600' : 'text-red-600'
                                                }`}
                                        >
                                            {result.success ? (
                                                <CheckCircle className="w-4 h-4" />
                                            ) : (
                                                <XCircle className="w-4 h-4" />
                                            )}
                                            <span>{result.filename}</span>
                                            {result.error && (
                                                <span className="text-gray-500">- {result.error}</span>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <button
                            onClick={() => {
                                setShowBatchUploadForm(false)
                                setBatchResults(null)
                            }}
                            className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
                        >
                            Close
                        </button>
                    </div>
                </div>
            )}

            {/* Images Grid */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <div className="text-gray-600">Loading...</div>
                </div>
            ) : images.length === 0 ? (
                <div className="text-center py-12">
                    <ImageIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <div className="text-gray-500">No images uploaded yet</div>
                    <div className="text-sm text-gray-400 mt-2">
                        Click &quot;Upload Image&quot; or &quot;Batch Upload&quot; to add images
                    </div>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {images.map((image) => (
                        <div
                            key={image.id}
                            className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
                        >
                            <div className="aspect-video bg-gray-100 relative">
                                <img
                                    src={`${API_URL}/api/v1/images/${image.id}/file?thumbnail=true`}
                                    alt={image.alt_text || image.description || 'Image'}
                                    className="w-full h-full object-cover cursor-pointer"
                                    onClick={() =>
                                        window.open(`${API_URL}/api/v1/images/${image.id}/file`, '_blank')
                                    }
                                />
                            </div>
                            <div className="p-4">
                                <h4 className="font-medium text-gray-900 truncate mb-2">
                                    {image.original_filename}
                                </h4>
                                {image.description && (
                                    <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                                        {image.description}
                                    </p>
                                )}
                                <div className="flex flex-wrap gap-1 mb-3">
                                    {image.tags.map((tag) => (
                                        <span
                                            key={tag.id}
                                            className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded"
                                        >
                                            {tag.name}
                                        </span>
                                    ))}
                                </div>
                                <div className="flex justify-between items-center text-xs text-gray-500">
                                    <span>{formatFileSize(image.file_size)}</span>
                                    <span>{formatDate(image.created_at)}</span>
                                </div>
                                <div className="mt-3 flex gap-2">
                                    <button
                                        onClick={() => handleDeleteImage(image.id, image.original_filename)}
                                        className="flex-1 px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors flex items-center justify-center gap-2"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                        Delete
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Stats */}
            {images.length > 0 && (
                <div className="mt-6 text-sm text-gray-600">
                    Total: {images.length} images
                </div>
            )}
        </div>
    )
}
