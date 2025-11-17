import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { ToastContainer } from '@/components/Toast'
import { ConfirmDialogContainer } from '@/components/ConfirmDialog'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'ABC AI Knowledge Hub',
  description: '企业级知识库系统 - 智能问答平台',
}

export default function LocaleLayout({
  children,
  params: { locale }
}: {
  children: React.ReactNode
  params: { locale: string }
}) {
  return (
    <html lang={locale}>
      <body className={inter.className}>
        {children}
        <ToastContainer />
        <ConfirmDialogContainer />
      </body>
    </html>
  )
}




















