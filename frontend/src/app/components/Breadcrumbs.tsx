'use client';

import React from 'react';
import Link from 'next/link';
import { ChevronRight, Home } from 'lucide-react';

export interface BreadcrumbItem {
  label: string;
  href?: string;
  current?: boolean;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
  showHomeIcon?: boolean;
}

export default function Breadcrumbs({
  items,
  className = '',
  showHomeIcon = true,
}: BreadcrumbsProps) {
  // Construct Schema.org BreadcrumbList structured data
  const baseUrl = 'https://repomentor.netlify.app';
  const schemaItems = items.map((item, index) => ({
    '@type': 'ListItem',
    position: index + 1,
    name: item.label,
    ...(item.href
      ? { item: item.href.startsWith('http') ? item.href : `${baseUrl}${item.href}` }
      : {}),
  }));

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: schemaItems,
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <nav aria-label="Breadcrumb" className={`select-none ${className}`}>
        <ol className="flex items-center flex-wrap gap-1 sm:gap-1.5 text-xs text-textSecondary font-medium">
          {items.map((item, idx) => {
            const isLast = idx === items.length - 1 || item.current;
            return (
              <li key={idx} className="flex items-center gap-1 sm:gap-1.5">
                {idx > 0 && (
                  <ChevronRight
                    className="w-3.5 h-3.5 text-slate-400 dark:text-zinc-600 shrink-0"
                    aria-hidden="true"
                  />
                )}
                {isLast ? (
                  <span
                    className="text-textPrimary font-semibold truncate max-w-[200px] sm:max-w-xs"
                    aria-current="page"
                  >
                    {item.label}
                  </span>
                ) : item.href ? (
                  <Link
                    href={item.href}
                    className="hover:text-textPrimary transition-colors flex items-center gap-1"
                  >
                    {idx === 0 && showHomeIcon && (
                      <Home className="w-3.5 h-3.5 shrink-0 text-slate-400 dark:text-zinc-500" />
                    )}
                    <span>{item.label}</span>
                  </Link>
                ) : (
                  <span>{item.label}</span>
                )}
              </li>
            );
          })}
        </ol>
      </nav>
    </>
  );
}
