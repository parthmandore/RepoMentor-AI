'use client';

import React from 'react';

export function SkeletonBlock({ className = '' }: { className?: string }) {
  return (
    <div
      className={`bg-borderPrimary/60 rounded animate-pulse ${className}`}
    />
  );
}

export function KpiCardsSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-${count} gap-4 w-full font-mono`}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-bgSecondary border border-borderPrimary rounded-lg p-5 shadow-report space-y-3"
        >
          <div className="flex justify-between items-center">
            <SkeletonBlock className="w-24 h-3" />
            <SkeletonBlock className="w-6 h-6 rounded" />
          </div>
          <SkeletonBlock className="w-32 h-7" />
          <SkeletonBlock className="w-20 h-2.5" />
        </div>
      ))}
    </div>
  );
}

export function ContentCardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 shadow-report space-y-4">
      <div className="flex justify-between items-center border-b border-borderPrimary pb-3">
        <SkeletonBlock className="w-36 h-4" />
        <SkeletonBlock className="w-16 h-3" />
      </div>
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex justify-between items-center gap-4 py-2 border-b border-borderPrimary/40 last:border-b-0">
            <div className="space-y-1.5 flex-1">
              <SkeletonBlock className="w-3/4 h-3.5" />
              <SkeletonBlock className="w-1/2 h-2.5" />
            </div>
            <SkeletonBlock className="w-12 h-6 rounded shrink-0" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 shadow-report space-y-4 overflow-hidden">
      <div className="flex justify-between items-center pb-2 border-b border-borderPrimary">
        <SkeletonBlock className="w-40 h-4" />
        <SkeletonBlock className="w-20 h-6 rounded" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex items-center gap-3 py-2 border-b border-borderPrimary/30 last:border-b-0">
            {Array.from({ length: cols }).map((_, c) => (
              <SkeletonBlock
                key={c}
                className={`h-3 ${c === 0 ? 'w-2/5' : c === 1 ? 'w-1/5' : 'flex-1'}`}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function PageLayoutSkeleton({ title = 'Compiling Field Report...' }: { title?: string }) {
  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans">
      <header className="fixed top-0 left-0 right-0 z-50 bg-bgSecondary border-b border-borderPrimary py-3 px-6 md:px-12">
        <div className="max-w-[1500px] mx-auto flex justify-between items-center">
          <div className="flex items-center gap-3">
            <SkeletonBlock className="w-7 h-7 rounded" />
            <SkeletonBlock className="w-36 h-4" />
          </div>
          <div className="flex items-center gap-2">
            <SkeletonBlock className="w-20 h-6 rounded" />
            <SkeletonBlock className="w-8 h-6 rounded-full" />
          </div>
        </div>
      </header>

      <main className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-10 pt-[82px] pb-12 space-y-8 flex-grow">
        <div className="bg-bgSecondary border border-borderPrimary rounded-lg p-8 shadow-report space-y-4">
          <div className="flex justify-between items-start gap-4">
            <div className="space-y-2 flex-1">
              <SkeletonBlock className="w-48 h-3" />
              <SkeletonBlock className="w-80 h-8" />
              <SkeletonBlock className="w-96 h-4" />
            </div>
            <SkeletonBlock className="w-24 h-24 rounded border-2 border-borderPrimary" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <KpiCardsSkeleton count={3} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ContentCardSkeleton rows={4} />
          <ContentCardSkeleton rows={4} />
        </div>
      </main>
    </div>
  );
}
