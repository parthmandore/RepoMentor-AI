'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Shield, Cookie, Check, X, Settings2, Sliders, ExternalLink } from 'lucide-react';

export interface CookieConsentPreferences {
  hasResponded: boolean;
  essential: boolean;
  analytics: boolean;
  preferences: boolean;
  timestamp: string;
  version: string;
}

export const CONSENT_STORAGE_KEY = 'repomentor_cookie_consent_v1';
export const CONSENT_VERSION = '1.0';

export const DEFAULT_CONSENT: CookieConsentPreferences = {
  hasResponded: false,
  essential: true,
  analytics: false,
  preferences: false,
  timestamp: '',
  version: CONSENT_VERSION,
};

export function getStoredConsent(): CookieConsentPreferences {
  if (typeof window === 'undefined') return DEFAULT_CONSENT;
  try {
    const raw = localStorage.getItem(CONSENT_STORAGE_KEY);
    if (!raw) return DEFAULT_CONSENT;
    const parsed = JSON.parse(raw);
    if (parsed && parsed.version === CONSENT_VERSION && typeof parsed.hasResponded === 'boolean') {
      return {
        ...parsed,
        essential: true, // Always enforced
      };
    }
  } catch (e) {
    // LocalStorage inaccessible
  }
  return DEFAULT_CONSENT;
}

export function saveConsent(prefs: Partial<CookieConsentPreferences>): CookieConsentPreferences {
  const updated: CookieConsentPreferences = {
    hasResponded: true,
    essential: true,
    analytics: Boolean(prefs.analytics),
    preferences: Boolean(prefs.preferences),
    timestamp: new Date().toISOString(),
    version: CONSENT_VERSION,
  };

  try {
    localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(updated));
  } catch (e) {
    // Storage quota or private browsing limitation
  }

  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('cookieConsentChanged', { detail: updated }));
  }

  return updated;
}

export function triggerOpenCookieSettings() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('openCookiePreferences'));
  }
}

