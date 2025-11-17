import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'ABC AI Knowledge Hub',
  description: '企业级知识库系统 - 智能问答平台',
}

export default function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: { locale: string }
}) {
  return <>{children}</>
}




















