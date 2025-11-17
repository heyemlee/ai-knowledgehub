export const runtime = "nodejs";

import {NextIntlClientProvider} from 'next-intl';
import {getMessages} from 'next-intl/server';
import {Inter} from 'next/font/google';
import {ToastContainer} from '@/components/Toast';
import {ConfirmDialogContainer} from '@/components/ConfirmDialog';

const inter = Inter({subsets: ['latin']});

export default async function LocaleLayout({
  children,
  params: {locale}
}: {
  children: React.ReactNode;
  params: {locale: string};
}) {
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body className={inter.className}>
        <NextIntlClientProvider messages={messages}>
          {children}
        </NextIntlClientProvider>
        <ToastContainer />
        <ConfirmDialogContainer />
      </body>
    </html>
  );
}