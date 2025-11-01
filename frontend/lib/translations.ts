import { usePathname } from 'next/navigation'
import enUS from '@/messages/en-US.json'
import zhCN from '@/messages/zh-CN.json'

type Translations = typeof enUS

function getTranslations(locale: string): Translations {
  return locale === 'zh-CN' ? zhCN : enUS
}

function getTranslationValue(obj: any, path: string): string {
  const keys = path.split('.')
  let value = obj
  for (const key of keys) {
    value = value?.[key]
    if (value === undefined) return path
  }
  return typeof value === 'string' ? value : path
}

export function useTranslations() {
  const pathname = usePathname()
  const segments = pathname.split('/')
  const locale = segments[1] && ['zh-CN', 'en-US'].includes(segments[1]) ? segments[1] : 'en-US'
  const t = getTranslations(locale)

  return {
    t: (key: string, params?: Record<string, string | number>): string => {
      const translation = getTranslationValue(t, key)
      if (params) {
        return translation.replace(/\{(\w+)\}/g, (match, paramKey) => {
          return params[paramKey]?.toString() || match
        })
      }
      return translation
    },
    locale
  }
}

