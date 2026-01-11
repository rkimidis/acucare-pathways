import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AcuCare - Patient Portal',
  description: 'UK Private Psychiatric Clinic Patient Portal',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
