import { Inter } from 'next/font/google'
import './globals.css'
import { ToastContainer } from '@/components/Toast'
import { ConfirmDialogContainer } from '@/components/ConfirmDialog'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html>
      <body className={inter.className}>
        {children}
        <ToastContainer />
        <ConfirmDialogContainer />
      </body>
    </html>
  )
}

