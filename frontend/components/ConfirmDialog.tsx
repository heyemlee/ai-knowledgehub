'use client'

import { useState, useCallback } from 'react'
import { create } from 'zustand'
import { X, AlertTriangle } from 'lucide-react'

export interface ConfirmDialog {
  id: string
  message: string
  title?: string
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  onCancel?: () => void
}

interface ConfirmStore {
  dialogs: ConfirmDialog[]
  showConfirm: (dialog: Omit<ConfirmDialog, 'id'>) => void
  removeDialog: (id: string) => void
}

const useConfirmStore = create<ConfirmStore>((set) => ({
  dialogs: [],
  showConfirm: (dialog) => {
    const id = Math.random().toString(36).substring(7)
    set((state) => ({
      dialogs: [...state.dialogs, { ...dialog, id }],
    }))
    return id
  },
  removeDialog: (id) => {
    set((state) => ({
      dialogs: state.dialogs.filter((dialog) => dialog.id !== id),
    }))
  },
}))

export const useConfirm = () => {
  const showConfirm = useConfirmStore((state) => state.showConfirm)
  
  return useCallback(
    (
      message: string,
      options?: {
        title?: string
        confirmText?: string
        cancelText?: string
      }
    ): Promise<boolean> => {
      return new Promise((resolve) => {
        showConfirm({
          message,
          title: options?.title,
          confirmText: options?.confirmText,
          cancelText: options?.cancelText,
          onConfirm: () => {
            resolve(true)
          },
          onCancel: () => {
            resolve(false)
          },
        })
      })
    },
    [showConfirm]
  )
}

export const confirm = (
  message: string,
  options?: {
    title?: string
    confirmText?: string
    cancelText?: string
  }
): Promise<boolean> => {
  return new Promise((resolve) => {
    useConfirmStore.getState().showConfirm({
      message,
      title: options?.title,
      confirmText: options?.confirmText,
      cancelText: options?.cancelText,
      onConfirm: () => {
        resolve(true)
      },
      onCancel: () => {
        resolve(false)
      },
    })
  })
}

function ConfirmDialogItem({ dialog }: { dialog: ConfirmDialog }) {
  const removeDialog = useConfirmStore((state) => state.removeDialog)
  
  const handleConfirm = () => {
    dialog.onConfirm()
    removeDialog(dialog.id)
  }
  
  const handleCancel = () => {
    if (dialog.onCancel) {
      dialog.onCancel()
    }
    removeDialog(dialog.id)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* 遮罩 */}
      <div
        className="absolute inset-0 bg-black/50 transition-opacity"
        onClick={handleCancel}
      />
      
      {/* 对话框 */}
      <div className="relative bg-white rounded-2xl shadow-2xl border border-gray-200 max-w-md w-full animate-scale-in">
        <div className="p-6">
          {/* 标题 */}
          {dialog.title && (
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-shrink-0 w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-yellow-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">
                {dialog.title}
              </h3>
            </div>
          )}
          
          {/* 消息 */}
          <div className={`${dialog.title ? 'mb-6' : 'mb-6'}`}>
            <p className="text-gray-700 whitespace-pre-line">
              {dialog.message}
            </p>
          </div>
          
          {/* 按钮 */}
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={handleCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              {dialog.cancelText || '取消'}
            </button>
            <button
              onClick={handleConfirm}
              className="px-4 py-2 text-sm font-medium text-white bg-black hover:bg-gray-800 rounded-lg transition-colors"
            >
              {dialog.confirmText || '确认'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export function ConfirmDialogContainer() {
  const dialogs = useConfirmStore((state) => state.dialogs)

  if (dialogs.length === 0) return null

  return (
    <>
      {dialogs.map((dialog) => (
        <ConfirmDialogItem key={dialog.id} dialog={dialog} />
      ))}
    </>
  )
}

