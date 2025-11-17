export const locales = ['en-US', 'zh-CN'] as const;

export const localePrefix = 'as-needed';

export const defaultLocale = 'en-US';

export type Locale = (typeof locales)[number];