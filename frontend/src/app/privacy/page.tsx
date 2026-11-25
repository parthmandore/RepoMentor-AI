'use client';

import React from 'react';
import Link from 'next/link';
import { 
  Shield, Lock, Eye, Cookie, Sliders, ArrowLeft, 
  Terminal, Server, Globe, ExternalLink, Mail 
} from 'lucide-react';
import ThemeToggle from '../ThemeToggle';
import Breadcrumbs from '../components/Breadcrumbs';
import { triggerOpenCookieSettings } from '../components/CookieConsent';

export default function PrivacyPage() {
  return (
    <div className="relative min-h-screen flex flex-col justify-between bg-bgPrimary text-textPrimary selection:bg-brand-500/30 transition-colors duration-300">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-bgSecondary border-b border-borderPrimary transition-colors duration-200">
        <div className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-12 py-3.5 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="p-1.5 rounded border border-borderPrimary bg-bgPrimary hover:border-borderStrong text-textSecondary hover:text-textPrimary transition-colors"
              title="Return to Home"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div className="flex items-center gap-2">
              <span className="font-serif font-bold text-base tracking-tight text-textPrimary">
                RepoMentor
              </span>
              <span className="section-header px-1.5 py-0.5 rounded bg-bgTertiary text-[9px] text-textSecondary border border-borderPrimary">
                PRIVACY
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3 font-mono text-xs">
            <Link
              href="/contact"
              className="text-textSecondary hover:text-textPrimary transition-colors"
            >
              Contact
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="w-full max-w-4xl mx-auto px-4 sm:px-6 pt-24 pb-16 flex-1 text-left">
        <Breadcrumbs
          items={[
            { label: 'Home', href: '/' },
            { label: 'Privacy Policy' },
          ]}
        />

        <div className="mt-6 space-y-10">
          {/* Title Header */}
          <div className="space-y-3 pb-6 border-b border-slate-200 dark:border-zinc-800">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-600 dark:text-brand-400 text-xs font-bold uppercase tracking-wider">
              <Shield className="w-3.5 h-3.5" /> Privacy & Security Commitment
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              Privacy Policy
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-zinc-400">
              Last Updated: November 2026 &bull; Effective for all RepoMentor AI users
            </p>
          </div>

          {/* Interactive Consent Controller Banner */}
          <div className="p-6 rounded-3xl bg-brand-500/5 border border-brand-500/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Cookie className="w-4 h-4 text-brand-500" />
                Manage Your Cookie & Telemetry Settings
              </h2>
              <p className="text-xs text-slate-600 dark:text-zinc-400">
                You can inspect or change your consent choices for analytics and personalization at any time.
              </p>
            </div>
            <button
              type="button"
              onClick={triggerOpenCookieSettings}
              className="px-4 py-2.5 rounded-xl text-xs font-bold bg-brand-600 hover:bg-brand-700 text-white shadow-sm transition-all flex items-center gap-1.5 shrink-0 cursor-pointer"
            >
              <Sliders className="w-3.5 h-3.5" />
              Open Cookie Settings
            </button>
          </div>

          {/* Section 1: Overview */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Eye className="w-4.5 h-4.5 text-indigo-500" />
              1. Overview & Core Philosophy
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-zinc-300 leading-relaxed">
              RepoMentor AI is an engineering portfolio project designed to evaluate code quality, detect smells, analyze architecture hierarchies, and provide evidence-grounded AI mentorship for public GitHub repositories. We believe in privacy by design: we do not sell your data, monetize repository contents, or inject invasive tracking beacons.
            </p>
          </section>

          {/* Section 2: Codebase Data Ingestion */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Server className="w-4.5 h-4.5 text-violet-500" />
              2. Repository Code & Analysis Data
            </h2>
            <div className="p-5 rounded-2xl bg-slate-50 dark:bg-zinc-900/50 border border-slate-200/80 dark:border-zinc-800/80 space-y-2 text-xs sm:text-sm text-slate-600 dark:text-zinc-300 leading-relaxed">
              <p>
                <strong className="text-slate-900 dark:text-white">Public Repositories Only:</strong> When you provide a GitHub repository URL, our engine fetches code strictly via public Git protocols or GitHub APIs. We never request or require OAuth write scopes or access to private repositories.
              </p>
              <p>
                <strong className="text-slate-900 dark:text-white">Ephemeral Analysis:</strong> Code clone buffers and static analysis AST representations are processed on secure worker environments. We do not redistribute, monetize, or train proprietary foundation models on your submitted repositories.
              </p>
              <p>
                <strong className="text-slate-900 dark:text-white">No Public Search Indexing:</strong> Analysis dashboards and user-scanned repositories are protected with <code className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-zinc-800 text-[11px] font-mono">robots.txt Disallow</code> and <code className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-zinc-800 text-[11px] font-mono">Cache-Control: private, no-store</code> headers to prevent dynamic code views from appearing in external search engines.
              </p>
            </div>
          </section>

          {/* Section 3: Cookies and Local Storage */}
          <section className="space-y-4">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Cookie className="w-4.5 h-4.5 text-amber-500" />
              3. Cookies & Browser Storage Disclosures
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-zinc-300 leading-relaxed">
              We use minimal local browser storage to provide core service features and respect your explicit consent choices:
            </p>

            <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-zinc-800">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100 dark:bg-zinc-900/80 border-b border-slate-200 dark:border-zinc-800 text-slate-800 dark:text-white font-bold">
                    <th className="p-3">Storage Key / Cookie</th>
                    <th className="p-3">Category</th>
                    <th className="p-3">Purpose</th>
                    <th className="p-3">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-zinc-800/80 text-slate-600 dark:text-zinc-300">
                  <tr>
                    <td className="p-3 font-mono text-[11px] text-slate-900 dark:text-white">theme</td>
                    <td className="p-3"><span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold text-[10px]">Essential</span></td>
                    <td className="p-3">Remembers user preference for Dark or Light mode.</td>
                    <td className="p-3">Persistent</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-mono text-[11px] text-slate-900 dark:text-white">repomentor_cookie_consent_v1</td>
                    <td className="p-3"><span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold text-[10px]">Essential</span></td>
                    <td className="p-3">Records your cookie choices so the consent banner is not repeated.</td>
                    <td className="p-3">Persistent</td>
                  </tr>
                  <tr>
                    <td className="p-3 font-mono text-[11px] text-slate-900 dark:text-white">repomentor:analytics_event</td>
                    <td className="p-3"><span className="px-1.5 py-0.5 rounded bg-brand-500/10 text-brand-600 dark:text-brand-400 font-semibold text-[10px]">Analytics</span></td>
                    <td className="p-3">First-party anonymous event dispatch (only loaded after opt-in consent).</td>
                    <td className="p-3">Session / Ephemeral</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Section 4: Contact Inquiries */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Mail className="w-4.5 h-4.5 text-emerald-500" />
              4. Contact Form Inquiries
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-zinc-300 leading-relaxed">
              When you submit a message through our <Link href="/contact" className="text-brand-600 dark:text-brand-400 underline font-medium">Contact Form</Link>, your name, email address, inquiry topic, and message are transmitted securely via encrypted HTTPS to our server API. We process this information exclusively to communicate with you and address your technical query or feedback. We never share or sell contact details to marketers.
            </p>
          </section>

          {/* Section 5: Third-Party Service Providers */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Globe className="w-4.5 h-4.5 text-sky-500" />
              5. Infrastructure & Third-Party Services
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-zinc-900/50 border border-slate-200 dark:border-zinc-800 space-y-1 text-xs">
                <h3 className="font-bold text-slate-900 dark:text-white">Netlify</h3>
                <p className="text-slate-600 dark:text-zinc-400">Hosts our frontend edge infrastructure, SSL termination, and static asset CDN.</p>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-zinc-900/50 border border-slate-200 dark:border-zinc-800 space-y-1 text-xs">
                <h3 className="font-bold text-slate-900 dark:text-white">Render</h3>
                <p className="text-slate-600 dark:text-zinc-400">Executes the FastAPI backend analysis engine in isolated containers.</p>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-zinc-900/50 border border-slate-200 dark:border-zinc-800 space-y-1 text-xs">
                <h3 className="font-bold text-slate-900 dark:text-white">GitHub API</h3>
                <p className="text-slate-600 dark:text-zinc-400">Provides public repository tree metadata and branch commit references.</p>
              </div>
            </div>
          </section>

          {/* Section 6: Security Safeguards */}
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Lock className="w-4.5 h-4.5 text-rose-500" />
              6. Technical Security Controls
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-zinc-300 leading-relaxed">
              RepoMentor AI enforces enterprise HTTP security standards:
            </p>
            <ul className="list-disc list-inside space-y-1 text-xs sm:text-sm text-slate-600 dark:text-zinc-300">
              <li><strong>Content Security Policy (CSP):</strong> Prevents unauthorized script injection, cross-site scripting (XSS), and data exfiltration.</li>
              <li><strong>Frame Protection:</strong> Configured with <code className="px-1 py-0.5 rounded bg-slate-200 dark:bg-zinc-800 font-mono text-[11px]">frame-ancestors &apos;none&apos;</code> and <code className="px-1 py-0.5 rounded bg-slate-200 dark:bg-zinc-800 font-mono text-[11px]">X-Frame-Options: DENY</code> to eliminate clickjacking vectors.</li>
              <li><strong>Strict Transport Security (HSTS):</strong> Mandates TLS encryption across all endpoints for 2 years with preloading enabled.</li>
              <li><strong>MIME Protection:</strong> <code className="px-1 py-0.5 rounded bg-slate-200 dark:bg-zinc-800 font-mono text-[11px]">X-Content-Type-Options: nosniff</code> prevents browser MIME-sniffing exploits.</li>
            </ul>
          </section>

          {/* Section 7: User Rights */}
          <section className="space-y-3 pb-4">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              7. Your Rights & Questions
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-zinc-300 leading-relaxed">
              You may clear your browser local storage at any time to remove saved preferences. If you have any inquiries regarding data handling or privacy practices, please contact us via our{' '}
              <Link href="/contact" className="text-brand-600 dark:text-brand-400 font-bold underline">
                Contact Page
              </Link>.
            </p>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full text-center py-8 text-[11px] text-slate-500 dark:text-zinc-500 border-t border-slate-200 dark:border-zinc-900/40 bg-slate-100/50 dark:bg-[#020308]/40">
        <div className="max-w-5xl mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p>Repository Mentor AI &copy; {new Date().getFullYear()}</p>
          <div className="flex items-center gap-4">
            <Link href="/" className="hover:text-textPrimary transition-colors">Home</Link>
            <span>|</span>
            <Link href="/contact" className="hover:text-textPrimary transition-colors">Contact Us</Link>
            <span>|</span>
            <Link href="/developer/diagnostics" className="hover:text-textPrimary transition-colors">Diagnostics</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
