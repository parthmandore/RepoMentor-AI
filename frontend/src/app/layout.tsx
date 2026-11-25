import './globals.css';
import type { Metadata, Viewport } from 'next';
import { ThemeProvider } from './ThemeProvider';
import { ToastProvider } from './ToastProvider';
import StructuredData from './components/StructuredData';
import CookieConsent from './components/CookieConsent';

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#F4F1EA' },
    { media: '(prefers-color-scheme: dark)', color: '#121110' },
  ],
};

export const metadata: Metadata = {
  metadataBase: new URL('https://repomentor.netlify.app'),
  title: {
    default: 'RepoMentor AI — Automated Repository Evaluation & Field Report',
    template: '%s | RepoMentor AI',
  },
  description: 'Automated repository quality analysis, cyclomatic complexity grading, security vulnerability scanning, and evidence-grounded AI Code Mentorship.',
  keywords: [
    'code quality',
    'repository evaluation',
    'static analysis',
    'code smells',
    'cyclomatic complexity',
    'security vulnerability scanner',
    'architecture dependency graph',
    'AI code mentor',
    'RAG codebase search',
    'software architecture',
  ],
  authors: [{ name: 'Parth Mandore', url: 'https://github.com/parthmandore' }],
  creator: 'Parth Mandore',
  publisher: 'RepoMentor AI',
  alternates: {
    canonical: 'https://repomentor.netlify.app',
  },
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/favicon.svg', type: 'image/svg+xml' },
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
    ],
    apple: [
      { url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
    other: [
      {
        rel: 'android-chrome-192x192',
        url: '/android-chrome-192x192.png',
      },
      {
        rel: 'android-chrome-512x512',
        url: '/android-chrome-512x512.png',
      },
    ],
  },
  manifest: '/site.webmanifest',
  openGraph: {
    title: 'RepoMentor AI — Automated Repository Evaluation & Field Report',
    description: 'Automated repository quality analysis, cyclomatic complexity grading, security vulnerability scanning, and evidence-grounded AI Code Mentorship.',
    url: 'https://repomentor.netlify.app',
    siteName: 'RepoMentor AI',
    locale: 'en_US',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'RepoMentor AI — Automated Repository Evaluation & Field Report',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'RepoMentor AI — Automated Repository Evaluation & Field Report',
    description: 'Automated repository quality analysis, cyclomatic complexity grading, security vulnerability scanning, and evidence-grounded AI Code Mentorship.',
    images: ['/og-image.png'],
    creator: '@parthmandore',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <StructuredData />
      </head>
      <body className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col justify-between antialiased selection:bg-signal selection:text-white">
        <ThemeProvider>
          <ToastProvider>
            {children}
            <CookieConsent />
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
