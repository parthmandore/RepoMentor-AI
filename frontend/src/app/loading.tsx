'use client';

import React from 'react';
import { Terminal, Loader2 } from 'lucide-react';

export default function Loading() {
  return (
    <div className="min-h-screen bg-bgPrimary flex flex-col items-center justify-center p-6 text-textPrimary">
      <div className="flex flex-col items-center gap-4">
        <div className="relative flex items-center justify-center w-16 h-16 rounded-2xl bg-bgSecondary border border-borderPrimary shadow-sm">
          <Terminal className="w-7 h-7 text-brand-500 animate-pulse" />
          <Loader2 className="absolute -bottom-1 -right-1 w-5 h-5 text-brand-500 animate-spin" />
        </div>
        <div className="flex flex-col items-center gap-1.5 text-center">
          <p className="text-sm font-semibold tracking-wide">Loading Repository Mentor...</p>
          <p className="text-xs text-textSecondary">Preparing metrics & evaluation context</p>
        </div>
      </div>
    </div>
  );
}
