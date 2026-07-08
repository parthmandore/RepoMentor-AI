'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Github, Terminal, AlertCircle, CheckCircle, 
  ArrowRight, Loader2, MessageSquare, Layers, Shield, BarChart3, 
  CheckCircle2, Zap
} from 'lucide-react';

import ThemeToggle from './ThemeToggle';

export default function Home() {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [isValid, setIsValid] = useState(false);
  const [touched, setTouched] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // GitHub repo regex validation
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || isSubmitting) return;

    setIsSubmitting(true);
    setApiError(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';

    try {
      const response = await fetch(`${apiUrl}/repositories`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url.trim() }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to submit repository');
      }

      const data = await response.json();
      router.push(`/repositories/${data.id}`);
    } catch (err: any) {
      setApiError(err.message || 'Failed to connect to backend service. Please check your setup.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-between overflow-hidden bg-bgPrimary text-textPrimary selection:bg-brand-500/30 transition-colors duration-300">
      {/* Background radial/linear glow elements */}
      <div className="absolute top-1/4 left-1/4 w-[450px] h-[450px] bg-indigo-600/10 rounded-full blur-[120px] animate-slow-blob-1 -z-10" />
      <div className="absolute bottom-1/4 right-1/4 w-[450px] h-[450px] bg-violet-600/10 rounded-full blur-[140px] animate-slow-blob-2 -z-10" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-brand-500/5 rounded-full blur-[160px] animate-slow-blob-3 -z-10" />
      
      {/* Grid Overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff03_1px,transparent_1px),linear-gradient(to_bottom,#ffffff03_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] -z-10" />
      <div className="absolute inset-0 bg-gradient-to-t from-bgPrimary via-transparent to-transparent -z-10" />

      {/* Fixed Premium Header / Navigation */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-bgSecondary border-b border-borderPrimary shadow-[0_1px_3px_rgba(0,0,0,0.08)] dark:shadow-[0_1px_3px_rgba(0,0,0,0.3)] transition-all duration-200 flex justify-between items-center py-4 px-6 md:px-12 max-w-[1700px] mx-auto">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-brand-500 dark:text-brand-400" />
          <span className="font-extrabold text-sm tracking-widest bg-gradient-to-r from-brand-600 to-indigo-600 dark:from-brand-400 dark:to-indigo-400 bg-clip-text text-transparent">REPOSITORY MENTOR AI</span>
        </div>
        <ThemeToggle />
      </header>

      {/* Main Landing Content Container */}
      <div className="w-full max-w-5xl px-6 z-10 flex flex-col items-center text-center space-y-12 pt-28">
        
        {/* Hero Section */}
        <div className="space-y-4 max-w-3xl">
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight leading-none bg-gradient-to-b from-slate-900 to-slate-700 dark:from-white dark:to-zinc-500 bg-clip-text text-transparent">
            Understand Repositories <br className="hidden sm:inline" />
            <span className="bg-gradient-to-r from-brand-600 via-indigo-600 to-violet-600 dark:from-brand-400 dark:via-indigo-400 dark:to-violet-400 bg-clip-text text-transparent">
              In Seconds
            </span>
          </h1>
          <p className="text-sm md:text-base text-slate-600 dark:text-zinc-400 max-w-xl mx-auto font-medium leading-relaxed">
            Accelerate your engineering reviews. Scan any GitHub repository to instantly unlock architecture mapping, code smell assessment, dependency checks, and natural Q&A with evidence-backed AI.
          </p>
        </div>

        {/* Input Form Box */}
        <div className="w-full max-w-2xl bg-white/70 dark:bg-[#0b0a16]/45 border border-slate-200 dark:border-zinc-800/40 rounded-3xl p-6 md:p-8 shadow-xl dark:shadow-[0_25px_60px_rgba(0,0,0,0.5)] backdrop-blur-md text-left space-y-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2.5">
              <label htmlFor="repo-url" className="text-[10px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider flex items-center gap-2">
                <Github className="w-4 h-4 text-slate-400 dark:text-zinc-500" />
                Repository GitHub URL
              </label>
              
              <div className="relative">
                <input
                  id="repo-url"
                  type="text"
                  placeholder="https://github.com/username/repository"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    setTouched(true);
                    setApiError(null);
                  }}
                  disabled={isSubmitting}
                  className={`w-full bg-[#FFFFFF] dark:bg-[#1A1A28] border border-[#D0D0E0] dark:border-[rgba(255,255,255,0.1)] text-[#0F0F1A] dark:text-[#F1F1F5] placeholder-[#6B6B80] dark:placeholder-[#8B8B9E] rounded-xl px-4.5 py-4 pr-12 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-500/20 transition-all duration-300 ${
                    isSubmitting
                      ? 'opacity-60 cursor-not-allowed'
                      : !touched
                      ? 'focus:border-indigo-500'
                      : isValid
                      ? 'border-emerald-500/40 focus:border-emerald-500'
                      : 'border-rose-500 dark:border-rose-500/40 focus:border-rose-500'
                  }`}
                />
                <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center">
                  {isSubmitting ? (
                    <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
                  ) : (
                    touched && url !== '' && (
                      isValid ? (
                        <CheckCircle className="w-5 h-5 text-emerald-400" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-rose-400" />
                      )
                    )
                  )}
                </div>
              </div>

              {/* Status / Helper Text */}
              {touched && url !== '' && !isValid && (
                <p className="text-[11px] text-rose-400/90 flex items-center gap-1.5 mt-1.5">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Please enter a valid GitHub repository URL (e.g., https://github.com/user/repo)
                </p>
              )}
              {touched && url !== '' && isValid && !apiError && (
                <p className="text-[11px] text-emerald-400/90 flex items-center gap-1.5 mt-1.5">
                  <CheckCircle className="w-3.5 h-3.5" />
                  Codebase matches GitHub specifications
                </p>
              )}
            </div>

            {apiError && (
              <div className="p-4 bg-rose-500/5 border border-rose-500/15 rounded-xl text-[11px] text-rose-400 flex items-center gap-2">
                <AlertCircle className="w-4.5 h-4.5 shrink-0 text-rose-400" />
                <span>{apiError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={!isValid || isSubmitting}
              className={`w-full flex items-center justify-center gap-2.5 py-4 px-4 rounded-xl text-xs font-bold uppercase tracking-wider btn-premium transition-all duration-300 ${
                isValid && !isSubmitting
                  ? 'bg-gradient-to-r from-brand-600 via-indigo-600 to-violet-600 text-white shadow-[0_4px_25px_rgba(99,102,241,0.2)] hover:shadow-[0_4px_30px_rgba(99,102,241,0.35)] cursor-pointer'
                  : 'bg-slate-200 dark:bg-zinc-900/60 text-slate-400 dark:text-zinc-500 border border-slate-300 dark:border-zinc-800 cursor-not-allowed'
              }`}
            >
              {isSubmitting ? (
                <>
                  Initializing Codebase Ingestion...
                  <Loader2 className="w-4 h-4 animate-spin" />
                </>
              ) : (
                <>
                  Analyze Repository
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Feature Cards Grid (Sleek Product Features) */}
        <div className="space-y-6 w-full pt-6">
          <div className="text-center space-y-1">
            <h2 className="text-[11px] font-bold text-brand-500 dark:text-brand-400 uppercase tracking-widest">Capabilities</h2>
            <p className="text-md font-bold text-slate-800 dark:text-white tracking-tight">Full Codebase Intellect</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
            <div className="p-6 premium-glass-card rounded-2xl space-y-3.5">
              <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-500 dark:text-indigo-400">
                <MessageSquare className="w-4.5 h-4.5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xs font-bold text-slate-800 dark:text-gray-200 uppercase tracking-wider">AI Repository Mentor</h3>
                <p className="text-[11px] text-slate-600 dark:text-zinc-400 leading-relaxed">Ask natural language questions about any repository with evidence-backed AI.</p>
              </div>
            </div>

            <div className="p-6 premium-glass-card rounded-2xl space-y-3.5">
              <div className="w-9 h-9 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-500 dark:text-violet-400">
                <Layers className="w-4.5 h-4.5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xs font-bold text-slate-800 dark:text-gray-200 uppercase tracking-wider">Architecture Intelligence</h3>
                <p className="text-[11px] text-slate-600 dark:text-zinc-400 leading-relaxed">Automatically map project structure, module boundaries, layering, and patterns.</p>
              </div>
            </div>

            <div className="p-6 premium-glass-card rounded-2xl space-y-3.5">
              <div className="w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-500 dark:text-rose-400">
                <Shield className="w-4.5 h-4.5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xs font-bold text-slate-800 dark:text-gray-200 uppercase tracking-wider">Security Review</h3>
                <p className="text-[11px] text-slate-600 dark:text-zinc-400 leading-relaxed">Scan configurations, check dependencies, and isolate hardcoded secrets or flaws.</p>
              </div>
            </div>

            <div className="p-6 premium-glass-card rounded-2xl space-y-3.5">
              <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500 dark:text-emerald-400">
                <BarChart3 className="w-4.5 h-4.5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xs font-bold text-slate-800 dark:text-gray-200 uppercase tracking-wider">Engineering Insights</h3>
                <p className="text-[11px] text-slate-600 dark:text-zinc-400 leading-relaxed">Assess overall complexity metrics, LOC, smells count, and modular coupling scores.</p>
              </div>
            </div>

            <div className="p-6 premium-glass-card rounded-2xl space-y-3.5">
              <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500 dark:text-amber-400">
                <CheckCircle2 className="w-4.5 h-4.5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xs font-bold text-slate-800 dark:text-gray-200 uppercase tracking-wider">Grounded AI</h3>
                <p className="text-[11px] text-slate-600 dark:text-zinc-400 leading-relaxed">Ensure all insights are strictly rooted in code snippets with detailed file citations.</p>
              </div>
            </div>

            <div className="p-6 premium-glass-card rounded-2xl space-y-3.5">
              <div className="w-9 h-9 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-500 dark:text-sky-400">
                <Zap className="w-4.5 h-4.5" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xs font-bold text-slate-800 dark:text-gray-200 uppercase tracking-wider">Lightning Fast Ingestion</h3>
                <p className="text-[11px] text-slate-600 dark:text-zinc-400 leading-relaxed">Utilize progressive parsing and indexing for high-speed analysis under 90 seconds.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Why Repository Mentor Info Segment */}
        <div className="w-full border-t border-slate-200 dark:border-zinc-900/60 pt-10 text-center space-y-4 max-w-2xl">
          <h2 className="text-sm font-bold text-slate-800 dark:text-white uppercase tracking-wider">Designed for Technical Portfolios</h2>
          <p className="text-xs text-slate-500 dark:text-zinc-400 leading-relaxed">
            Repository Mentor AI runs completely automated code analysis across security scanners, AST parsers, and vector chunking systems. Developed to showcase modern, enterprise-ready software development standards.
          </p>
        </div>

      </div>
      
      {/* Footer */}
      <footer className="w-full text-center py-10 text-[11px] text-slate-500 dark:text-zinc-500 mt-16 border-t border-slate-200 dark:border-zinc-900/40 space-y-2 bg-slate-100/50 dark:bg-[#020308]/40 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p>Repository Mentor AI &copy; 2026</p>
          <div className="flex items-center gap-4">
            <a 
              href="/developer/diagnostics" 
              className="text-slate-500 hover:text-indigo-600 dark:text-zinc-500 dark:hover:text-indigo-400 font-medium transition-all duration-200"
            >
              Diagnostics
            </a>
            <span className="text-slate-300 dark:text-zinc-800">|</span>
            <a 
              href="https://github.com/parthmandore/repository-mentor-ai" 
              target="_blank" 
              rel="noreferrer"
              className="text-slate-500 hover:text-slate-800 dark:text-zinc-500 dark:hover:text-white flex items-center gap-1 transition-all duration-200"
            >
              <Github className="w-3.5 h-3.5" /> Code
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
