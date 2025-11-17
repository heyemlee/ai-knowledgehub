import { getRequestConfig } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { LOCALES, DEFAULT_LOCALE } from './constants/locales'
import type { Locale as LocaleType } from './constants/locales'

export const locales = LOCALES;
export const defaultLocale = DEFAULT_LOCALE;

export type Locale = LocaleType;

export default getRequestConfig(async ({ locale }) => {
  // Validate that the incoming `locale` parameter is valid
  if (!locales.includes(locale as Locale)) notFound();

  return {
    locale: locale as Locale,
    messages: (await import(`./messages/${locale}.json`)).default
  };
});

















