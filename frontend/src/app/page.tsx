'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { 
  Github, Terminal, ArrowRight, Loader2, CheckCircle2,
  AlertCircle, Shield, Layers, FileCode, Check, Sparkles
} from 'lucide-react';

import ThemeToggle from './ThemeToggle';
import { useToast } from './ToastProvider';
import { trackRepoAnalysisStarted } from './lib/analytics';
import { triggerOpenCookieSettings } from './components/CookieConsent';

const EXAMPLE_REPOS = [
  { 
    name: 'Gyan', 
    url: 'https://github.com/parthmandore/Gyan', 
    id: 'b271888b-ecd1-4f1a-aa89-666b1e445bc8',
    desc: 'Educational math & language app', 
    tag: 'React Native / TS',
    instant: true
  },
  { 
    name: 'RepoMentor AI', 
    url: 'https://github.com/parthmandore/RepoMentor-AI', 
    id: '34484dcd-0d1c-4df5-b459-2a078d675ff6',
    desc: 'Automated Architecture & Code Health', 
    tag: 'Fullstack FastAPI',
    instant: true
  },
  { 
    name: 'DocuMind', 
    url: 'https://github.com/parthmandore/MindPulse-AI', 
    id: '34055b95-2462-4b5f-9d36-3e7884e6d11e',
    desc: 'Local AI document intelligence engine', 
    tag: 'Python / RAG',
    instant: true
  },
  { 
    name: 'CodeMyPicture', 
    url: 'https://github.com/parthmandore/CodeMyPicture', 
    id: '3dde103e-ae24-4bb7-bcd2-67f0db1efa05',
    desc: 'Code screenshot & visual syntax engine', 
    tag: 'React / Next.js',
    instant: true
  },
  { 
    name: 'URL Shortener API', 
    url: 'https://github.com/parthmandore/url-shortener-api', 
    id: 'a0c6cee5-f03c-42a6-97a2-12d878208f49',
    desc: 'Production Spring Boot Java API', 
    tag: 'Java / Spring',
    instant: true
  },
  { 
    name: 'Hello-World', 
    url: 'https://github.com/octocat/Hello-World', 
    id: 'c9608ef8-d706-4635-958b-38e20bd561b2',
    desc: 'Canonical Octocat starter repository', 
    tag: 'Open Source',
    instant: true
  },
];

