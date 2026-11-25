'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  ArrowLeft, Github, Loader2, Sparkles, 
  Menu, X, Check, Copy, RefreshCw
} from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { useToast } from './ToastProvider';

interface HeaderProps {
  repoId: string;
  repoUrl: string;
  repoStatus: string;
  activeTab?: 'overview' | 'security' | 'architecture' | 'mentor' | 'knowledge' | 'assessment' | 'performance';
}

export default function Header({ repoId, repoUrl, repoStatus, activeTab }: HeaderProps) {
  const router = useRouter();
  const toast = useToast();
  const [isNavOpen, setIsNavOpen] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [isReanalysing, setIsReanalysing] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  const isCompleted = repoStatus === 'ready';

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(repoUrl);
    setIsCopied(true);
    toast.success('Repository URL copied to clipboard');
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleReanalyse = async () => {
    if (!window.confirm("Trigger a full re-analysis? This refreshes all metrics and inspections.")) {
      return;
    }
    setIsReanalysing(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/reanalyse`, {
        method: 'POST'
      });
      if (res.ok) {
        toast.info('Re-analysis started. Re-evaluating repository...');
        router.push(`/repositories/${repoId}`);
        setTimeout(() => window.location.reload(), 500);
      } else {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to trigger full re-analysis');
      }
    } catch (err: any) {
      toast.error(err.message || 'Re-analysis failed');
    } finally {
      setIsReanalysing(false);
    }
  };

  const tabs = [
    { key: 'overview', label: '01. Overview', path: `/repositories/${repoId}` },
    { key: 'assessment', label: '02. Assessment', path: `/repositories/${repoId}/assessment` },
    { key: 'architecture', label: '03. Architecture', path: `/repositories/${repoId}/architecture` },
    { key: 'security', label: '04. Security', path: `/repositories/${repoId}/security` },
    { key: 'performance', label: '05. Performance', path: `/repositories/${repoId}/performance` },
    { key: 'mentor', label: '06. AI Mentor', path: `/repositories/${repoId}/mentor`, icon: Sparkles },
    { key: 'knowledge', label: '07. Knowledge', path: `/repositories/${repoId}/knowledge` },
  ];

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-bgSecondary/95 backdrop-blur-sm border-b border-borderPrimary transition-colors duration-200">
      <div className="w-full max-w-[1700px] mx-auto px-4 sm:px-6 lg:px-10 py-3 flex flex-col lg:flex-row justify-between lg:items-center gap-3">
        
        {/* Left Side: Back button, Title and Repo Details */}
        <div className="flex items-center justify-between w-full lg:w-auto">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => router.push('/')} 
              className="p-1.5 rounded-lg border border-borderPrimary hover:border-borderStrong bg-bgPrimary text-textSecondary hover:text-textPrimary transition-colors" 
              title="Return to Landing"
              aria-label="Return to Landing"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-serif font-bold text-base tracking-tight text-textPrimary">
                  RepoMentor
                </span>
                <span className="section-header px-1.5 py-0.5 rounded bg-bgTertiary text-[9px] text-textSecondary border border-borderPrimary">
                  FIELD REPORT
                </span>
              </div>
              <div className="text-[11px] text-textSecondary flex items-center gap-2 mt-0.5 font-mono">
                <span className="truncate max-w-[140px] sm:max-w-[220px] md:max-w-[320px] text-textPrimary font-medium">
                  {repoUrl.replace(/^https?:\/\/github\.com\//, '')}
                </span>
                <span className="text-borderPrimary">•</span>
                <button 
                  onClick={handleCopyUrl}
                  className="hover:text-textPrimary underline underline-offset-2 flex items-center gap-1"
                  title="Copy GitHub URL"
                >
                  {isCopied ? <Check className="w-3 h-3 text-good" /> : 'copy'}
                </button>
                <span className="text-borderPrimary">•</span>
                <button 
                  onClick={handleReanalyse} 
                  disabled={isReanalysing}
                  className="hover:text-signal disabled:opacity-40 transition-colors flex items-center gap-1"
                  title="Re-run inspection"
                >
                  {isReanalysing ? <Loader2 className="w-3 h-3 animate-spin text-signal" /> : <RefreshCw className="w-3 h-3" />}
                  <span>re-scan</span>
                </button>
              </div>
            </div>
          </div>
          
          {/* Hamburger / Toggle button for Mobile/Tablet */}
          <div className="flex items-center gap-2 lg:hidden">
            <ThemeToggle />
            <button 
              onClick={() => setIsNavOpen(!isNavOpen)}
              className="p-1.5 rounded-lg border border-borderPrimary text-textSecondary hover:text-textPrimary transition-colors"
              aria-label={isNavOpen ? "Close menu" : "Open menu"}
            >
              {isNavOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Desktop Tab Navigation */}
        <div className="hidden lg:flex items-center gap-4">
          {isCompleted && (
            <nav className="flex items-center gap-0.5" role="tablist" aria-label="Report navigation">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.key;
                const Icon = tab.icon;
                return (
                  <button 
                    key={tab.key}
                    onClick={() => router.push(tab.path)}
                    role="tab"
                    aria-selected={isActive}
                    className={`px-3 py-1.5 text-xs font-mono tracking-tight transition-all rounded-md flex items-center gap-1.5 ${
                      isActive 
                        ? 'text-signal font-bold bg-signal/10 border border-signal/20'
                        : 'text-textSecondary hover:text-textPrimary hover:bg-bgTertiary border border-transparent'
                    }`}
                  >
                    {Icon && <Icon className="w-3 h-3 text-signal" />}
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </nav>
          )}
          <div className="h-4 w-px bg-borderPrimary" />
          <ThemeToggle />
        </div>

        {/* Mobile Dropdown Navigation Menu */}
        {isNavOpen && isCompleted && (
          <div className="w-full lg:hidden py-2 border-t border-borderPrimary mt-2 animate-fade-in">
            <nav className="flex flex-col gap-1" role="tablist" aria-label="Mobile report navigation">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.key;
                const Icon = tab.icon;
                return (
                  <button 
                    key={tab.key}
                    onClick={() => { router.push(tab.path); setIsNavOpen(false); }}
                    role="tab"
                    aria-selected={isActive}
                    className={`w-full text-left px-3 py-2 rounded-md text-xs font-mono transition-colors flex items-center justify-between ${
                      isActive 
                        ? 'text-signal font-bold bg-signal/10 border border-signal/20'
                        : 'text-textSecondary hover:text-textPrimary hover:bg-bgTertiary'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      {Icon && <Icon className="w-3.5 h-3.5 text-signal" />}
                      {tab.label}
                    </span>
                    {isActive && <span className="w-1.5 h-1.5 rounded-full bg-signal" />}
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
