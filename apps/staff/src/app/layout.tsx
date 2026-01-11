import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AcuCare - Staff Console',
  description: 'UK Private Psychiatric Clinic Staff Console',
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
