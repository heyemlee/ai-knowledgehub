import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const locales = ['zh-CN', 'en-US']
const defaultLocale = 'en-US'

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname

  // 已经是带 locale 的路径，直接放行
  if (locales.some((loc) => pathname.startsWith(`/${loc}/`) || pathname === `/${loc}`)) {
    return NextResponse.next()
  }

  // 静态资源自动跳过
  if (pathname.startsWith('/_next') || pathname.startsWith('/favicon.ico')) {
    return NextResponse.next()
  }

  // 根路径 → 重定向到默认语言
  if (pathname === '/') {
    const url = request.nextUrl.clone()
    url.pathname = `/${defaultLocale}`
    return NextResponse.redirect(url)
  }

  // 非法路径：自动补上 locale
  const url = request.nextUrl.clone()
  url.pathname = `/${defaultLocale}${pathname}`
  return NextResponse.redirect(url)
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|_next/data|favicon.ico).*)',
  ],
}
