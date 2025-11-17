import createMiddleware from 'next-intl/middleware';

export default createMiddleware({
  locales: ['en-US', 'zh-CN'],
  defaultLocale: 'en-US'
});

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)']
};