'use client'

import { useState, useEffect } from 'react'
import ChatInterface from '@/components/ChatInterface'
import LoginForm from '@/components/LoginForm'
import { useAuthStore } from '@/store/authStore'

export default function Home() {
  const { isAuthenticated, checkAuth } = useAuthStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkAuth()
    setLoading(false)
  }, [checkAuth])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading...</div>
      </div>
    )
  }

  return (
    <main className="min-h-screen">
      {isAuthenticated ? <ChatInterface /> : <LoginForm />}
    </main>
  )
}

