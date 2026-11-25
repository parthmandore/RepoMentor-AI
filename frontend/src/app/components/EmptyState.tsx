'use client';

import React from 'react';
import Link from 'next/link';
import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  badge?: string;
  primaryAction?: {
    label: string;
    href?: string;
    onClick?: () => void;
    icon?: LucideIcon;
  };
  secondaryAction?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
  variant?: 'neutral' | 'success' | 'warning';
}

export default function EmptyState({
  icon: Icon,
  title,
  description,
  badge,
  primaryAction,
  secondaryAction,
  variant = 'neutral',
}: EmptyStateProps) {
  const getVariantStyles = () => {
    switch (variant) {
      case 'success':
        return {
          iconBox: 'bg-good-bg border-good-border text-good',
          badge: 'bg-good-bg text-good border-good-border',
        };
      case 'warning':
        return {
          iconBox: 'bg-warn-bg border-warn-border text-warn',
          badge: 'bg-warn-bg text-warn border-warn-border',
        };
      case 'neutral':
      default:
        return {
          iconBox: 'bg-bgTertiary border-borderPrimary text-textSecondary',
          badge: 'bg-bgTertiary text-textSecondary border-borderPrimary',
        };
    }
  };

  const styles = getVariantStyles();

  return (
    <div className="w-full bg-bgSecondary border border-borderPrimary rounded-lg p-8 sm:p-12 text-center shadow-report flex flex-col items-center justify-center max-w-xl mx-auto my-6 font-sans">
      <div className={`w-12 h-12 rounded-lg border flex items-center justify-center mb-4 ${styles.iconBox}`}>
        <Icon className="w-6 h-6" />
      </div>

      {badge && (
        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border mb-2.5 ${styles.badge}`}>
          {badge}
        </span>
      )}

      <h3 className="font-serif text-xl font-bold text-textPrimary tracking-tight mb-2">
        {title}
      </h3>
      <p className="text-xs sm:text-sm text-textSecondary max-w-md leading-relaxed mb-6 font-sans">
        {description}
      </p>

      {(primaryAction || secondaryAction) && (
        <div className="flex flex-wrap items-center justify-center gap-3 font-mono text-xs">
          {primaryAction && (
            primaryAction.href ? (
              <Link
                href={primaryAction.href}
                className="px-4 py-2 bg-signal hover:bg-signal-hover text-white rounded font-bold transition-colors shadow-sm flex items-center gap-1.5"
              >
                {primaryAction.icon && <primaryAction.icon className="w-3.5 h-3.5" />}
                <span>{primaryAction.label}</span>
              </Link>
            ) : (
              <button
                onClick={primaryAction.onClick}
                className="px-4 py-2 bg-signal hover:bg-signal-hover text-white rounded font-bold transition-colors shadow-sm flex items-center gap-1.5"
              >
                {primaryAction.icon && <primaryAction.icon className="w-3.5 h-3.5" />}
                <span>{primaryAction.label}</span>
              </button>
            )
          )}

          {secondaryAction && (
            secondaryAction.href ? (
              <Link
                href={secondaryAction.href}
                className="px-3.5 py-2 bg-bgTertiary hover:bg-borderPrimary border border-borderPrimary text-textPrimary rounded font-semibold transition-colors"
              >
                {secondaryAction.label}
              </Link>
            ) : (
              <button
                onClick={secondaryAction.onClick}
                className="px-3.5 py-2 bg-bgTertiary hover:bg-borderPrimary border border-borderPrimary text-textPrimary rounded font-semibold transition-colors"
              >
                {secondaryAction.label}
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
}
