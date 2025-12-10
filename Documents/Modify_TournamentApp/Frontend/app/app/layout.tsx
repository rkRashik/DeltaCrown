/**
 * Root Layout
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Root layout wraps all pages with providers and global components.
 * Integrates design tokens, accessibility, and responsive design.
 */

import type { Metadata } from 'next';
import { Inter, Poppins, Roboto_Mono } from 'next/font/google';
import '../styles/globals.css';

// Providers
import { ThemeProvider } from '../providers/ThemeProvider';
import { AuthProvider } from '../providers/AuthProvider';
import { QueryProvider } from '../providers/QueryProvider';
import { ToastProvider } from '../providers/ToastProvider';

// Layout Components
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';

// Font configurations
const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const poppins = Poppins({
  weight: ['400', '500', '600', '700'],
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
});

const robotoMono = Roboto_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

// Metadata
export const metadata: Metadata = {
  title: {
    default: 'DeltaCrown | Tournament Platform',
    template: '%s | DeltaCrown',
  },
  description: 'Professional esports tournament management platform for organizers and players.',
  keywords: [
    'esports',
    'tournaments',
    'gaming',
    'competitive',
    'brackets',
    'match management',
  ],
  authors: [{ name: 'DeltaCrown Team' }],
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 5, // Allow user zoom for accessibility
  },
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#3b82f6' },
    { media: '(prefers-color-scheme: dark)', color: '#1e3a8a' },
  ],
  manifest: '/manifest.json',
  icons: {
    icon: '/favicon.ico',
    apple: '/apple-touch-icon.png',
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://deltacrown.gg',
    siteName: 'DeltaCrown',
    title: 'DeltaCrown | Tournament Platform',
    description: 'Professional esports tournament management platform.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'DeltaCrown Tournament Platform',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@deltacrown',
    creator: '@deltacrown',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${poppins.variable} ${robotoMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Preconnect to external resources */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="antialiased custom-scrollbar">
        <ThemeProvider defaultTheme="system" storageKey="deltacrown-theme">
          <AuthProvider>
            <QueryProvider>
              <ToastProvider maxToasts={5}>
                <div className="flex h-screen overflow-hidden bg-neutral-50">
                  {/* Sidebar - Hidden on mobile, visible on desktop */}
                  <Sidebar />

                  {/* Main Content Area */}
                  <div className="flex flex-col flex-1 overflow-hidden">
                    {/* Header */}
                    <Header />

                    {/* Page Content */}
                    <main className="flex-1 overflow-y-auto bg-neutral-50 custom-scrollbar">
                      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-6">
                        {children}
                      </div>
                    </main>
                  </div>
                </div>

                {/* Skip to main content link (accessibility) */}
                <a
                  href="#main-content"
                  className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-tooltip focus:px-4 focus:py-2 focus:bg-brand-primary-600 focus:text-white focus:rounded-md"
                >
                  Skip to main content
                </a>
              </ToastProvider>
            </QueryProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
