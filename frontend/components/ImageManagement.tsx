'use client'

import { useState, useEffect } from 'react'
import { X, Upload, Trash2, Edit, Image as ImageIcon, Tag } from 'lucide-react'
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

interface ImageManagementProps {
    isOpen: boolean
}

export default function ImageManagement({ isOpen }: ImageManagementProps) {
    const [images, setImages] = useState<ImageData[]>([])
    const [tags, setTags] = useState<ImageTag[]>([])
    const [loading, setLoading] = useState(false)
    const [uploading, setUploading] = useState(false)
    const [selectedImage, setSelectedImage] = useState<File | null>(null)
    const [description, setDescription] = useState('')
    const [altText, setAltText] = useState('')
    const [selectedTags, setSelectedTags] = useState<number[]>([])
    const [newTagName, setNewTagName] = useState('')
    const [showUploadForm, setShowUploadForm] = useState(false)

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

    const loadTags = async () => {
        try {
            const response = await apiClient.get('/images/tags')
            setTags(response.data)
        } catch (error: any) {
            console.error('Failed to load tags:', error)
            toast.error('Failed to load tags')
        }
    }

    useEffect(() => {
        if (isOpen) {
            setLoading(true)
            Promise.all([loadImages(), loadTags()]).finally(() => setLoading(false))
        }
    }, [isOpen])

    const handleCreateTag = async () => {
        if (!newTagName.trim()) {
            toast.error('Please enter a tag name')
            return
        }

        try {
            await apiClient.post('/images/tags', { name: newTagName.trim() })
            toast.success('Tag created successfully')
            setNewTagName('')
            await loadTags()
        } catch (error: any) {
            console.error('Failed to create tag:', error)
            toast.error(error.response?.data?.detail || 'Failed to create tag')
        }
    }

    const handleImageUpload = async () => {
        if (!selectedImage) {
            toast.error('Please select an image')
            return
        }

        // Validate file type
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if (!allowedTypes.includes(selectedImage.type)) {
            toast.error('Unsupported image format. Supported: JPEG, PNG, GIF, WebP')
            return
        }

        // Validate file size (10MB)
        if (selectedImage.size > 10 * 1024 * 1024) {
            toast.error('Image size cannot exceed 10MB')
            return
        }

        try {
            setUploading(true)
            const formData = new FormData()
            formData.append('file', selectedImage)
            if (description) formData.append('description', description)
            if (altText) formData.append('alt_text', altText)
            if (selectedTags.length > 0) {
                formData.append('tag_ids', selectedTags.join(','))
            }

            await apiClient.post('/images/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            })

            toast.success('Image uploaded successfully!')
            setSelectedImage(null)
            setDescription('')
            setAltText('')
            setSelectedTags([])
            setShowUploadForm(false)
            await loadImages()
        } catch (error: any) {
            console.error('Upload failed:', error)
            toast.error(error.response?.data?.detail || 'Upload failed')
        } finally {
            setUploading(false)
        }
    }

    const handleDeleteImage = async (imageId: number, filename: string) => {
        const confirmed = await confirm(
            `Are you sure you want to delete "${filename}"?\\n\\nThis action cannot be undone!`,
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
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => setShowUploadForm(!showUploadForm)}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                    >
                        <Upload className="w-4 h-4" />
                        Upload Image
                    </button>
                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            placeholder="New tag name"
                            value={newTagName}
                            onChange={(e) => setNewTagName(e.target.value)}
                            className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                            onKeyPress={(e) => e.key === 'Enter' && handleCreateTag()}
                        />
                        <button
                            onClick={handleCreateTag}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                        >
                            <Tag className="w-4 h-4" />
                            Create Tag
                        </button>
                    </div>
                </div>
            </div>

            {/* Upload Form */}
            {showUploadForm && (
                <div className="bg-gray-50 rounded-lg p-6 mb-6">
                    <h3 className="text-lg font-semibold mb-4">Upload New Image</h3>
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
                                Description
                            </label>
                            <textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="Describe the image content (used for search)"
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                                rows={3}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Alt Text
                            </label>
                            <input
                                type="text"
                                value={altText}
                                onChange={(e) => setAltText(e.target.value)}
                                placeholder="Alternative text for accessibility"
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Tags
                            </label>
                            <div className="flex flex-wrap gap-2">
                                {tags.map((tag) => (
                                    <label
                                        key={tag.id}
                                        className="flex items-center gap-2 px-3 py-1 bg-white border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50"
                                    >
                                        <input
                                            type="checkbox"
                                            checked={selectedTags.includes(tag.id)}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    setSelectedTags([...selectedTags, tag.id])
                                                } else {
                                                    setSelectedTags(selectedTags.filter((id) => id !== tag.id))
                                                }
                                            }}
                                            className="rounded"
                                        />
                                        <span className="text-sm">{tag.name}</span>
                                    </label>
                                ))}
                            </div>
                        </div>

                        <div className="flex gap-2">
                            <button
                                onClick={handleImageUpload}
                                disabled={!selectedImage || uploading}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {uploading ? 'Uploading...' : 'Upload'}
                            </button>
                            <button
                                onClick={() => {
                                    setShowUploadForm(false)
                                    setSelectedImage(null)
                                    setDescription('')
                                    setAltText('')
                                    setSelectedTags([])
                                }}
                                className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
                            >
                                Cancel
                            </button>
                        </div>
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
                        Click "Upload Image" to add your first image
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
