import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// 支持的语言列表
const locales = ['zh-CN', 'en-US']
const defaultLocale = 'en-US'

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname

  // 根路径，已经有 page.tsx 处理重定向
  if (pathname === '/') {
    return NextResponse.next()
  }

  // 提取第一个路径段作为 locale
  const segments = pathname.split('/')
  const potentialLocale = segments[1]

  // 检查是否是有效的语言代码
  if (potentialLocale && !locales.includes(potentialLocale)) {
    // 如果不是有效的语言代码，重定向到默认语言 + 原路径
    const url = request.nextUrl.clone()
    url.pathname = `/${defaultLocale}${pathname}`
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  // 匹配所有路径，除了 api、_next/static、_next/image、favicon.ico
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
