import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // 简单放行所有请求
  return NextResponse.next()
}

export const config = {
  // 匹配所有路径，除了 api、_next/static、_next/image、favicon.ico
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
