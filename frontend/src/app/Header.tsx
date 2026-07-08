'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  ArrowLeft, Terminal, Github, Loader2, Sparkles, 
  Menu, X
} from 'lucide-react';
import ThemeToggle from './ThemeToggle';

interface HeaderProps {
  repoId: string;
  repoUrl: string;
  repoStatus: string;
  activeTab: 'overview' | 'security' | 'architecture' | 'mentor' | 'knowledge' | 'assessment' | 'performance';
}

export default function Header({ repoId, repoUrl, repoStatus, activeTab }: HeaderProps) {
  const router = useRouter();
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [isReanalysing, setIsReanalysing] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';
  const isCompleted = repoStatus === 'ready';
  const isProcessing = repoStatus !== 'ready' && repoStatus !== 'failed';

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(repoUrl);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleReanalyse = async () => {
    if (!window.confirm("Are you sure you want to trigger a full codebase re-analysis? This will delete all cached metrics, smells, and vector indexes, and run the pipeline from scratch.")) {
      return;
    }
    setIsReanalysing(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/reanalyse`, {
        method: 'POST'
      });
      if (res.ok) {
        // Redirect to overview to show ingestion checklist
        router.push(`/repositories/${repoId}`);
        setTimeout(() => window.location.reload(), 500);
      } else {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to trigger full re-analysis');
      }
    } catch (err: any) {
      alert(err.message || 'Re-analysis failed');
    } finally {
      setIsReanalysing(false);
    }
  };

  const tabs = [
    { key: 'overview', label: 'Overview', path: `/repositories/${repoId}` },
    { key: 'security', label: 'Security', path: `/repositories/${repoId}/security` },
    { key: 'architecture', label: 'Architecture', path: `/repositories/${repoId}/architecture` },
    { key: 'mentor', label: 'Mentor', path: `/repositories/${repoId}/mentor`, icon: Sparkles },
    { key: 'knowledge', label: 'Knowledge', path: `/repositories/${repoId}/knowledge` },
  ];

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-bgSecondary border-b border-borderPrimary shadow-[0_1px_3px_rgba(0,0,0,0.08)] dark:shadow-[0_1px_3px_rgba(0,0,0,0.3)] transition-all duration-200">
      <div className="w-full max-w-[1700px] mx-auto px-4 sm:px-6 lg:px-12 py-3.5 flex flex-col lg:flex-row justify-between lg:items-center gap-4">
        
        {/* Left Side: Back button, Title and Repo Details */}
        <div className="flex items-center justify-between w-full lg:w-auto">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => router.push('/')} 
              className="p-2 bg-slate-100 dark:bg-zinc-900/50 hover:bg-slate-200 dark:hover:bg-zinc-800 border border-slate-200 dark:border-zinc-800/80 rounded-xl text-textSecondary hover:text-textPrimary transition-all duration-150 shadow-sm" 
              title="Change Repository"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <h1 className="text-sm sm:text-base font-bold text-textPrimary tracking-tight flex items-center gap-2">
                <Terminal className="w-4.5 h-4.5 text-brand-500 dark:text-brand-400" />
                Repository Mentor AI
              </h1>
              <p className="text-[10px] text-textSecondary flex flex-wrap items-center gap-2 mt-0.5">
                <span className="flex items-center gap-1">
                  <Github className="w-3 h-3 text-slate-400 dark:text-zinc-500" />
                  <span className="truncate max-w-[110px] sm:max-w-[180px] md:max-w-[260px] font-mono">{repoUrl}</span>
                </span>
                <span className="flex items-center gap-1.5 flex-wrap">
                  <button 
                    onClick={handleCopyUrl} 
                    className="hover:text-textPrimary text-[9px] bg-slate-100 dark:bg-zinc-900 px-1.5 py-0.5 rounded border border-slate-200 dark:border-zinc-800 transition-all active:scale-95 shadow-sm font-mono"
                  >
                    {isCopied ? 'Copied' : 'Copy'}
                  </button>
                  <button 
                    onClick={handleReanalyse} 
                    disabled={isReanalysing || isProcessing}
                    className="hover:text-textPrimary text-[9px] bg-brand-50 dark:bg-brand-950/30 text-brand-600 dark:text-brand-400 hover:bg-brand-100 dark:hover:bg-brand-900/40 px-2 py-0.5 rounded border border-brand-200 dark:border-brand-500/25 transition-all active:scale-95 disabled:opacity-45 flex items-center gap-1 font-semibold shadow-sm"
                    title="Re-analyse codebase from scratch"
                  >
                    {isReanalysing && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
                    Re-analyse
                  </button>
                  <button 
                    onClick={() => router.push('/')} 
                    className="hover:text-textPrimary text-[9px] bg-slate-100 dark:bg-zinc-900 px-2 py-0.5 rounded border border-slate-200 dark:border-zinc-800 transition-all active:scale-95 font-semibold shadow-sm"
                    title="Analyze another repository"
                  >
                    Change Repo
                  </button>
                </span>
              </p>
            </div>
          </div>
          
          {/* Hamburger / Toggle button for Mobile/Tablet */}
          <div className="flex items-center gap-2 lg:hidden">
            <ThemeToggle />
            <button 
              onClick={() => setIsNavOpen(!isNavOpen)}
              className="p-2 rounded-lg border border-borderPrimary hover:bg-slate-100 dark:hover:bg-zinc-900 text-textSecondary transition-all"
            >
              {isNavOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Desktop Tab Navigation */}
        <div className="hidden lg:flex items-center gap-3">
          {isCompleted && (
            <nav className="flex items-center gap-1 bg-slate-100 dark:bg-[#090a12]/60 border border-slate-200 dark:border-zinc-800/80 p-1 rounded-xl shadow-inner">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.key;
                const Icon = tab.icon;
                return (
                  <button 
                    key={tab.key}
                    onClick={() => router.push(tab.path)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all duration-200 flex items-center gap-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:focus-visible:ring-brand-400 ${
                      isActive 
                        ? 'bg-white dark:bg-indigo-500/10 text-brand-600 dark:text-indigo-305 border border-slate-200 dark:border-indigo-500/20 shadow-sm'
                        : 'text-textSecondary hover:text-textPrimary hover:bg-white dark:hover:bg-zinc-900'
                    }`}
                  >
                    {Icon && <Icon className="w-3.5 h-3.5" />}
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          )}
          <ThemeToggle />
        </div>

        {/* Mobile/Tablet Dropdown Navigation Menu */}
        {isNavOpen && isCompleted && (
          <div className="w-full lg:hidden py-2 border-t border-borderPrimary mt-2 animate-fade-in">
            <nav className="flex flex-col gap-1.5">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.key;
                const Icon = tab.icon;
                return (
                  <button 
                    key={tab.key}
                    onClick={() => { router.push(tab.path); setIsNavOpen(false); }}
                    className={`w-full text-left px-4 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 flex items-center gap-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:focus-visible:ring-brand-400 ${
                      isActive 
                        ? 'bg-slate-100 dark:bg-indigo-500/10 text-brand-600 dark:text-indigo-305 border border-slate-200 dark:border-indigo-500/20 shadow-sm'
                        : 'text-textSecondary hover:text-textPrimary hover:bg-slate-50 dark:hover:bg-zinc-900'
                    }`}
                  >
                    {Icon && <Icon className="w-3.5 h-3.5" />}
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}
