import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/hooks/useAuth';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: 'WalchandGPT — AI College Assistant',
  description:
    'AI-powered college assistant for Walchand College of Engineering. Get instant answers about academics, faculty, timetables, notices, and more.',
  keywords: ['WalchandGPT', 'WCE', 'Walchand', 'AI', 'college assistant'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
