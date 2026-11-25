'use client';

import React from 'react';
import Link from 'next/link';
import { Compass, ArrowLeft, Home, Search } from 'lucide-react';
import ThemeToggle from './ThemeToggle';

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col justify-between bg-bgPrimary text-textPrimary font-sans transition-colors duration-200">
      
      {/* Header */}
      <header className="w-full max-w-[1500px] mx-auto px-6 md:px-12 py-3.5 flex items-center justify-between border-b border-borderPrimary bg-bgSecondary">
        <Link 
          href="/" 
          className="flex items-center gap-2"
          aria-label="RepoMentor Home"
        >
          <span className="font-serif font-bold text-base tracking-tight text-textPrimary">
            RepoMentor
          </span>
          <span className="section-header px-1.5 py-0.5 rounded bg-bgTertiary text-[9px] text-textSecondary border border-borderPrimary">
            404
          </span>
        </Link>
        <ThemeToggle />
      </header>

      {/* Central 404 Hero */}
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 max-w-xl mx-auto my-12">
        <div className="p-4 sm:p-6 rounded border-2 border-borderStrong bg-bgSecondary text-center min-w-[140px] shadow-report mb-6">
          <span className="section-header text-[9px] block">HTTP STATUS</span>
          <div className="inspection-stamp text-5xl sm:text-6xl font-black text-textPrimary mt-1">
            404
          </div>
          <span className="text-[10px] font-mono text-bad font-bold block mt-0.5">
            DOCUMENT UNLOCATED
          </span>
        </div>

        <h1 className="font-serif text-3xl sm:text-4xl font-bold tracking-tight mb-2 text-textPrimary">
          Report Record Not Found
        </h1>
        <p className="text-xs sm:text-sm text-textSecondary max-w-md mb-8 leading-relaxed font-sans">
          The repository report, architecture topology, or file path you requested does not exist in the registry or was removed after session purge.
        </p>

        {/* Action Link */}
        <Link
          href="/"
          className="px-5 py-2.5 bg-signal hover:bg-signal-hover text-white rounded font-mono font-bold text-xs flex items-center gap-2 transition-colors shadow-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Repository Registry</span>
        </Link>
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-borderPrimary py-4 text-center text-xs font-mono text-textMuted bg-bgSecondary">
        Repository Mentor AI • Field Report System
      </footer>

    </div>
  );
}
