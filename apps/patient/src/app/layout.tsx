import type { Metadata } from 'next';
import { Sora, Source_Sans_3 } from 'next/font/google';
import './globals.css';

const headingFont = Sora({
  subsets: ['latin'],
  variable: '--font-heading',
  display: 'swap',
});

const bodyFont = Source_Sans_3({
  subsets: ['latin'],
  variable: '--font-body',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'AcuCare Pathways - Patient Portal',
  description: 'UK Private Psychiatric Clinic Patient Portal',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${headingFont.variable} ${bodyFont.variable}`}>
      <body>{children}</body>
    </html>
  );
}
