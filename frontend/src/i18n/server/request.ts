import {getRequestConfig} from 'next-intl/server';
import {locales, defaultLocale} from '../../../i18n';

export default getRequestConfig(async ({locale}) => {
  const resolvedLocale = (locales.includes(locale as any) ? locale : defaultLocale) as string;

  return {
    locale: resolvedLocale,
    messages: (await import(`../../../messages/${resolvedLocale}.json`)).default
  };
});