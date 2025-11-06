'use client'

import { useState, useCallback, useEffect } from 'react'
import { create } from 'zustand'
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface Toast {
  id: string
  message: string
  type: ToastType
  duration?: number
}

interface ToastStore {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (toast) => {
    const id = Math.random().toString(36).substring(7)
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id }],
    }))
    return id
  },
  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    }))
  },
}))

export const useToast = () => {
  const addToast = useToastStore((state) => state.addToast)
  
  return useCallback(
    (message: string, type: ToastType = 'info', duration: number = 5000) => {
      addToast({ message, type, duration })
    },
    [addToast]
  )
}

export const toast = {
  success: (message: string, duration?: number) => {
    useToastStore.getState().addToast({ message, type: 'success', duration })
  },
  error: (message: string, duration?: number) => {
    useToastStore.getState().addToast({ message, type: 'error', duration })
  },
  info: (message: string, duration?: number) => {
    useToastStore.getState().addToast({ message, type: 'info', duration })
  },
  warning: (message: string, duration?: number) => {
    useToastStore.getState().addToast({ message, type: 'warning', duration })
  },
}

function ToastItem({ toast: toastItem }: { toast: Toast }) {
  const removeToast = useToastStore((state) => state.removeToast)
  
  useEffect(() => {
    if (toastItem.duration !== 0) {
      const timer = setTimeout(() => {
        removeToast(toastItem.id)
      }, toastItem.duration || 5000)
      return () => clearTimeout(timer)
    }
  }, [toastItem.id, toastItem.duration, removeToast])

  const icons = {
    success: <CheckCircle className="w-5 h-5 text-green-500" />,
    error: <AlertCircle className="w-5 h-5 text-red-500" />,
    info: <Info className="w-5 h-5 text-blue-500" />,
    warning: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
  }

  const bgColors = {
    success: 'bg-green-50 border-green-200',
    error: 'bg-red-50 border-red-200',
    info: 'bg-blue-50 border-blue-200',
    warning: 'bg-yellow-50 border-yellow-200',
  }

  const textColors = {
    success: 'text-green-800',
    error: 'text-red-800',
    info: 'text-blue-800',
    warning: 'text-yellow-800',
  }

  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-xl border shadow-lg min-w-[300px] max-w-md animate-slide-in ${bgColors[toastItem.type]}`}
    >
      <div className="flex-shrink-0 mt-0.5">{icons[toastItem.type]}</div>
      <div className="flex-1">
        <p className={`text-sm font-medium ${textColors[toastItem.type]}`}>
          {toastItem.message}
        </p>
      </div>
      <button
        onClick={() => removeToast(toastItem.id)}
        className={`flex-shrink-0 p-1 rounded-lg hover:bg-black/5 transition-colors ${textColors[toastItem.type]}`}
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

export function ToastContainer() {
  const toasts = useToastStore((state) => state.toasts)

  if (toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-3 pointer-events-none">
      {toasts.map((toastItem) => (
        <div key={toastItem.id} className="pointer-events-auto">
          <ToastItem toast={toastItem} />
        </div>
      ))}
    </div>
  )
}

