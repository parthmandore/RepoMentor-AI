'use client';

import { getStoredConsent, CookieConsentPreferences } from '../components/CookieConsent';

export type ConversionEventName =
  | 'repo_analysis_started'
  | 'mentor_query_sent'
  | 'architecture_explored'
  | 'diagnostics_executed'
  | 'contact_form_submitted'
  | 'cookie_preferences_saved';

export interface AnalyticsEventPayload {
  eventName: ConversionEventName;
  properties?: Record<string, any>;
  timestamp: string;
}

// In-memory deduplication cache: fingerprint -> timestamp in ms
const recentEvents = new Map<string, number>();
const DEDUPLICATION_WINDOW_MS = 6000; // 6 seconds debounce window

// In-memory queue for events triggered before consent response
const queuedEvents: AnalyticsEventPayload[] = [];
const MAX_QUEUED_EVENTS = 20;

// Listen for consent changes dynamically
if (typeof window !== 'undefined') {
  window.addEventListener('cookieConsentChanged', (e: any) => {
    const prefs: CookieConsentPreferences = e.detail;
    if (prefs && prefs.analytics) {
      flushQueuedEvents();
    } else {
      queuedEvents.length = 0; // Clear queue if rejected
    }
  });
}

function flushQueuedEvents() {
  if (typeof window === 'undefined') return;
  while (queuedEvents.length > 0) {
    const evt = queuedEvents.shift();
    if (evt) {
      dispatchVerifiedEvent(evt);
    }
  }
}

function dispatchVerifiedEvent(payload: AnalyticsEventPayload) {
  if (typeof window === 'undefined') return;

  // 1. Dispatch custom DOM event for custom trackers
  window.dispatchEvent(
    new CustomEvent('repomentor:analytics_event', {
      detail: payload,
    })
  );

  // 2. Dispatch to window.dataLayer if Tag Manager exists
  const win = window as any;
  if (Array.isArray(win.dataLayer)) {
    win.dataLayer.push({
      event: payload.eventName,
      ...payload.properties,
      eventTimestamp: payload.timestamp,
    });
  }

  // 3. Debug logging in development mode
  if (process.env.NODE_ENV !== 'production') {
    console.debug(`[Analytics Tracked] ${payload.eventName}:`, payload.properties);
  }
}

/**
 * Core event tracking engine.
 * Respects user cookie consent strictly and prevents duplicate event firings.
 */
export function trackConversionEvent(
  eventName: ConversionEventName,
  properties: Record<string, any> = {}
): boolean {
  if (typeof window === 'undefined') return false;

  const now = Date.now();

  // Deduplication check: fingerprint based on event name and key properties
  const fingerprint = `${eventName}_${JSON.stringify(properties)}`;
  const lastFired = recentEvents.get(fingerprint);
  if (lastFired && now - lastFired < DEDUPLICATION_WINDOW_MS) {
    // Duplicate detected within deduplication window
    return false;
  }
  recentEvents.set(fingerprint, now);

  // Clean old entries in deduplication cache
  recentEvents.forEach((time, key) => {
    if (now - time > 60000) {
      recentEvents.delete(key);
    }
  });

  const payload: AnalyticsEventPayload = {
    eventName,
    properties: {
      ...properties,
      path: window.location.pathname,
    },
    timestamp: new Date().toISOString(),
  };

  // Check consent gate
  const consent = getStoredConsent();
  if (!consent.hasResponded) {
    // Queue event until user responds
    if (queuedEvents.length < MAX_QUEUED_EVENTS) {
      queuedEvents.push(payload);
    }
    return false;
  }

  if (!consent.analytics) {
    // User explicitly rejected analytics cookies — do not dispatch
    return false;
  }

  // User granted analytics consent — dispatch event
  dispatchVerifiedEvent(payload);
  return true;
}

// Specialized helpers for high-value user milestones
export function trackRepoAnalysisStarted(repoUrl: string) {
  // Sanitize repoUrl: extract domain and owner/repo without query params or tokens
  let sanitized = 'unknown';
  try {
    const parsed = new URL(repoUrl);
    sanitized = parsed.pathname.replace(/^\/+|\/+$/g, '').toLowerCase();
  } catch (e) {
    sanitized = repoUrl.slice(0, 40);
  }

  return trackConversionEvent('repo_analysis_started', {
    repository: sanitized,
  });
}

export function trackMentorQuerySent(repoId: string, hasCodeSample: boolean = false) {
  return trackConversionEvent('mentor_query_sent', {
    repoId,
    hasCodeSample,
  });
}

export function trackArchitectureExplored(repoId: string) {
  return trackConversionEvent('architecture_explored', {
    repoId,
  });
}

export function trackDiagnosticsExecuted(healthy: boolean) {
  return trackConversionEvent('diagnostics_executed', {
    healthy,
  });
}

export function trackContactFormSubmitted(subjectCategory: string) {
  return trackConversionEvent('contact_form_submitted', {
    subjectCategory,
  });
}
