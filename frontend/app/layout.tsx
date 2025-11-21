import { Inter } from 'next/font/google'
import './globals.css'
import { ToastContainer } from '@/components/Toast'
import { ConfirmDialogContainer } from '@/components/ConfirmDialog'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'ABC AI Hub',
  description: 'AI Knowledge Hub',
  viewport: 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0',
}

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