export default function CookieConsent() {
  const [mounted, setMounted] = useState(false);
  const [showBanner, setShowBanner] = useState(true);
  const [showPreferences, setShowPreferences] = useState(false);

  // Granular preference state for customization panel
  const [analyticsEnabled, setAnalyticsEnabled] = useState(false);
  const [preferencesEnabled, setPreferencesEnabled] = useState(false);

  useEffect(() => {
    setMounted(true);
    const existing = getStoredConsent();
    if (existing.hasResponded) {
      setShowBanner(false);
      setAnalyticsEnabled(existing.analytics);
      setPreferencesEnabled(existing.preferences);
    } else {
      setShowBanner(true);
    }

    const handleOpenModal = () => {
      const current = getStoredConsent();
      setAnalyticsEnabled(current.analytics);
      setPreferencesEnabled(current.preferences);
      setShowPreferences(true);
      setShowBanner(false);
    };

    window.addEventListener('openCookiePreferences', handleOpenModal);
    return () => {
      window.removeEventListener('openCookiePreferences', handleOpenModal);
    };
  }, []);

  const handleAcceptAll = useCallback(() => {
    saveConsent({ analytics: true, preferences: true });
    setShowBanner(false);
    setShowPreferences(false);
  }, []);

  const handleRejectNonEssential = useCallback(() => {
    saveConsent({ analytics: false, preferences: false });
    setShowBanner(false);
    setShowPreferences(false);
  }, []);

  const handleSaveCustom = useCallback(() => {
    saveConsent({
      analytics: analyticsEnabled,
      preferences: preferencesEnabled,
    });
    setShowBanner(false);
    setShowPreferences(false);
  }, [analyticsEnabled, preferencesEnabled]);

  if (!mounted) return null;

  return (
    <>
      {/* 1. Bottom Slide Banner */}
      {showBanner && !showPreferences && (
        <aside
          role="region"
          aria-label="Cookie and Privacy Consent"
          className="fixed bottom-4 left-4 right-4 md:left-8 md:right-8 lg:left-auto lg:right-8 lg:max-w-xl z-50 p-5 rounded-lg bg-bgSecondary border border-borderPrimary shadow-report transition-all duration-200 animate-slide-up"
        >
          <div className="flex items-start gap-3.5">
            <div className="p-2 rounded bg-signal/10 border border-signal/20 text-signal shrink-0 mt-0.5">
              <Cookie className="w-4 h-4" />
            </div>
            <div className="space-y-2 flex-1 text-left">
              <div className="flex items-center justify-between">
                <h3 className="font-serif text-sm font-bold tracking-tight text-textPrimary flex items-center gap-1.5">
                  Privacy & Cookie Preferences
                </h3>
              </div>
              <p className="text-xs text-textSecondary leading-relaxed font-sans">
                RepoMentor AI uses essential storage for core functionality. We only load telemetry and performance tracking if you explicitly consent.{' '}
                <Link
                  href="/privacy"
                  className="underline hover:text-signal font-medium inline-flex items-center gap-0.5"
                >
                  Privacy Policy
                  <ExternalLink className="w-2.5 h-2.5" />
                </Link>
              </p>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-2 pt-2 font-mono text-xs">
                <button
                  type="button"
                  onClick={handleAcceptAll}
                  className="px-3.5 py-1.5 rounded text-xs font-bold bg-signal hover:bg-signal-hover text-white transition-colors cursor-pointer shadow-sm"
                >
                  Accept All
                </button>
                <button
                  type="button"
                  onClick={handleRejectNonEssential}
                  className="px-3.5 py-1.5 rounded text-xs font-bold bg-bgTertiary hover:bg-borderPrimary text-textPrimary border border-borderPrimary transition-colors cursor-pointer"
                >
                  Essential Only
                </button>
                <button
                  type="button"
                  onClick={() => setShowPreferences(true)}
                  className="px-3 py-1.5 rounded text-xs text-textSecondary hover:text-textPrimary hover:bg-bgTertiary transition-colors flex items-center gap-1.5 cursor-pointer"
                  aria-label="Customize cookie preferences"
                >
                  <Sliders className="w-3 h-3" />
                  Customize
                </button>
              </div>
            </div>
          </div>
        </aside>
      )}

      {/* 2. Granular Preferences Modal */}
      {showPreferences && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="cookie-preferences-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
        >
          <div className="w-full max-w-lg bg-bgSecondary border border-borderPrimary rounded-lg p-6 md:p-8 shadow-report-lg space-y-6 text-left max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-borderPrimary">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded bg-signal/10 border border-signal/20 text-signal">
                  <Shield className="w-4 h-4" />
                </div>
                <div>
                  <h2 id="cookie-preferences-title" className="font-serif text-base font-bold text-textPrimary">
                    Cookie & Storage Preferences
                  </h2>
                  <p className="text-[11px] font-mono text-textSecondary">
                    Control how data is stored in your browser
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowPreferences(false)}
                className="p-1.5 rounded text-textSecondary hover:text-textPrimary hover:bg-bgTertiary transition-colors"
                aria-label="Close preferences panel"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Granular Categories */}
            <div className="space-y-4">
              {/* Essential Category */}
              <div className="p-4 rounded bg-bgPrimary border border-borderPrimary space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-textPrimary flex items-center gap-1.5">
                    Essential Storage
                    <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-good-bg text-good font-bold border border-good-border">
                      Required
                    </span>
                  </span>
                  <span className="text-[11px] font-mono font-medium text-textMuted">
                    Always Active
                  </span>
                </div>
                <p className="text-xs text-textSecondary leading-relaxed font-sans">
                  Required for core security, session state, theme preservation, and storing your consent preferences. Cannot be disabled.
                </p>
              </div>

              {/* Analytics Category */}
              <div className="p-4 rounded bg-bgPrimary border border-borderPrimary space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-textPrimary block">
                      Analytics & Telemetry
                    </span>
                    <span className="text-[10px] font-mono text-textSecondary">
                      Anonymous usage insights & conversion tracking
                    </span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={analyticsEnabled}
                      onChange={(e) => setAnalyticsEnabled(e.target.checked)}
                      className="sr-only peer"
                      aria-label="Toggle analytics cookies"
                    />
                    <div className="w-11 h-6 bg-slate-300 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-zinc-600 peer-checked:bg-brand-600"></div>
                  </label>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-zinc-400 leading-relaxed">
                  Helps us understand repository ingestion performance and AI mentor engagement. Never stores personal code snippets, secrets, or GitHub tokens.
                </p>
              </div>

              {/* Personalization Category */}
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-zinc-900/40 border border-slate-200/80 dark:border-zinc-800/80 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-slate-900 dark:text-white block">
                      UI Personalization
                    </span>
                    <span className="text-[10px] text-slate-500 dark:text-zinc-400">
                      Interface preferences & dashboard defaults
                    </span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={preferencesEnabled}
                      onChange={(e) => setPreferencesEnabled(e.target.checked)}
                      className="sr-only peer"
                      aria-label="Toggle UI personalization cookies"
                    />
                    <div className="w-11 h-6 bg-slate-300 peer-focus:outline-none rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-zinc-600 peer-checked:bg-brand-600"></div>
                  </label>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-zinc-400 leading-relaxed">
                  Preserves active tabs, graph zoom states, and inspection filters across browsing sessions.
                </p>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex flex-col sm:flex-row items-center justify-end gap-2.5 pt-4 border-t border-borderPrimary font-mono text-xs">
              <button
                type="button"
                onClick={handleAcceptAll}
                className="w-full sm:w-auto px-4 py-2 rounded bg-bgTertiary hover:bg-borderPrimary text-textPrimary transition-colors cursor-pointer"
              >
                Accept All
              </button>
              <button
                type="button"
                onClick={handleSaveCustom}
                className="w-full sm:w-auto px-5 py-2 rounded font-bold bg-signal hover:bg-signal-hover text-white transition-colors cursor-pointer shadow-sm"
              >
                Save Preferences
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