export default function Home() {
  const router = useRouter();
  const toast = useToast();
  const [url, setUrl] = useState('');
  const [isValid, setIsValid] = useState(false);
  const [touched, setTouched] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isWakingServer, setIsWakingServer] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const validateUrl = (input: string) => {
    const regex = /^https?:\/\/(www\.)?github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+(\.git)?\/?$/;
    return regex.test(input.trim());
  };

  useEffect(() => {
    if (url.trim() === '') {
      setIsValid(false);
    } else {
      setIsValid(validateUrl(url));
    }
  }, [url]);

  const handleSubmit = async (e?: React.FormEvent, customUrl?: string) => {
    if (e) e.preventDefault();
    const targetUrl = (customUrl || url).trim();
    if (!validateUrl(targetUrl) || isSubmitting) return;

    setIsSubmitting(true);
    setIsWakingServer(false);
    setApiError(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

    const maxAttempts = 4;
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 12000);

        const response = await fetch(`${apiUrl}/repositories`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: targetUrl }),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Server responded with HTTP ${response.status}`);
        }

        const data = await response.json();
        trackRepoAnalysisStarted(targetUrl);
        setIsWakingServer(false);
        if (data.status === 'ready') {
          toast.success('Inspection report ready! Directing to Field Report...');
        } else {
          toast.success('Inspection initiated! Directing to Field Report...');
        }
        router.push(`/repositories/${data.id}`);
        return;
      } catch (err: any) {
        if (attempt < maxAttempts) {
          setIsWakingServer(true);
          const backoff = attempt * 3000;
          await new Promise((res) => setTimeout(res, backoff));
        } else {
          const msg = err.message || 'Failed to connect to inspection service. Check backend setup.';
          setApiError(msg);
          toast.error(msg);
          setIsSubmitting(false);
          setIsWakingServer(false);
        }
      }
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between bg-bgPrimary text-textPrimary transition-colors duration-200 font-sans">
      
      {/* Top Editorial Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-bgSecondary/95 backdrop-blur-sm border-b border-borderPrimary py-3.5 px-6 md:px-12 transition-colors">
        <div className="max-w-[1500px] mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2">
            <span className="font-serif font-bold text-base tracking-tight text-textPrimary">
              RepoMentor
            </span>
            <span className="section-header px-1.5 py-0.5 rounded bg-bgTertiary text-[9px] text-textSecondary border border-borderPrimary">
              REGISTRY
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono">
            <Link href="/privacy" className="text-textSecondary hover:text-textPrimary transition-colors">
              Privacy
            </Link>
            <Link href="/contact" className="text-textSecondary hover:text-textPrimary transition-colors">
              Contact
            </Link>
            <div className="h-3 w-px bg-borderPrimary" />
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main Content Body */}
      <main className="w-full max-w-5xl mx-auto px-4 sm:px-6 pt-28 pb-16 space-y-12">
        
        {/* Hero Section */}
        <div className="text-center space-y-4 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-bgSecondary border border-borderPrimary text-[10px] font-mono text-textSecondary">
            <span className="w-1.5 h-1.5 rounded-full bg-signal" />
            <span>ARCHIVAL REPOSITORY INSPECTOR</span>
          </div>

          <h1 className="font-serif text-4xl sm:text-6xl font-bold tracking-tight text-textPrimary leading-[1.08]">
            Engineering Field Reports <br />
            <span className="italic font-normal text-textSecondary">for Any Repository.</span>
          </h1>

          <p className="text-xs sm:text-sm text-textSecondary font-sans max-w-xl mx-auto leading-relaxed">
            Enter a public GitHub repository. Get an editorial inspection report with architectural swim-lanes, code smell audits, and evidence-grounded AI mentorship.
          </p>
        </div>

        {/* Input & Scan Box */}
        <div className="max-w-2xl mx-auto bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report space-y-6">
          
          {/* Repository Submission Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="repo-url" className="section-header flex items-center justify-between">
                <span>TARGET GITHUB REPOSITORY</span>
                <span className="text-[10px] text-textMuted lowercase font-normal">public repositories only</span>
              </label>
              <div className="relative">
                <input
                  id="repo-url"
                  type="text"
                  placeholder="https://github.com/owner/repository"
                  value={url}
                  disabled={isSubmitting}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    setTouched(true);
                    setApiError(null);
                  }}
                  className={`w-full bg-bgPrimary border text-textPrimary placeholder:text-textMuted rounded px-4 py-3 text-xs sm:text-sm font-mono focus:outline-none transition-colors ${
                    touched && url && !isValid
                      ? 'border-bad focus:border-bad'
                      : 'border-borderPrimary focus:border-signal'
                  }`}
                />
              </div>

              {touched && url && !isValid && (
                <p className="text-[11px] font-mono text-bad flex items-center gap-1 mt-1">
                  <AlertCircle className="w-3 h-3" /> Must be a valid GitHub URL (e.g., https://github.com/owner/repo)
                </p>
              )}
            </div>

            {isWakingServer && (
              <div className="p-3 bg-[#C4A000]/10 border border-[#C4A000]/30 rounded text-xs font-mono text-[#C4A000] flex items-center gap-2 animate-pulse">
                <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                <span>Waking up backend service from sleep... (Render Free spins down after 15 min idle). Connecting automatically...</span>
              </div>
            )}

            {apiError && (
              <div className="p-3 bg-bad-bg border border-bad-border rounded text-xs font-mono text-bad flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{apiError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={!isValid || isSubmitting}
              className="w-full py-3.5 px-4 bg-signal hover:bg-signal-hover disabled:opacity-40 disabled:cursor-not-allowed text-white rounded text-xs font-mono font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors shadow-sm"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Connecting to Inspection Engine...</span>
                </>
              ) : (
                <>
                  <span>Generate Inspection Field Report</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Try These Demo Repos (Instant <2s Open) */}
          <div className="pt-3 border-t border-borderPrimary space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="section-header flex items-center gap-1.5 text-[10px] text-textSecondary font-bold">
                <Sparkles className="w-3 h-3 text-signal" />
                <span>TRY THESE — INSTANT FIELD REPORT & AI MENTOR DEMOS</span>
              </span>
              <span className="text-[10px] font-mono text-signal font-semibold bg-signal/10 px-2 py-0.5 rounded border border-signal/20">
                Instant Ready (&lt;2s)
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
              {EXAMPLE_REPOS.map((ex, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    if (ex.id) {
                      router.push(`/repositories/${ex.id}`);
                    } else {
                      setUrl(ex.url);
                      setTouched(true);
                      handleSubmit(undefined, ex.url);
                    }
                  }}
                  disabled={isSubmitting}
                  className="p-3 rounded-md bg-bgPrimary border border-borderPrimary hover:border-signal text-left transition-all font-mono text-xs group hover:shadow-sm flex flex-col justify-between relative overflow-hidden"
                >
                  <div className="space-y-1">
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-[12px] font-bold text-textPrimary group-hover:text-signal block truncate">
                        {ex.name}
                      </span>
                      <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-bgSecondary text-textSecondary border border-borderPrimary shrink-0">
                        {ex.tag}
                      </span>
                    </div>
                    <span className="text-[11px] text-textMuted block font-sans line-clamp-1">
                      {ex.desc}
                    </span>
                  </div>
                  <div className="mt-2 pt-1.5 border-t border-borderPrimary/40 flex items-center justify-between text-[10px] text-textSecondary group-hover:text-signal">
                    <span className="font-sans font-medium text-[10px]">Open field report</span>
                    <ArrowRight className="w-3 h-3 transition-transform group-hover:translate-x-0.5" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Realistic Sample Field Report Preview (Shows users what they get) */}
        <div className="max-w-3xl mx-auto space-y-3">
          <div className="flex items-center justify-between text-xs font-mono px-1">
            <span className="section-header">SAMPLE REPORT PREVIEW</span>
            <span className="text-textMuted">Generated for standard repository</span>
          </div>

          <div className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 shadow-report space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-borderPrimary pb-4">
              <div>
                <span className="section-header text-[9px]">INSPECTION SNAPSHOT</span>
                <h3 className="font-serif text-2xl font-bold text-textPrimary">url-shortener-api</h3>
                <p className="text-xs font-mono text-textSecondary">Spring Boot • Java • Maven</p>
              </div>

              {/* Sample Grade Stamp */}
              <div className="px-5 py-3 border-2 border-borderStrong bg-bgPrimary rounded text-center shrink-0">
                <span className="section-header text-[8px] block">GRADE</span>
                <span className="inspection-stamp text-4xl font-black text-textPrimary">A</span>
                <span className="text-[10px] font-mono text-textSecondary font-bold block">92 / 100</span>
              </div>
            </div>

            {/* Segmented bar preview */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-[11px] font-mono text-textSecondary">
                <span>Health Profile Breakdown</span>
                <span className="text-good font-bold">Passing / Production Grade</span>
              </div>
              <div className="grid grid-cols-4 gap-1 h-2 bg-bgTertiary p-0.5 rounded border border-borderPrimary">
                <div className="h-full bg-signal rounded-sm" />
                <div className="h-full bg-signal rounded-sm" />
                <div className="h-full bg-signal/80 rounded-sm" />
                <div className="h-full bg-signal/60 rounded-sm" />
              </div>
            </div>

            {/* Metrics row */}
            <div className="grid grid-cols-3 gap-3 text-xs font-mono text-center">
              <div className="p-2.5 bg-bgPrimary border border-borderPrimary rounded">
                <span className="text-[9px] text-textMuted block">CODEBASE SIZE</span>
                <strong className="text-sm text-textPrimary">4,820 LOC</strong>
              </div>
              <div className="p-2.5 bg-bgPrimary border border-borderPrimary rounded">
                <span className="text-[9px] text-textMuted block">SWIM-LANES</span>
                <strong className="text-sm text-textPrimary">Layered (5 Lanes)</strong>
              </div>
              <div className="p-2.5 bg-bgPrimary border border-borderPrimary rounded">
                <span className="text-[9px] text-textMuted block">CRITICAL SMELLS</span>
                <strong className="text-sm text-good">0 Detected</strong>
              </div>
            </div>
          </div>
        </div>

      </main>

      {/* Editorial Footer */}
      <footer className="w-full border-t border-borderPrimary bg-bgSecondary/60 py-6 px-6 text-center text-xs font-mono text-textMuted">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <span>Repository Mentor AI • Engineering Field Reports</span>
          <div className="flex items-center gap-4">
            <button 
              onClick={triggerOpenCookieSettings} 
              className="hover:text-textPrimary transition-colors underline underline-offset-2"
            >
              Cookie Settings
            </button>
            <Link href="/privacy" className="hover:text-textPrimary transition-colors">
              Privacy
            </Link>
            <Link href="/contact" className="hover:text-textPrimary transition-colors">
              Contact
            </Link>
          </div>
        </div>
      </footer>

    </div>
  );
}
