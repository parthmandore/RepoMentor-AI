'use client';

import React from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-neutral-950 text-neutral-100 flex items-center justify-center p-6 font-sans">
        <div className="max-w-md w-full bg-neutral-900 border border-neutral-800 rounded-2xl p-8 text-center shadow-xl">
          <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-center mx-auto mb-4 text-xl font-bold">
            !
          </div>
          <h2 className="text-xl font-bold mb-2">Application Critical Error</h2>
          <p className="text-sm text-neutral-400 mb-6">
            A critical system error occurred. Please refresh or try again.
          </p>
          <button
            onClick={() => reset()}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all"
          >
            Refresh Application
          </button>
        </div>
      </body>
    </html>
  );
}
