'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log client error to console
    console.error('App-level error caught by ErrorBoundary:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary rounded-2xl p-8 shadow-lg text-center">
        <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-5 text-red-500">
          <AlertTriangle className="w-7 h-7" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight mb-2">Something went wrong</h2>
        <p className="text-textSecondary text-sm mb-6">
          {error.message || 'An unexpected runtime error occurred while rendering this page.'}
        </p>

        {error.digest && (
          <p className="text-xs font-mono text-textSecondary/70 bg-bgPrimary p-2 rounded-lg border border-borderPrimary mb-6 break-all">
            Error ID: {error.digest}
          </p>
        )}

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={() => reset()}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm bg-brand-600 hover:bg-brand-500 text-white transition-all shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm border border-borderPrimary hover:bg-bgPrimary text-textPrimary transition-all focus:outline-none focus:ring-2 focus:ring-borderPrimary"
          >
            <Home className="w-4 h-4" />
            Return Home
          </Link>
        </div>
      </div>
    </div>
  );
}
