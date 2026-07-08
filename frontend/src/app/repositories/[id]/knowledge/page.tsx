'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, ArrowRight, Loader2, ShieldAlert, BookOpen, CheckCircle2,
  FileText, Cpu, AlertCircle, Database, Server, RefreshCw,
  LayoutList, ChevronRight, Search, Activity, Shield, Info, HelpCircle,
  Layers, Sparkles, FolderHeart, Milestone, Terminal, Library, GraduationCap, Gauge
} from 'lucide-react';

import Header from '../../../Header';

interface EvidenceDocEntry {
  document_type: string;
  title: string;
  summary: string;
  source_file: string;
}

interface SearchResult {
  document: string;
  metadata: {
    source: string;
    line_start?: number;
    type?: string;
  };
  distance: number;
}

interface WikiCard {
  items: string[];
  reason_if_empty: string;
}

interface LearningReport {
  purpose: string;
  architecture: string;
  tech_stack: string;
  design_patterns: string[];
  complexity: string;
  security: string;
  maintainability: string;
  strengths: string[];
  weaknesses: string[];
  top_improvements: string[];
  interview_questions: string[];
  resume_highlights: string[];
  recruiter_summary: string;
}

interface KnowledgeSummary {
  total_chunks: number;
  code_chunks: number;
  evidence_documents: number;
  indexed_files: number;
  supported_languages: string[];
  build_status: string;
  embedding_status: string;
  evidence_docs_list: EvidenceDocEntry[];
  summary_description?: string;
  wiki_data?: Record<string, WikiCard>;
  learning_report?: LearningReport;
  timing_metadata?: Record<string, number | string>;
  knowledge_graph?: {
    nodes: Array<{ id: string; label: string; type: string }>;
    edges: Array<{ source: string; target: string; type: string }>;
  };
}

interface RepositoryResponse {
  id: string;
  url: string;
  status: string;
  status_message: string | null;
  knowledge_status: string;
  error_message: string | null;
}

