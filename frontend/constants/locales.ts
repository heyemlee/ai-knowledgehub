export const LOCALES = ['en-US', 'zh-CN'] as const;
export const DEFAULT_LOCALE = 'en-US' as const;
export type Locale = (typeof LOCALES)[number];
