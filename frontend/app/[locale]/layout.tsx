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
  return (
    <html lang={locale}>
      <body className={inter.className}>
        {children}
        <ToastContainer />
        <ConfirmDialogContainer />
      </body>
    </html>
  );
}