const STATUS_CONFIGS: Record<string, { label: string; text: string; border: string; bg: string; icon: any }> = {
  completed: { label: 'Ready for AI', text: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/10', icon: CheckCircle2 },
  indexing: { label: 'Building Index', text: 'text-indigo-400', border: 'border-indigo-500/30', bg: 'bg-indigo-500/10', icon: Loader2 },
  pending: { label: 'Pending Build', text: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10', icon: AlertCircle },
  failed: { label: 'Build Failed', text: 'text-rose-400', border: 'border-rose-500/30', bg: 'bg-rose-500/10', icon: ShieldAlert },
};

export default function KnowledgeBasePage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';

  const [repo, setRepo] = useState<RepositoryResponse | null>(null);
  const [summary, setSummary] = useState<KnowledgeSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRetrying, setIsRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Tab State
  const [activeTab, setActiveTab] = useState<'wiki' | 'report'>('wiki');

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const fetchRepoAndSummary = useCallback(async () => {
    try {
      const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
      if (!repoRes.ok) throw new Error('Repository detail not found.');
      const repoData = await repoRes.json();
      setRepo(repoData);

      const pct = (() => {
        if (!repoData.status_message) return 0;
        const match = repoData.status_message.match(/(\d+)%\s+complete/);
        return match ? parseInt(match[1]) : 0;
      })();
      
      const isUnlocked = repoData.knowledge_status === 'completed' || 
        (repoData.knowledge_status === 'indexing' && pct >= 40);

      if (isUnlocked || repoData.knowledge_status === 'failed') {
        const summaryRes = await fetch(`${apiUrl}/repositories/${repoId}/knowledge/summary`);
        if (summaryRes.ok) {
          setSummary(await summaryRes.json());
        }
      }
      setIsLoading(false);
      setError(null);
      return repoData.knowledge_status;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch details');
      setIsLoading(false);
      return 'failed';
    }
  }, [apiUrl, repoId]);

  useEffect(() => {
    fetchRepoAndSummary();
    const interval = setInterval(async () => {
      const kStatus = await fetchRepoAndSummary();
      if (kStatus === 'completed' || kStatus === 'failed') {
        clearInterval(interval);
      }
    }, 4000);
    return () => clearInterval(interval);
  }, [repoId, fetchRepoAndSummary]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/knowledge/search?query=${encodeURIComponent(searchQuery)}`);
      if (res.ok) {
        setSearchResults(await res.json());
      }
    } catch (err) {
      console.error(err);
    }
    setIsSearching(false);
  };

  const handleRetryBuild = async () => {
    setIsRetrying(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/analyze`, { method: 'POST' });
      if (res.ok) {
        setRepo(prev => prev ? { ...prev, knowledge_status: 'indexing' } : null);
        setError(null);
      }
    } catch (err) {
      console.error(err);
    }
    setIsRetrying(false);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary text-textPrimary">
        <div className="text-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 mx-auto" />
          <p className="text-sm text-textSecondary">Loading Knowledge Base overview...</p>
        </div>
      </div>
    );
  }

  const kStatus = repo?.knowledge_status || 'pending';
  const statusConfig = STATUS_CONFIGS[kStatus] || STATUS_CONFIGS.pending;
  const StatusIcon = statusConfig.icon;

  if (error || !repo) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-6 rounded-2xl shadow-md text-center space-y-6">
          <ShieldAlert className="w-8 h-8 text-rose-500 mx-auto" />
          <h2 className="text-xl font-bold text-textPrimary">Error</h2>
          <p className="text-sm text-textSecondary">{error}</p>
          <button onClick={() => router.push(`/repositories/${repoId}`)} className="w-full py-2.5 px-4 bg-slate-100 dark:bg-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-800 border border-slate-200 dark:border-zinc-800 text-textPrimary rounded-xl text-sm font-semibold transition-all">
            Return to Overview
          </button>
        </div>
      </div>
    );
  }

  const pctVal = (() => {
    if (!repo?.status_message) return 0;
    const match = repo.status_message.match(/(\d+)%\s+complete/);
    return match ? parseInt(match[1]) : 0;
  })();

  if (repo && (repo.knowledge_status === 'pending' || (repo.knowledge_status === 'indexing' && pctVal < 40))) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4 font-sans text-center text-textPrimary">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-8 rounded-2xl shadow-md space-y-6">
          <Loader2 className="w-10 h-10 animate-spin text-brand-500 mx-auto" />
          <div className="space-y-2">
            <h2 className="text-lg font-bold text-textPrimary tracking-tight flex items-center justify-center gap-2">
              Building Knowledge Base Index
            </h2>
            <p className="text-xs text-textSecondary">
              The codebase knowledge base is currently indexing. This tab will unlock automatically once index progression reaches 40%.
            </p>
          </div>
          <div className="bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900/60 p-4 rounded-xl text-xs space-y-2 text-left">
            <div className="flex justify-between items-center text-textSecondary">
              <span>Current Indexing Progress</span>
              <span className="text-[10px] text-brand-600 dark:text-brand-400 font-bold uppercase tracking-wider animate-pulse">{pctVal}%</span>
            </div>
            <div className="flex justify-between items-center text-slate-400 dark:text-zinc-500">
              <span>Unlock Threshold</span>
              <span>40%</span>
            </div>
          </div>
          <p className="text-[10px] text-textSecondary font-mono">Status: {repo.status_message || 'Indexing...'}</p>
          <button
            onClick={() => router.push(`/repositories/${repoId}`)}
            className="w-full py-2.5 px-4 bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-800 text-textPrimary rounded-xl text-xs font-semibold transition-all"
          >
            Back to Overview
          </button>
        </div>
      </div>
    );
  }

  const wiki = summary?.wiki_data || {};

  const wikiCardsList = [
    { key: 'controllers', label: 'Controllers / APIs', icon: Server },
    { key: 'services', label: 'Services Layer', icon: Cpu },
    { key: 'repositories', label: 'Data Access Repositories', icon: Database },
    { key: 'entities', label: 'Data Models / Entities', icon: FileText },
    { key: 'utilities', label: 'Utilities & Helpers', icon: FolderHeart },
    { key: 'configurations', label: 'Configurations', icon: Info },
    { key: 'architecture', label: 'Architecture Patterns', icon: Layers },
    { key: 'entry_points', label: 'Entry Points', icon: Terminal },
    { key: 'important_files', label: 'Important Modules', icon: Milestone },
    { key: 'dependencies', label: 'Dependencies Manifest', icon: Library }
  ];

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans selection:bg-brand-500/20 transition-colors duration-300">
      {/* Background glow */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-brand-500/5 rounded-full blur-[120px] pointer-events-none -z-10 animate-slow-blob-1" />

      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="knowledge" 
      />

      {/* Main Content */}
      <main className="w-full max-w-[1700px] mx-auto px-4 sm:px-6 lg:px-12 pt-[92px] pb-6 space-y-6 flex-grow">
        {kStatus === 'failed' && (
          <div className="p-6 bg-bgSecondary border border-rose-500/20 rounded-2xl space-y-4 shadow-sm">
            <div className="flex items-start gap-4">
              <ShieldAlert className="w-10 h-10 text-rose-500 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h3 className="text-md font-bold text-textPrimary">Knowledge Base unavailable.</h3>
                <p className="text-sm text-textSecondary">Reason: Embedding generation failed or database connection was interrupted. Please verify your internet connection and API keys.</p>
              </div>
            </div>
            <button onClick={handleRetryBuild} disabled={isRetrying} className="py-2.5 px-5 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-semibold flex items-center gap-2 transition-all disabled:opacity-50 shadow-sm">
              {isRetrying ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              Retry Index Build
            </button>
          </div>
        )}

        {kStatus !== 'failed' && (
          <>
            {kStatus === 'indexing' && (
              <div className="p-3.5 bg-indigo-500/5 border border-indigo-500/15 rounded-xl flex items-center justify-between text-xs text-brand-600 dark:text-indigo-300 shadow-sm animate-pulse">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-500 dark:text-indigo-400" />
                  <span>Knowledge Base Wiki is live with partial repository files. Indexing continues in the background...</span>
                </div>
                <span className="font-mono text-[9px] bg-brand-500/10 px-2 py-0.5 rounded border border-brand-500/15">
                  {repo?.status_message || 'Indexing...'}
                </span>
              </div>
            )}

            {/* Status indicators */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-5 flex items-center justify-between shadow-sm">
                <div className="space-y-1">
                  <span className="text-[10px] text-textSecondary uppercase tracking-wider block font-semibold">Vector Index Status</span>
                  <h2 className="text-md font-bold text-textPrimary flex items-center gap-1.5">
                    <StatusIcon className={`w-4 h-4 ${kStatus === 'indexing' ? 'animate-spin' : ''} ${statusConfig.text}`} />
                    {statusConfig.label}
                  </h2>
                </div>
              </div>
              <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-5 text-center shadow-sm">
                <span className="text-[10px] text-textSecondary uppercase font-semibold block">Total Chunks</span>
                <p className="text-xl font-bold text-textPrimary mt-1">{summary?.total_chunks || 0}</p>
              </div>
              <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-5 text-center shadow-sm">
                <span className="text-[10px] text-textSecondary uppercase font-semibold block">Evidence Documents</span>
                <p className="text-xl font-bold text-brand-500 dark:text-brand-400 mt-1">{summary?.evidence_documents || 0}</p>
              </div>
              <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-5 text-center shadow-sm">
                <span className="text-[10px] text-textSecondary uppercase font-semibold block">Indexed Files</span>
                <p className="text-xl font-bold text-textPrimary mt-1">{summary?.indexed_files || 0}</p>
              </div>
            </div>

            {summary && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left Panel: Wiki or Learning Report */}
                <div className="lg:col-span-2 space-y-6">
                  <div className="space-y-6">
                    {/* Wiki Cards */}
                    <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-6 shadow-sm">
                      <h3 className="text-xs font-bold text-textSecondary uppercase tracking-wider flex items-center gap-1.5 font-mono">
                        <Layers className="w-4 h-4 text-brand-500 dark:text-brand-400 animate-pulse" /> Repository Knowledge Cards
                      </h3>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {wikiCardsList.map(({ key, label, icon: Icon }) => {
                          const card = wiki[key] || { items: [], reason_if_empty: 'No information parsed for this module.' };
                          const hasItems = card.items && card.items.length > 0;
                          return (
                            <div key={key} className="p-4 bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 rounded-xl space-y-2 flex flex-col justify-between shadow-inner">
                              <div className="space-y-1.5">
                                <span className="font-bold text-textPrimary text-xs flex items-center gap-1.5">
                                  <Icon className="w-3.5 h-3.5 text-brand-500 dark:text-brand-400 animate-none" /> {label}
                                </span>
                                {hasItems ? (
                                  <ul className="list-disc list-inside text-textSecondary text-[11px] space-y-1">
                                    {card.items.slice(0, 4).map((item, idx) => (
                                      <li key={idx} className="truncate text-textSecondary">{item}</li>
                                    ))}
                                    {card.items.length > 4 && (
                                      <li className="text-[10px] text-textSecondary list-none font-semibold">
                                        + {card.items.length - 4} more files
                                      </li>
                                    )}
                                  </ul>
                                ) : (
                                  <p className="text-textSecondary text-[10px] leading-relaxed italic">{card.reason_if_empty}</p>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Suggested Questions Panel */}
                    <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-4 shadow-sm">
                      <h3 className="text-xs font-bold text-textPrimary uppercase tracking-wider flex items-center gap-1.5 font-mono">
                        <HelpCircle className="w-4 h-4 text-brand-500 dark:text-brand-400" /> Suggested Recruiter Inquiries
                      </h3>
                      <p className="text-[11px] text-textSecondary leading-relaxed">
                        Select an inquiry below to populate it inside the AI Code Mentor:
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {[
                          "Explain the overall architecture.",
                          "What are the biggest security concerns?",
                          "Which modules should be refactored first?"
                        ].map((q) => (
                          <button
                            key={q}
                            onClick={() => router.push(`/repositories/${repoId}/mentor?q=${encodeURIComponent(q)}`)}
                            className="p-4 bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 hover:border-brand-500/30 hover:bg-brand-500/5 text-left rounded-xl transition-all duration-200 group active:scale-98 shadow-sm"
                          >
                            <p className="text-xs font-bold text-textPrimary group-hover:text-brand-600 dark:group-hover:text-brand-300 transition-colors leading-snug">{q}</p>
                            <span className="text-[9px] text-textSecondary group-hover:text-textPrimary font-semibold flex items-center gap-1 mt-2.5">
                              Ask Mentor <ArrowRight className="w-3 h-3 transition-transform group-hover:translate-x-0.5" />
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Panel: Project Metadata & Pipeline metrics */}
                <div className="space-y-6">
                  {/* Supported Languages */}
                  <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-3 shadow-sm">
                    <h3 className="text-xs font-bold text-textPrimary uppercase tracking-wider flex items-center gap-1.5 font-mono">
                      <Terminal className="w-4 h-4 text-brand-500 dark:text-brand-400" /> Supported Languages
                    </h3>
                    <div className="flex flex-wrap gap-1.5">
                      {summary.supported_languages && summary.supported_languages.length > 0 ? (
                        summary.supported_languages.map(lang => (
                          <span 
                            key={lang} 
                            className="px-2.5 py-1 bg-brand-500/10 dark:bg-brand-500/10 border border-slate-200 dark:border-zinc-800/20 text-brand-600 dark:text-brand-300 text-[10px] rounded-lg font-bold"
                          >
                            {lang}
                          </span>
                        ))
                      ) : (
                        <span className="text-[10px] text-textSecondary italic">No languages detected.</span>
                      )}
                    </div>
                  </div>

                  {/* Timing progress trackers */}
                  <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-4 shadow-sm">
                    <h3 className="text-xs font-bold text-textPrimary uppercase tracking-wider flex items-center gap-1.5 font-mono">
                      <Activity className="w-4 h-4 text-brand-500 dark:text-brand-400" /> Pipeline Timings
                    </h3>
                    <div className="space-y-3 text-xs leading-normal">
                      {summary.timing_metadata ? (
                        <>
                          {Object.entries(summary.timing_metadata).map(([stage, secs]: any) => (
                            <div key={stage} className="space-y-1">
                              <div className="flex justify-between items-center text-[11px] text-textSecondary">
                                <span className="capitalize font-medium">{stage}</span>
                                <span className="font-mono text-textPrimary">{parseFloat(secs).toFixed(2)}s</span>
                              </div>
                              <div className="h-1 bg-slate-200 dark:bg-zinc-900 rounded-full overflow-hidden">
                                <div 
                                  className="h-full bg-brand-500 rounded-full" 
                                  style={{ width: `${Math.min(100, (parseFloat(secs) / 10.0) * 100)}%` }}
                                />
                              </div>
                            </div>
                          ))}
                        </>
                      ) : (
                        <p className="text-[10px] text-textSecondary italic">No timing metadata found.</p>
                      )}
                    </div>
                  </div>
                </div>

              </div>
            )}
          </>
        )}
      </main>

      <footer className="w-full text-center py-6 text-xs text-slate-500 dark:text-zinc-500 border-t border-slate-200 dark:border-zinc-900/40 mt-8 font-mono">
        Repository Mentor AI &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
}
