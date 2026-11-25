'use client';

import React from 'react';
import { Loader2 } from 'lucide-react';

export default function RepositoryLoading() {
  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col">
      {/* Top Header Skeleton */}
      <div className="h-16 border-b border-borderPrimary bg-bgSecondary/60 px-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-lg bg-borderPrimary/40 animate-pulse" />
          <div className="w-48 h-5 rounded-md bg-borderPrimary/40 animate-pulse" />
        </div>
        <div className="flex items-center gap-3">
          <div className="w-24 h-8 rounded-lg bg-borderPrimary/30 animate-pulse" />
          <div className="w-8 h-8 rounded-lg bg-borderPrimary/30 animate-pulse" />
        </div>
      </div>

      {/* Tabs Skeleton */}
      <div className="border-b border-borderPrimary bg-bgSecondary/40 px-6 py-3 flex gap-2 overflow-x-auto">
        {[1, 2, 3, 4, 5, 6, 7].map((i) => (
          <div key={i} className="w-24 h-8 rounded-lg bg-borderPrimary/30 animate-pulse" />
        ))}
      </div>

      {/* Main Content Skeleton */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-44 rounded-2xl bg-bgSecondary border border-borderPrimary p-6 flex flex-col justify-between animate-pulse">
            <div className="w-28 h-4 rounded bg-borderPrimary/40" />
            <div className="w-16 h-12 rounded bg-borderPrimary/40" />
            <div className="w-36 h-3 rounded bg-borderPrimary/30" />
          </div>
          <div className="h-44 rounded-2xl bg-bgSecondary border border-borderPrimary p-6 flex flex-col justify-between animate-pulse">
            <div className="w-28 h-4 rounded bg-borderPrimary/40" />
            <div className="w-20 h-12 rounded bg-borderPrimary/40" />
            <div className="w-36 h-3 rounded bg-borderPrimary/30" />
          </div>
          <div className="h-44 rounded-2xl bg-bgSecondary border border-borderPrimary p-6 flex flex-col justify-between animate-pulse">
            <div className="w-28 h-4 rounded bg-borderPrimary/40" />
            <div className="w-24 h-12 rounded bg-borderPrimary/40" />
            <div className="w-36 h-3 rounded bg-borderPrimary/30" />
          </div>
        </div>

        <div className="h-96 rounded-2xl bg-bgSecondary border border-borderPrimary p-8 flex flex-col items-center justify-center gap-3 animate-pulse">
          <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
          <p className="text-sm font-medium text-textSecondary">Fetching repository metrics and architecture analysis...</p>
        </div>
      </main>
    </div>
  );
}
