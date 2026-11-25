'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { AlertCircle, RefreshCw, ArrowLeft, Home } from 'lucide-react';

export default function RepositoryError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Repository view error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col items-center justify-center p-6">
      <div className="max-w-lg w-full bg-bgSecondary border border-borderPrimary rounded-2xl p-8 shadow-md text-center">
        <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-5 text-red-500">
          <AlertCircle className="w-7 h-7" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight mb-2">Repository Data Unavailable</h2>
        <p className="text-textSecondary text-sm mb-6">
          {error.message || 'Unable to load or display repository metrics. The backend server might be starting up or the repository may still be processing.'}
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={() => reset()}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm bg-brand-600 hover:bg-brand-500 text-white transition-all shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm border border-borderPrimary hover:bg-bgPrimary text-textPrimary transition-all focus:outline-none focus:ring-2 focus:ring-borderPrimary"
          >
            <Home className="w-4 h-4" />
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
