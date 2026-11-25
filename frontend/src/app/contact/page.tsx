'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { 
  Mail, Send, CheckCircle2, AlertCircle, ArrowLeft, 
  Terminal, Github, Loader2, MessageSquare, ShieldCheck, Bug 
} from 'lucide-react';
import ThemeToggle from '../ThemeToggle';
import { useToast } from '../ToastProvider';
import Breadcrumbs from '../components/Breadcrumbs';
import { trackContactFormSubmitted } from '../lib/analytics';

export default function ContactPage() {
  const router = useRouter();
  const toast = useToast();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [subjectCategory, setSubjectCategory] = useState('Feedback');
  const [customSubject, setCustomSubject] = useState('');
  const [message, setMessage] = useState('');
  
  // Anti-spam honeypot and timing
  const [honeypot, setHoneypot] = useState('');
  const [mountTimestamp, setMountTimestamp] = useState<number>(0);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    setMountTimestamp(Date.now());
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    setErrorMessage(null);
    setIsSubmitting(true);

    const fullSubject = customSubject.trim()
      ? `[${subjectCategory}] ${customSubject.trim()}`
      : `[${subjectCategory}] Inquiry from ${name.trim()}`;

    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          subject: fullSubject,
          message: message.trim(),
          company_website: honeypot, // Honeypot field
          form_timestamp: mountTimestamp,
        }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.error || 'Failed to submit contact message.');
      }

      setIsSuccess(true);
      toast.success('Your message has been sent successfully!');
      
      // Track conversion event (governed by cookie consent)
      trackContactFormSubmitted(subjectCategory);
    } catch (err: any) {
      const msg = err.message || 'An unexpected error occurred. Please try again.';
      setErrorMessage(msg);
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setName('');
    setEmail('');
    setCustomSubject('');
    setMessage('');
    setHoneypot('');
    setMountTimestamp(Date.now());
    setIsSuccess(false);
    setErrorMessage(null);
  };

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
                CONTACT
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3 font-mono text-xs">
            <Link
              href="/privacy"
              className="text-textSecondary hover:text-textPrimary transition-colors"
            >
              Privacy
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="w-full max-w-4xl mx-auto px-4 sm:px-6 pt-24 pb-12 flex-1">
        <Breadcrumbs
          items={[
            { label: 'Home', href: '/' },
            { label: 'Contact & Inquiries' },
          ]}
        />

        <div className="mt-6 space-y-8">
          {/* Hero segment */}
          <div className="space-y-2 text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-600 dark:text-brand-400 text-xs font-bold uppercase tracking-wider">
              <Mail className="w-3.5 h-3.5" /> Contact & Feedback
            </div>
            <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              Get in Touch with the Engineering Team
            </h1>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-zinc-400 max-w-2xl leading-relaxed">
              Have a question about AST parsing, static analysis metrics, AI mentor citations, or want to report an issue? Send us a message below.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Form Section */}
            <div className="lg:col-span-2">
              {isSuccess ? (
                <div className="p-8 rounded-3xl bg-emerald-500/10 border border-emerald-500/30 text-left space-y-4 animate-fade-in">
                  <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 flex items-center justify-center text-emerald-500">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                    Message Successfully Sent!
                  </h2>
                  <p className="text-xs text-slate-600 dark:text-zinc-300 leading-relaxed">
                    Thank you for reaching out. Your submission has been securely recorded by our engineering team. We typically review inquiries within 24–48 hours.
                  </p>
                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={handleReset}
                      className="px-4 py-2.5 rounded-xl text-xs font-bold bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:opacity-90 transition-all cursor-pointer"
                    >
                      Send Another Message
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-6 sm:p-8 rounded-3xl bg-white/70 dark:bg-[#0b0a16]/60 border border-slate-200 dark:border-zinc-800 shadow-xl backdrop-blur-md text-left space-y-6">
                  {errorMessage && (
                    <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0" />
                      <span>{errorMessage}</span>
                    </div>
                  )}

                  <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Honeypot field (hidden from genuine users) */}
                    <div className="hidden" aria-hidden="true">
                      <label htmlFor="company_website">Company Website</label>
                      <input
                        type="text"
                        id="company_website"
                        name="company_website"
                        value={honeypot}
                        onChange={(e) => setHoneypot(e.target.value)}
                        tabIndex={-1}
                        autoComplete="off"
                      />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Name */}
                      <div className="space-y-1.5">
                        <label htmlFor="contact-name" className="text-xs font-bold text-slate-700 dark:text-zinc-300">
                          Your Name <span className="text-rose-500">*</span>
                        </label>
                        <input
                          id="contact-name"
                          type="text"
                          required
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          placeholder="Ada Lovelace"
                          disabled={isSubmitting}
                          className="w-full bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl px-4 py-3 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500/30 transition-all"
                        />
                      </div>

                      {/* Email */}
                      <div className="space-y-1.5">
                        <label htmlFor="contact-email" className="text-xs font-bold text-slate-700 dark:text-zinc-300">
                          Your Email <span className="text-rose-500">*</span>
                        </label>
                        <input
                          id="contact-email"
                          type="email"
                          required
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="ada@example.com"
                          disabled={isSubmitting}
                          className="w-full bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl px-4 py-3 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500/30 transition-all"
                        />
                      </div>
                    </div>

                    {/* Topic / Category */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label htmlFor="contact-category" className="text-xs font-bold text-slate-700 dark:text-zinc-300">
                          Inquiry Category
                        </label>
                        <select
                          id="contact-category"
                          value={subjectCategory}
                          onChange={(e) => setSubjectCategory(e.target.value)}
                          disabled={isSubmitting}
                          className="w-full bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl px-4 py-3 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500/30 transition-all"
                        >
                          <option value="Feedback">General Technical Feedback</option>
                          <option value="Bug Report">Bug / Issue Report</option>
                          <option value="Security">Security / Vulnerability Disclosure</option>
                          <option value="Feature Request">Feature Request</option>
                          <option value="Collaboration">Collaboration / Hiring Inquiry</option>
                        </select>
                      </div>

                      <div className="space-y-1.5">
                        <label htmlFor="contact-subject" className="text-xs font-bold text-slate-700 dark:text-zinc-300">
                          Subject Line
                        </label>
                        <input
                          id="contact-subject"
                          type="text"
                          value={customSubject}
                          onChange={(e) => setCustomSubject(e.target.value)}
                          placeholder="e.g., Question about AST parsing"
                          disabled={isSubmitting}
                          className="w-full bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl px-4 py-3 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500/30 transition-all"
                        />
                      </div>
                    </div>

                    {/* Message */}
                    <div className="space-y-1.5">
                      <label htmlFor="contact-message" className="text-xs font-bold text-slate-700 dark:text-zinc-300">
                        Message <span className="text-rose-500">*</span>
                      </label>
                      <textarea
                        id="contact-message"
                        required
                        rows={5}
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        placeholder="Write your question, comment, or technical details here..."
                        disabled={isSubmitting}
                        className="w-full bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-xl p-4 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500/30 transition-all resize-y"
                      />
                    </div>

                    {/* Submit Button */}
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full flex items-center justify-center gap-2 py-3 px-6 rounded text-xs font-mono font-bold bg-signal hover:bg-signal-hover text-white transition-colors disabled:opacity-50 cursor-pointer shadow-sm"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Sending Message...
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4" />
                          Send Message
                        </>
                      )}
                    </button>
                  </form>
                </div>
              )}
            </div>

            {/* Sidebar Details */}
            <div className="space-y-6 text-left">
              <div className="p-6 rounded-3xl bg-slate-50 dark:bg-zinc-900/50 border border-slate-200/80 dark:border-zinc-800/80 space-y-4">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-zinc-300 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-500" />
                  Responsible Disclosure
                </h2>
                <p className="text-xs text-slate-600 dark:text-zinc-400 leading-relaxed">
                  If you have identified a security vulnerability in RepoMentor AI or our analysis engine, please select the &ldquo;Security&rdquo; category to reach the maintainer directly.
                </p>
              </div>

              <div className="p-6 rounded-3xl bg-slate-50 dark:bg-zinc-900/50 border border-slate-200/80 dark:border-zinc-800/80 space-y-4">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-zinc-300 flex items-center gap-2">
                  <Github className="w-4 h-4 text-indigo-500" />
                  GitHub Repository
                </h2>
                <p className="text-xs text-slate-600 dark:text-zinc-400 leading-relaxed">
                  Prefer public issue tracking? Feel free to open an issue or pull request directly on GitHub.
                </p>
                <a
                  href="https://github.com/parthmandore/RepoMentor-AI/issues"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-brand-600 dark:text-brand-400 hover:underline"
                >
                  <Bug className="w-3.5 h-3.5" />
                  Open GitHub Issue &rarr;
                </a>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full text-center py-8 text-[11px] text-slate-500 dark:text-zinc-500 border-t border-slate-200 dark:border-zinc-900/40 bg-slate-100/50 dark:bg-[#020308]/40">
        <div className="max-w-5xl mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p>Repository Mentor AI &copy; {new Date().getFullYear()}</p>
          <div className="flex items-center gap-4">
            <Link href="/" className="hover:text-textPrimary transition-colors">Home</Link>
            <span>|</span>
            <Link href="/privacy" className="hover:text-textPrimary transition-colors">Privacy Policy</Link>
            <span>|</span>
            <Link href="/developer/diagnostics" className="hover:text-textPrimary transition-colors">Diagnostics</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
