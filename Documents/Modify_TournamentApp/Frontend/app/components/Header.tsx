/**
 * Header Component
 * Phase 9, Epic 9.4 - Frontend Boilerplate Scaffolding
 * 
 * Top navigation header with mobile menu toggle, search, and user menu.
 * Responsive design: hamburger menu on mobile, full nav on desktop.
 */

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '../providers/AuthProvider';
import { useTheme } from '../providers/ThemeProvider';
import UserMenu from './UserMenu';

export default function Header() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { user, isAuthenticated } = useAuth();
  const { theme, setTheme } = useTheme();

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark');
  };

  return (
    <header className="bg-white border-b border-neutral-200 sticky top-0 z-sticky shadow-sm">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Mobile Menu Button */}
          <button
            type="button"
            className="lg:hidden p-2 rounded-md text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-brand-primary-500"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label="Toggle navigation menu"
            aria-expanded={isMobileMenuOpen}
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              {isMobileMenuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>

          {/* Logo */}
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2 focus-ring rounded-md px-2 py-1">
              <div className="w-8 h-8 bg-gradient-to-br from-brand-primary-600 to-brand-secondary-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">D</span>
              </div>
              <span className="hidden sm:block font-display font-bold text-xl text-gradient">
                DeltaCrown
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-6" aria-label="Primary navigation">
            <Link
              href="/tournaments"
              className="text-neutral-700 hover:text-brand-primary-600 font-medium transition-colors focus-ring rounded-md px-3 py-2"
            >
              Tournaments
            </Link>
            <Link
              href="/matches"
              className="text-neutral-700 hover:text-brand-primary-600 font-medium transition-colors focus-ring rounded-md px-3 py-2"
            >
              Matches
            </Link>
            <Link
              href="/analytics"
              className="text-neutral-700 hover:text-brand-primary-600 font-medium transition-colors focus-ring rounded-md px-3 py-2"
            >
              Analytics
            </Link>
            <Link
              href="/help"
              className="text-neutral-700 hover:text-brand-primary-600 font-medium transition-colors focus-ring rounded-md px-3 py-2"
            >
              Help
            </Link>
          </nav>

          {/* Actions */}
          <div className="flex items-center gap-3">
            {/* Theme Toggle */}
            <button
              type="button"
              onClick={toggleTheme}
              className="p-2 rounded-md text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 focus-ring"
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {theme === 'dark' ? (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                </svg>
              )}
            </button>

            {/* Notifications (placeholder) */}
            <button
              type="button"
              className="p-2 rounded-md text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 focus-ring relative"
              aria-label="View notifications"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
              </svg>
              {/* Notification badge */}
              <span className="absolute top-1 right-1 w-2 h-2 bg-error rounded-full"></span>
            </button>

            {/* User Menu */}
            {isAuthenticated && user ? (
              <UserMenu user={user} />
            ) : (
              <Link href="/login" className="btn btn-primary">
                Sign In
              </Link>
            )}
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <nav
            className="lg:hidden border-t border-neutral-200 py-4 space-y-2"
            aria-label="Mobile navigation"
          >
            <Link
              href="/tournaments"
              className="block px-4 py-2 text-neutral-700 hover:bg-neutral-100 hover:text-brand-primary-600 rounded-md transition-colors"
            >
              Tournaments
            </Link>
            <Link
              href="/matches"
              className="block px-4 py-2 text-neutral-700 hover:bg-neutral-100 hover:text-brand-primary-600 rounded-md transition-colors"
            >
              Matches
            </Link>
            <Link
              href="/analytics"
              className="block px-4 py-2 text-neutral-700 hover:bg-neutral-100 hover:text-brand-primary-600 rounded-md transition-colors"
            >
              Analytics
            </Link>
            <Link
              href="/help"
              className="block px-4 py-2 text-neutral-700 hover:bg-neutral-100 hover:text-brand-primary-600 rounded-md transition-colors"
            >
              Help
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
}
