'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Github, Terminal, Sparkles, AlertCircle, CheckCircle, Cpu, ArrowLeft,
  Loader2, Clock, Shield, ChevronLeft, ChevronRight, Activity, 
  Layers, Copy, BookOpen, FileJson, FileCode, ArrowUpRight, 
  CheckSquare, Keyboard, HelpCircle as HelpIcon, Flame, AlertTriangle, ShieldAlert, Gauge,
  ChevronDown, ChevronUp
} from 'lucide-react';

import Header from '../../Header';

interface Recommendation {
  id: string;
  title: string;
  priority: string;
  category: string;
  effort: string;
  difficulty: string;
  health_improvement: number;
  security_improvement: number;
  architecture_improvement: number;
  maintainability_improvement: number;
  why_it_matters: string;
  steps: string[];
  affected_files: string[];
  related_issues: Array<{ id: string; file_path: string; line_number: number | null; type: string }>;
  before_code?: string;
  after_code?: string;
}

interface RepositoryData {
  id: string;
  url: string;
  status: string;
  status_message: string | null;
  total_files: number;
  total_folders: number;
  text_file_count: number;
  binary_file_count: number;
  language_breakdown: Record<string, number> | null;
  tech_stack: { frameworks: string[]; package_manager: string } | null;
  health_score: number;
  health_grade: string;
  total_lines_of_code: number;
  average_complexity: number;
  max_complexity: number;
  total_smells: number;
  duplication_percentage: number;
  files_analyzed: number;
  files_skipped: number;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  analysis_started_at: string | null;
  analysis_completed_at: string | null;
  analysis_duration_seconds: number | null;
  error_message: string | null;
  created_at: string;
  knowledge_summary?: {
    summary_description?: string;
    timing_metadata?: Record<string, number>;
    health_metadata?: {
      final_score?: number;
      breakdown?: Record<string, { score: number; max: number }>;
      details?: Array<{ dimension: string; type: string; rule: string; measured: string; impact: number; reason: string }>;
    };
    knowledge_objects?: {
      files?: Array<{
        path: string;
        loc: number;
        complexity: number;
        smells_count: number;
        extension?: string;
      }>;
    };
  } | null;
  knowledge_status?: string;
  progress?: Record<string, { status: string; duration?: number }>;
  current_stage?: string;
}

interface ScannedFile {
  id: string;
  repository_id: string;
  path: string;
  extension: string;
  size_bytes: number;
  content_hash: string;
  is_text: boolean;
  lines_of_code: number;
  complexity: number;
  code_smells_count: number;
}

interface FilesResponse {
  total: number;
  skip: number;
  limit: number;
  files: ScannedFile[];
}

const GRADE_COLORS: Record<string, string> = {
  A: 'accent-green border',
  B: 'accent-blue border',
  C: 'accent-amber border',
  D: 'accent-orange border',
  F: 'accent-red border',
};

const SEVERITY_TEXT_COLORS: Record<string, string> = {
  Critical: 'text-red-500',
  High: 'text-orange-500',
  Medium: 'text-yellow-500',
  Low: 'text-blue-500',
  Info: 'text-gray-400',
};

const SEVERITY_BORDER_COLORS: Record<string, string> = {
  Critical: 'border-red-500/30 bg-red-500/5',
  High: 'border-orange-500/25 bg-orange-500/5',
  Medium: 'border-yellow-500/25 bg-yellow-500/5',
  Low: 'border-blue-500/25 bg-blue-500/5',
  Info: 'border-gray-800 bg-gray-900/40',
};

const LANG_COLORS = [
  'bg-violet-500', 'bg-emerald-500', 'bg-amber-500', 'bg-sky-500',
  'bg-rose-500', 'bg-indigo-500', 'bg-fuchsia-500', 'bg-teal-500'
];

const LANG_TEXT_COLORS = [
  'accent-purple border',
  'accent-green border',
  'accent-amber border',
  'accent-blue border',
  'accent-red border',
  'accent-indigo border',
  'accent-fuchsia border',
  'accent-teal border'
];

const PIPELINE_STEPS = [
  { status: 'queued', label: 'Repository queued' },
  { status: 'cloning', label: 'Cloning repository...' },
  { status: 'parsing', label: 'Scanning project files...' },
  { status: 'detecting_technologies', label: 'Detecting technologies...' },
  { status: 'analyzing', label: 'Running analysis...' },
  { status: 'finalizing', label: 'Preparing overview...' },
];

export default function RepositoryDetail({ params }: { params: { id: string } }) {
  const router = useRouter();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';

  // API states
  const [repo, setRepo] = useState<RepositoryData | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [forecast, setForecast] = useState<any[]>([]);
  const [potentialScore, setPotentialScore] = useState<number>(100);
  const [maxAchievable, setMaxAchievable] = useState<number>(100);
  const [filesData, setFilesData] = useState<FilesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(0);
  const limit = 10;

  const [isCopied, setIsCopied] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [isRetryingKb, setIsRetryingKb] = useState(false);
  const [isReanalysing, setIsReanalysing] = useState(false);
  const [expandedRecId, setExpandedRecId] = useState<string | null>(null);
  const [isLedgerExpanded, setIsLedgerExpanded] = useState(false);
  const [isPlannerExpanded, setIsPlannerExpanded] = useState(false);

  const fetchRepository = useCallback(async () => {
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}`);
      if (!res.ok) throw new Error('Repository not found.');
      const data = await res.json();
      setRepo(data);
      setIsLoading(false);
      setError(null);
      return data.status;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch details');
      setIsLoading(false);
      return 'failed';
    }
  }, [apiUrl, repoId]);

  const fetchRecommendations = useCallback(async () => {
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/recommendations`);
      if (res.ok) {
        const data = await res.json();
        setRecommendations(data.recommendations || []);
        setForecast(data.forecast || []);
        setPotentialScore(data.potential_score || 100);
        setMaxAchievable(data.max_achievable || 100);
      }
    } catch (err) {
      console.error('Error fetching recommendations:', err);
    }
  }, [apiUrl, repoId]);

  const fetchFiles = useCallback(async (page: number) => {
    try {
      const skip = page * limit;
      const res = await fetch(`${apiUrl}/repositories/${repoId}/files?skip=${skip}&limit=${limit}`);
      if (res.ok) setFilesData(await res.json());
    } catch (err) {
      console.error('Error fetching files:', err);
    }
  }, [apiUrl, repoId, limit]);

  // Keyboard Shortcuts (Linear-style navigation)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      
      switch (e.key) {
        case '1':
          router.push(`/repositories/${repoId}`);
          break;
        case '2':
          router.push(`/repositories/${repoId}/security`);
          break;
        case '3':
          router.push(`/repositories/${repoId}/architecture`);
          break;
        case '4':
          router.push(`/repositories/${repoId}/mentor`);
          break;
        case '5':
          router.push(`/repositories/${repoId}/knowledge`);
          break;
        case 'a':
          router.push(`/repositories/${repoId}/assessment`);
          break;
        default:
          break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [repoId, router]);

  // Polling loop for active analysis
  useEffect(() => {
    fetchRepository().then((status) => {
      if (status === 'ready') {
        fetchFiles(0);
        fetchRecommendations();
      }
    });

    let pollCount = 0;
    const interval = setInterval(async () => {
      pollCount++;
      const status = await fetchRepository();
      const isKbFinished = repo && repo.knowledge_status !== 'indexing' && repo.knowledge_status !== 'pending';
      
      if (status === 'failed' || pollCount > 60 || (status === 'ready' && isKbFinished)) {
        clearInterval(interval);
        if (status === 'ready') {
          fetchFiles(0);
          fetchRecommendations();
        }
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [repoId, fetchRepository, fetchFiles, fetchRecommendations, repo?.knowledge_status]);

  const handleCopyUrl = () => {
    if (!repo) return;
    navigator.clipboard.writeText(repo.url);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleRetry = async () => {
    if (!repo) return;
    setIsRetrying(true);
    try {
      const res = await fetch(`${apiUrl}/repositories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: repo.url })
      });
      if (res.ok) {
        setError(null);
        setIsLoading(true);
        const status = await fetchRepository();
        if (status === 'ready') {
          fetchFiles(0);
          fetchRecommendations();
        }
      } else {
        throw new Error('Failed to submit repository for retry');
      }
    } catch (err: any) {
      alert(err.message || 'Retry failed');
    } finally {
      setIsRetrying(false);
    }
  };

  const handleRetryKb = async () => {
    setIsRetryingKb(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/knowledge/retry`, {
        method: 'POST'
      });
      if (res.ok) {
        setError(null);
        await fetchRepository();
      } else {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to trigger Knowledge Base retry');
      }
    } catch (err: any) {
      alert(err.message || 'KB retry failed');
    } finally {
      setIsRetryingKb(false);
    }
  };

  const handleReanalyse = async () => {
    if (!repo) return;
    if (!window.confirm("Are you sure you want to trigger a full codebase re-analysis? This will delete all cached metrics, smells, and vector indexes, and run the pipeline from scratch.")) {
      return;
    }
    setIsReanalysing(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/reanalyse`, {
        method: 'POST'
      });
      if (res.ok) {
        window.location.reload();
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

  const handleAskMentor = (rec: Recommendation) => {
    const promptText = `Explain why the recommendation "${rec.title}" is important for this repository, and walk me through refactoring the affected files: ${rec.affected_files.join(', ')}.`;
    router.push(`/repositories/${repoId}/mentor?q=${encodeURIComponent(promptText)}`);
  };

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    fetchFiles(newPage);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary text-textPrimary">
        <div className="text-center space-y-6 max-w-sm w-full px-4 animate-fade-in">
          <Loader2 className="w-10 h-10 animate-spin text-brand-500 mx-auto" />
          <div className="space-y-2">
            <div className="h-4 bg-slate-200 dark:bg-zinc-800 rounded w-3/4 mx-auto animate-pulse" />
            <div className="h-3 bg-slate-100 dark:bg-zinc-900 rounded w-1/2 mx-auto animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !repo) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-6 rounded-2xl shadow-2xl text-center space-y-6 animate-fade-in">
          <ShieldAlert className="w-10 h-10 text-rose-500 mx-auto animate-pulse" />
          <div className="space-y-2">
            <h2 className="text-xl font-bold text-textPrimary tracking-tight">Error Loading Repository</h2>
            <p className="text-sm text-textSecondary leading-relaxed">{error}</p>
          </div>
          <button onClick={() => router.push('/')} className="w-full py-2.5 px-4 bg-slate-100 dark:bg-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-700 border border-borderPrimary text-textPrimary rounded-xl text-sm font-semibold transition-all shadow-sm">
            Return Home
          </button>
        </div>
      </div>
    );
  }

  const isCompleted = repo.status === 'ready';
  const isFailed = repo.status === 'failed';
  const isProcessing = !isCompleted && !isFailed;

  // Calculate scores potentials (retrieved dynamically from backend)
  const totalEffort = recommendations.reduce((acc, r) => {
    const mins = r.effort.includes('hour') ? parseFloat(r.effort) * 60 : parseFloat(r.effort);
    return acc + (isNaN(mins) ? 0 : mins);
  }, 0);
  
  const totalEffortText = totalEffort >= 60 
    ? `${(totalEffort / 60).toFixed(1)} hours` 
    : `${totalEffort} mins`;

  // Sort files for lists
  const allKoFiles = repo.knowledge_summary?.knowledge_objects?.files || [];
  const largestFiles = [...allKoFiles].sort((a, b) => b.loc - a.loc).slice(0, 5);
  const complexFiles = [...allKoFiles].sort((a, b) => b.complexity - a.complexity).slice(0, 5);
  const smellyFiles = [...allKoFiles].sort((a, b) => b.smells_count - a.smells_count).slice(0, 5);

  const healthMeta = repo.knowledge_summary?.health_metadata;
  const healthBreakdown = healthMeta?.breakdown || {};
  const timing = repo.knowledge_summary?.timing_metadata || {};

  // Group recommendations by timeline
  const quickWins = recommendations.filter(r => r.priority === 'Low' || r.effort.includes('5') || r.effort.includes('15') || r.effort.includes('20'));
  const mediumEffort = recommendations.filter(r => r.priority === 'Medium' || r.effort.includes('30') || r.effort.includes('45'));
  const majorRefactor = recommendations.filter(r => r.priority === 'High' || r.priority === 'Critical' || r.effort.includes('hour'));

  // Calculate dynamic circular progress parameters
  const scoreRadius = 50;
  const scoreCircumference = 2 * Math.PI * scoreRadius;
  const scoreOffset = scoreCircumference - (repo.health_score / 100) * scoreCircumference;

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans selection:bg-brand-500/20 relative overflow-hidden transition-colors duration-300">
      {/* Background radial/linear glow elements */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-[100px] animate-slow-blob-1 -z-10" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-600/10 rounded-full blur-[120px] animate-slow-blob-2 -z-10" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-brand-500/5 rounded-full blur-[140px] animate-slow-blob-3 -z-10" />
      
      {/* Grid Overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(99,102,241,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(99,102,241,0.02)_1px,transparent_1px)] bg-[size:3.5rem_3.5rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] -z-10" />

      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="overview" 
      />

      <main className="w-full max-w-[1700px] mx-auto px-4 sm:px-6 lg:px-12 pt-[92px] pb-6 space-y-6 flex-grow">
        
        {/* PROCESSING CHECKLIST VIEW */}
        {isProcessing && (
          <div className="max-w-xl mx-auto bg-bgSecondary border border-borderPrimary rounded-2xl p-8 shadow-sm space-y-8 mt-10">
            <div className="text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mx-auto animate-pulse">
                <Loader2 className="w-6 h-6 animate-spin text-brand-500 dark:text-brand-400" />
              </div>
              <h2 className="text-lg font-bold text-textPrimary tracking-tight">
                Ingestion & Analysis Pipeline Active
              </h2>
              <p className="text-xs text-textSecondary leading-relaxed">
                We are scanning your files and building deterministic insights. This dashboard will automatically unlock once compilation finishes.
              </p>
            </div>
            
            <div className="bg-slate-100/50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 p-6 rounded-xl space-y-4 text-xs">
              {(() => {
                const stageList = [
                  { key: 'clone', label: 'Clone Repository' },
                  { key: 'parse', label: 'Scan Project Files' },
                  { key: 'tech_detect', label: 'Detect Technologies' },
                  { key: 'metrics', label: 'Calculate Code Metrics' },
                  { key: 'architecture', label: 'Analyze Architecture & Imports' },
                  { key: 'security', label: 'Perform Security Vulnerability Review' }
                ];
                
                return stageList.map((stg) => {
                  const info = repo.progress?.[stg.key] || { status: 'pending' };
                  const isCompleted = info.status === 'completed';
                  const isRunning = info.status === 'running';
                  const isFailed = info.status === 'failed';
                  
                  return (
                    <div key={stg.key} className="flex items-center justify-between py-2 border-b border-slate-150 dark:border-zinc-900/40 last:border-0">
                      <div className="flex items-center gap-3">
                        {isCompleted && <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />}
                        {isRunning && <Loader2 className="w-4 h-4 animate-spin text-brand-500 dark:text-brand-400 shrink-0" />}
                        {isFailed && <ShieldAlert className="w-4 h-4 text-rose-500 shrink-0" />}
                        {!isCompleted && !isRunning && !isFailed && <div className="w-4 h-4 rounded-full border border-slate-300 dark:border-zinc-800 shrink-0" />}
                        
                        <span className={`font-semibold ${isCompleted ? 'text-slate-700 dark:text-zinc-300' : isRunning ? 'text-textPrimary' : 'text-slate-600 dark:text-zinc-400'}`}>
                          {stg.label}
                        </span>
                      </div>
                      
                      {isCompleted && info.duration !== undefined && (
                        <span className="font-mono text-[10px] text-textSecondary">
                          {info.duration > 0 ? `${info.duration.toFixed(2)}s` : '<0.1s'}
                        </span>
                      )}
                      {isRunning && <span className="text-[9px] text-brand-500 dark:text-brand-400 font-bold uppercase tracking-widest animate-pulse">Running</span>}
                    </div>
                  );
                });
              })()}
            </div>
            
            <div className="text-center text-[10px] text-textSecondary font-mono">
              Pipeline Ref: {repo.id.slice(0, 8)} | Stage: {repo.current_stage || 'Queued'}
            </div>
          </div>
        )}

        {/* FAILED STATE VIEW */}
        {isFailed && (
          <div className="max-w-2xl mx-auto bg-bgSecondary border border-rose-500/20 rounded-2xl p-8 shadow-sm space-y-6 mt-10">
            <div className="flex items-center gap-4 pb-4 border-b border-borderPrimary">
              <ShieldAlert className="w-8 h-8 text-rose-500 animate-bounce" />
              <div>
                <h2 className="text-lg font-bold text-textPrimary tracking-tight">Pipeline Fault Detected</h2>
                <p className="text-xs text-textSecondary">The ingestion agent hit a configuration blocker.</p>
              </div>
            </div>
            <pre className="bg-slate-100 dark:bg-zinc-950/60 border border-rose-500/10 p-4 rounded-xl font-mono text-[11px] text-rose-650 dark:text-rose-300 overflow-x-auto whitespace-pre-wrap max-h-48">
              {repo.error_message || 'Uncaught exit status during Docker scan.'}
            </pre>
            <div className="flex gap-4">
              <button 
                onClick={() => router.push('/')} 
                className="flex-1 py-2.5 px-4 bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-800 text-textPrimary rounded-xl text-xs font-bold transition-all"
              >
                Back to Home
              </button>
              <button 
                disabled={isRetrying} 
                onClick={handleRetry} 
                className="flex-1 py-2.5 px-4 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-sm"
              >
                {isRetrying && <Loader2 className="w-4 h-4 animate-spin" />}
                Retry Analysis
              </button>
            </div>
          </div>
        )}

        {/* READY DASHBOARD OVERVIEW */}
        {isCompleted && (
          <div className="space-y-6 animate-fade-in duration-200">

            {/* Knowledge Base Indexing Warning Banner */}
            {repo.knowledge_status !== 'completed' && (
              <div className={`p-4 rounded-2xl border flex flex-col sm:flex-row justify-between sm:items-center gap-4 shadow-sm ${
                repo.knowledge_status === 'indexing' || repo.knowledge_status === 'pending'
                  ? 'bg-indigo-500/5 dark:bg-indigo-950/10 border-indigo-500/20 text-indigo-600 dark:text-indigo-300'
                  : 'bg-rose-500/5 dark:bg-rose-950/5 border-rose-500/20 text-rose-600 dark:text-rose-300'
              }`}>
                <div className="flex items-start gap-3">
                  {repo.knowledge_status === 'indexing' || repo.knowledge_status === 'pending' ? (
                    <Loader2 className="w-5 h-5 text-brand-500 dark:text-indigo-400 animate-spin shrink-0 mt-0.5" />
                  ) : (
                    <ShieldAlert className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
                  )}
                  <div className="text-xs space-y-0.5">
                    <span className="font-bold text-textPrimary block">
                      {repo.knowledge_status === 'indexing' || repo.knowledge_status === 'pending'
                        ? 'Knowledge Base Indexing Active'
                        : 'Knowledge Base Indexing Halted'}
                    </span>
                    <p className="text-textSecondary">
                      {repo.knowledge_status === 'indexing' || repo.knowledge_status === 'pending'
                        ? 'The vector index is compiling. AI Mentor features and deep architectural checks will unlock shortly.'
                        : `AI indexing stopped. Reason: ${repo.error_message || 'Cloud API offline or rate limit exceeded'}.`}
                    </p>
                  </div>
                </div>
                {(repo.knowledge_status === 'failed' || repo.knowledge_status === 'interrupted') && (
                  <button
                    disabled={isRetryingKb}
                    onClick={handleRetryKb}
                    className="py-1.5 px-3 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-lg transition-all flex items-center justify-center gap-1.5 shrink-0 shadow-sm"
                  >
                    {isRetryingKb && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    Retry Indexing
                  </button>
                )}
              </div>
            )}

            {/* ROW 1: 5 stat cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 sm:gap-6">
              <div className="bg-bgSecondary border border-borderPrimary p-6 rounded-2xl flex flex-col justify-between h-32 shadow-sm transition-all duration-300 hover:border-brand-500/20">
                <span className="section-header">Overall Grade</span>
                <div className="flex items-baseline gap-2">
                  <h3 className={`text-3xl font-bold ${repo.health_score >= 90 ? 'text-emerald-500 dark:text-emerald-400' : repo.health_score >= 80 ? 'text-sky-500' : repo.health_score >= 70 ? 'text-amber-500' : 'text-rose-500'}`}>
                    {repo.health_grade}
                  </h3>
                  <span className="text-xs font-mono text-textSecondary font-semibold">({repo.health_score}%)</span>
                </div>
                <span className="text-[10px] text-textSecondary font-mono block">Scoring Ledger Baseline</span>
              </div>

              <div className="bg-bgSecondary border border-borderPrimary p-6 rounded-2xl flex flex-col justify-between h-32 shadow-sm transition-all duration-300 hover:border-brand-500/20">
                <span className="section-header">Top Risk</span>
                <h3 className="text-sm font-semibold text-textPrimary truncate" title={recommendations[0]?.title || 'None'}>
                  {recommendations[0] ? recommendations[0].title : '🎉 Codebase Clean'}
                </h3>
                <span className={`text-[10px] font-bold font-mono block ${recommendations[0]?.priority === 'Critical' || recommendations[0]?.priority === 'High' ? 'text-rose-500' : 'text-emerald-500'}`}>
                  {recommendations[0] ? `${recommendations[0].priority} Priority` : 'Good practices detected'}
                </span>
              </div>

              <div className="bg-bgSecondary border border-borderPrimary p-6 rounded-2xl flex flex-col justify-between h-32 shadow-sm transition-all duration-300 hover:border-brand-500/20">
                <span className="section-header">Tech Stack</span>
                <h3 className="text-sm font-semibold text-textPrimary truncate" title={repo.tech_stack?.frameworks?.join(', ') || ''}>
                  {repo.tech_stack?.frameworks?.length ? repo.tech_stack.frameworks.join(', ') : 'Vanilla Codebase'}
                </h3>
                <span className="text-[10px] text-textSecondary font-mono block">
                  Manager: {repo.tech_stack?.package_manager || 'None'}
                </span>
              </div>

              <div className="bg-bgSecondary border border-borderPrimary p-6 rounded-2xl flex flex-col justify-between h-32 shadow-sm transition-all duration-300 hover:border-brand-500/20">
                <span className="section-header">Repository Size</span>
                <h3 className="text-2xl font-bold text-accent-primary font-mono">
                  {repo.total_lines_of_code.toLocaleString()} LOC
                </h3>
                <span className="text-[10px] text-textSecondary font-mono block">
                  {repo.total_files} Files | {repo.total_smells} Smells
                </span>
              </div>

              <div className="bg-bgSecondary border border-borderPrimary p-6 rounded-2xl flex flex-col justify-between h-32 shadow-sm transition-all duration-300 hover:border-brand-500/20">
                <span className="section-header">Refactor Effort</span>
                <h3 className="text-2xl font-bold text-accent-primary font-mono">
                  {totalEffortText}
                </h3>
                <span className="text-[10px] text-textSecondary font-mono block">
                  {recommendations.length} Actionable Tasks
                </span>
              </div>
            </div>

            {/* ROW 2: Health Improvement Roadmap banner */}
            <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-brand-500/5 rounded-full blur-2xl pointer-events-none -z-10" />
              <div className="flex flex-col md:flex-row justify-between items-center gap-6 relative">
                <div className="space-y-2 text-center md:text-left">
                  <span className="text-[10px] bg-brand-500/10 text-brand-600 dark:text-brand-300 border border-brand-500/20 px-2 py-0.5 rounded-lg font-bold tracking-wider uppercase">Repository Journey</span>
                  <h2 className="text-xl font-bold text-textPrimary tracking-tight">Health Improvement Roadmap</h2>
                  <p className="text-xs text-textSecondary max-w-md">Complete these prioritized refactoring tasks to clean structural flaws, eliminate smells, and secure variables.</p>
                </div>

                {/* Journey Steps Progress */}
                <div className="flex items-center gap-4 bg-slate-100/50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 p-4 rounded-xl shrink-0 w-full md:w-auto overflow-x-auto">
                  <div className="text-center shrink-0 animate-fade-in">
                    <span className="text-[9px] text-textSecondary uppercase font-bold block">Current</span>
                    <span className="text-xl font-black text-textPrimary">{repo.health_score}</span>
                  </div>
                  <span className="text-slate-400 dark:text-zinc-650 font-mono">→</span>
                  <div className="text-center shrink-0">
                    <span className="text-[9px] text-brand-600 dark:text-brand-400 uppercase font-bold block">Potential</span>
                    <span className="text-xl font-black text-brand-500 dark:text-brand-400">{potentialScore}</span>
                  </div>
                  <span className="text-slate-400 dark:text-zinc-650 font-mono">→</span>
                  <div className="text-center shrink-0">
                    <span className="text-[9px] text-textSecondary uppercase font-bold block">Estimated work</span>
                    <span className="text-sm font-black text-textPrimary block mt-1">{totalEffortText}</span>
                  </div>
                  <span className="text-slate-400 dark:text-zinc-650 font-mono">→</span>
                  <div className="text-center shrink-0 bg-brand-500/5 border border-brand-500/20 px-3 py-1 rounded-lg">
                    <span className="text-[9px] text-brand-600 dark:text-brand-400 uppercase font-bold block">Tasks</span>
                    <span className="text-sm font-black text-textPrimary">{recommendations.length}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* ROW 3: Two-column layout (60/40 split) */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
              
              {/* LEFT Column (60% width): Codebase Health radial gauge + Scoring Ledger */}
              <div className="lg:col-span-3 space-y-6">
                
                {/* SVG Radial Gauge Card */}
                <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 text-center space-y-6 shadow-sm relative overflow-hidden">
                  <h3 className="section-header text-left border-b border-borderPrimary pb-2">Codebase Health</h3>
                  
                  <div className="relative flex justify-center items-center py-4">
                    <svg className="w-36 h-36 transform -rotate-90" viewBox="0 0 144 144">
                      {/* Grey background circle */}
                      <circle
                         cx="72"
                         cy="72"
                         r={scoreRadius}
                         className="stroke-slate-200 dark:stroke-zinc-900"
                         strokeWidth="10"
                         fill="transparent"
                       />
                      {/* Colored progress circle */}
                      <circle
                        cx="72"
                        cy="72"
                        r={scoreRadius}
                        className={`transition-all duration-1000 ${
                          repo.health_score >= 90 ? 'stroke-emerald-500' : repo.health_score >= 80 ? 'stroke-sky-500' : repo.health_score >= 70 ? 'stroke-amber-500' : 'stroke-rose-500'
                        }`}
                        strokeWidth="10"
                        fill="transparent"
                        strokeDasharray={scoreCircumference}
                        strokeDashoffset={scoreOffset}
                        strokeLinecap="round"
                      />
                    </svg>
                    {/* Centered score text */}
                    <div className="absolute text-center">
                      <h4 className="text-3xl font-black text-textPrimary tracking-tight leading-none">{repo.health_score}</h4>
                      <span className="text-[9px] text-textSecondary uppercase font-bold tracking-wider mt-1 block">Grade {repo.health_grade}</span>
                    </div>
                  </div>

                  <div className="flex justify-between items-center text-xs text-textSecondary pt-2 border-t border-borderPrimary">
                    <span>Potential Improvement</span>
                    <span className="font-bold text-accent-primary">+{potentialScore - repo.health_score} Points</span>
                  </div>
                </div>

                {/* Scoring Ledger */}
                <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-4 shadow-sm">
                  <div className="flex justify-between items-center pb-2 border-b border-borderPrimary">
                    <h3 className="section-header flex items-center gap-1.5"><Shield className="w-3.5 h-3.5 text-accent-primary" /> Scoring Ledger</h3>
                    <button 
                      onClick={() => setIsLedgerExpanded(!isLedgerExpanded)}
                      className="text-[9px] text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 px-2 py-0.5 rounded-lg transition-all"
                    >
                      {isLedgerExpanded ? 'Hide' : 'Expand Details'}
                    </button>
                  </div>

                  <div className="space-y-3.5">
                    {Object.entries(healthBreakdown).map(([key, val]: [string, any]) => (
                      <div key={key} className="space-y-1 text-xs">
                        <div className="flex justify-between text-textSecondary font-medium">
                          <span className="capitalize">{key}</span>
                          <span className="font-semibold text-textPrimary">{val.score}/{val.max}</span>
                        </div>
                        <div className="w-full bg-slate-200 dark:bg-zinc-900 h-2 rounded-full overflow-hidden">
                          <div className="bg-accent-primary h-full transition-all duration-500 rounded-full" style={{ width: `${(val.score / val.max) * 100}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>

                  {isLedgerExpanded && repo.knowledge_summary?.health_metadata?.details && (
                    <div className="pt-4 border-t border-borderPrimary space-y-2 animate-fade-in">
                      <span className="text-[9px] text-textSecondary uppercase font-bold block">Score Adjustments Ledger</span>
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {repo.knowledge_summary.health_metadata.details.map((detail: any, idx: number) => {
                          const isDeduction = detail.type === 'deduction';
                          return (
                            <div key={idx} className="p-2.5 bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 rounded-xl text-[10px] space-y-1">
                              <div className="flex justify-between font-bold">
                                <span className={isDeduction ? 'text-rose-600 dark:text-rose-450' : 'text-emerald-600 dark:text-emerald-450'}>{detail.rule}</span>
                                <span className="font-mono">{isDeduction ? detail.impact : `+${detail.impact}`}</span>
                              </div>
                              <p className="text-textSecondary leading-normal">{detail.reason}</p>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

              </div>

              {/* RIGHT Column (40% width): Onboarding Path + Health Forecast */}
              <div className="lg:col-span-2 space-y-6">
                
                {/* Insights Onboarding timeline */}
                <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-4 shadow-sm">
                  <h3 className="section-header flex items-center gap-1.5">
                    <Activity className="w-4 h-4 text-accent-primary" /> Repository Insights Onboarding Path
                  </h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1 text-center">
                    {[
                      { label: 'Overview', done: true },
                      { label: 'Files', done: repo.total_files > 0 },
                      { label: 'Languages', done: !!repo.language_breakdown && Object.keys(repo.language_breakdown).length > 0 },
                      { label: 'Architecture', done: repo.status === 'ready' },
                      { label: 'Security', done: repo.status === 'ready' },
                      { label: 'Code Smells', done: repo.total_smells > 0 },
                      { label: 'Recommendations', done: recommendations.length > 0 },
                      { label: 'Roadmap', done: repo.knowledge_status === 'completed' }
                    ].map((step, idx) => (
                      <div key={idx} className="p-2.5 bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 rounded-xl relative flex flex-col items-center justify-between gap-1.5 shadow-inner">
                        <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold ${
                          step.done ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-450 border border-emerald-500/30' : 'bg-slate-250 dark:bg-zinc-900 text-slate-400 dark:text-zinc-500 border border-slate-300 dark:border-zinc-800'
                        }`}>
                          {idx + 1}
                        </span>
                        <span className="text-[9px] font-bold uppercase tracking-tight text-textSecondary">{step.label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Health Forecast */}
                <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-4 shadow-sm">
                  <h3 className="section-header flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-accent-primary animate-pulse" /> Repository Health Forecast
                  </h3>
                  
                  <div className="relative p-4 bg-slate-50 dark:bg-zinc-950/60 border border-slate-200 dark:border-zinc-900 rounded-xl space-y-4 shadow-inner">
                    <div className="flex flex-col sm:flex-row justify-between items-center gap-4 text-xs font-mono">
                      {forecast.length > 0 ? (
                        forecast.map((fc, idx) => (
                          <React.Fragment key={idx}>
                            <div className="flex-1 flex flex-col items-center gap-1 text-center w-full">
                              <span className="text-[9px] text-textSecondary uppercase font-semibold">{fc.stage}</span>
                              <div className="flex items-baseline gap-1 mt-0.5">
                                <span className={`text-lg font-black ${
                                  idx === 0 ? 'text-slate-400 dark:text-zinc-500' : idx === forecast.length - 1 ? 'text-accent-primary' : 'text-emerald-500 dark:text-emerald-450'
                                }`}>
                                  {fc.score}
                                </span>
                                <span className="text-[9px] text-slate-400 dark:text-zinc-650">/100</span>
                              </div>
                            </div>
                            {idx < forecast.length - 1 && (
                              <>
                                <ChevronRight className="hidden sm:block w-4 h-4 text-slate-300 dark:text-zinc-800 shrink-0" />
                                <ChevronDown className="sm:hidden w-4 h-4 text-slate-300 dark:text-zinc-800 shrink-0" />
                              </>
                            )}
                          </React.Fragment>
                        ))
                      ) : (
                        <div className="text-center py-4 text-textSecondary text-xs w-full">Forecast progression data compiling...</div>
                      )}
                    </div>
                    
                    {forecast.length > 0 && forecast[forecast.length - 1].reason && (
                      <div className="text-[10px] text-textSecondary bg-slate-100 dark:bg-zinc-950 p-2.5 rounded-lg border border-slate-200 dark:border-zinc-900 font-medium">
                        <AlertCircle className="w-3.5 h-3.5 inline text-slate-400 dark:text-zinc-500 mr-1.5 -mt-0.5 animate-bounce" />
                        {forecast[forecast.length - 1].reason}
                      </div>
                    )}
                  </div>
                </div>

              </div>

            </div>

            {/* ROW 4: Refactoring Timeline Tasks + Engineering Summary Description */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
              
              {/* Refactoring Timeline Tasks card */}
              <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-4 shadow-sm flex flex-col justify-between">
                <div className="flex justify-between items-center text-xs pb-2 border-b border-borderPrimary">
                  <span className="section-header">Refactoring Timeline Tasks</span>
                  <span className="font-mono text-textSecondary">{recommendations.length} Actionable Tasks</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs pt-2">
                  <div className="p-3.5 bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 rounded-xl flex items-center justify-between shadow-inner">
                    <span className="text-emerald-600 dark:text-emerald-400 uppercase font-bold text-[10px] tracking-wider flex items-center gap-1.5">🟢 Quick Wins</span>
                    <span className="font-bold text-textPrimary font-mono bg-slate-250 dark:bg-zinc-900 px-2 py-0.5 rounded-lg">{quickWins.length}</span>
                  </div>
                  <div className="p-3.5 bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 rounded-xl flex items-center justify-between shadow-inner">
                    <span className="text-yellow-600 dark:text-yellow-500 uppercase font-bold text-[10px] tracking-wider flex items-center gap-1.5">🟡 Medium Effort</span>
                    <span className="font-bold text-textPrimary font-mono bg-slate-250 dark:bg-zinc-900 px-2 py-0.5 rounded-lg">{mediumEffort.length}</span>
                  </div>
                  <div className="p-3.5 bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 rounded-xl flex items-center justify-between shadow-inner">
                    <span className="text-rose-600 dark:text-red-400 uppercase font-bold text-[10px] tracking-wider flex items-center gap-1.5">🔴 Major Refactoring</span>
                    <span className="font-bold text-textPrimary font-mono bg-slate-250 dark:bg-zinc-900 px-2 py-0.5 rounded-lg">{majorRefactor.length}</span>
                  </div>
                </div>
              </div>

              {/* Engineering Summary Description card */}
              <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-3 shadow-sm flex flex-col justify-between">
                <div className="pb-2 border-b border-borderPrimary">
                  <h3 className="section-header flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-accent-primary" /> Engineering Summary Description
                  </h3>
                </div>
                <p className="text-textSecondary leading-relaxed text-xs pt-1">
                  {repo.knowledge_summary?.summary_description || 'Analysis complete. Run assessment or talk to the AI mentor to explore refactoring patterns.'}
                </p>
              </div>

            </div>

            {/* ROW 5: Actionable Task Planner cards */}
            <div className="space-y-4">
              <h3 className="section-header flex items-center gap-1.5">
                <CheckSquare className="w-4 h-4 text-accent-primary" /> Actionable Task Planner
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {(isPlannerExpanded ? recommendations : recommendations.slice(0, 3)).map(rec => {
                  const priBg = rec.priority === 'Critical' ? 'bg-red-500/10 border-red-500/20 text-red-500' 
                    : rec.priority === 'High' ? 'bg-orange-500/10 border-orange-500/20 text-orange-500' 
                    : rec.priority === 'Medium' ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-500' 
                    : 'bg-blue-500/10 border-blue-500/20 text-blue-500';

                  return (
                    <div 
                      key={rec.id} 
                      onClick={() => setExpandedRecId(rec.id)}
                      className="bg-bgSecondary border border-cardBorder hover:border-brand-500/40 cursor-pointer rounded-2xl flex flex-col justify-between p-6 transition-all duration-300 h-[340px] relative group premium-glass-card shadow-sm"
                    >
                      <div className="space-y-3.5">
                        {/* Badges */}
                        <div className="flex justify-between items-center text-[10px]">
                          <span className={`px-2 py-0.5 rounded font-bold border uppercase tracking-wider ${priBg}`}>
                            {rec.priority === 'Critical' ? '🔴 Critical' : rec.priority === 'High' ? '🟠 High' : rec.priority === 'Medium' ? '🟡 Medium' : '🔵 Low'}
                          </span>
                          <span className="text-textSecondary font-mono font-medium">{rec.category}</span>
                        </div>

                        {/* Title & Why */}
                        <div className="space-y-1.5">
                          <h4 className="card-title line-clamp-2">{rec.title}</h4>
                          <p className="text-xs text-textSecondary leading-relaxed line-clamp-3">{rec.why_it_matters}</p>
                        </div>

                        {/* Affected Files & Effort */}
                        <div className="flex items-center justify-between text-[10px] text-textSecondary font-mono pt-1">
                          <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5 text-slate-400 dark:text-zinc-500" /> {rec.effort}</span>
                          <span className="bg-slate-100 dark:bg-zinc-900 border border-cardBorder px-2 py-0.5 rounded text-[9px] font-bold">
                            {rec.affected_files.length} Affected {rec.affected_files.length === 1 ? 'File' : 'Files'}
                          </span>
                        </div>
                      </div>

                      {/* Footer Stats & Actions */}
                      <div className="border-t border-cardBorder pt-4 flex justify-between items-center mt-auto">
                        <div className="flex gap-3 text-[10px] font-mono">
                          <span className="text-textSecondary">Health: <strong className="text-accent-primary font-bold">+{rec.health_improvement}</strong></span>
                          {rec.security_improvement > 0 && <span className="text-rose-500 font-bold">+{rec.security_improvement} Sec</span>}
                        </div>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleAskMentor(rec); }}
                          className="px-2.5 py-1.5 rounded-lg border border-brand-500/20 bg-brand-500/5 hover:bg-brand-500/10 text-brand-600 dark:text-brand-400 text-[10px] font-bold flex items-center gap-1 transition-all"
                        >
                          <Sparkles className="w-3 h-3 text-brand-500 dark:text-brand-400 animate-pulse" /> Ask AI
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              {recommendations.length > 3 && (
                <div className="flex justify-center pt-2">
                  <button
                    onClick={() => setIsPlannerExpanded(!isPlannerExpanded)}
                    className="px-4 py-2 border border-slate-200 dark:border-zinc-800 bg-slate-100/80 dark:bg-[#090a12]/80 hover:bg-slate-200 dark:hover:bg-[#0c0f1e] hover:border-slate-350 dark:hover:border-zinc-700 text-textSecondary dark:text-zinc-300 hover:text-textPrimary hover:dark:text-white rounded-xl text-xs font-semibold flex items-center gap-2 transition-all shadow-md active:scale-98"
                  >
                    {isPlannerExpanded ? (
                      <>
                        Show Fewer Recommendations
                        <ChevronUp className="w-4 h-4 text-zinc-500" />
                      </>
                    ) : (
                      <>
                        View All Recommendations ({recommendations.length})
                        <ChevronDown className="w-4 h-4 text-zinc-500" />
                      </>
                    )}
                  </button>
                </div>
              )}

              {recommendations.length === 0 && (
                <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-8 text-center space-y-2">
                  <p className="text-sm font-bold text-textPrimary">🎉 Codebase Clean!</p>
                  <p className="text-xs text-textSecondary">No score deductions or critical refactoring points were found.</p>
                </div>
              )}
            </div>

            {/* ROW 6: Two-column layout (60/40 split) */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
              
              {/* LEFT Column (60% width): File Explorer */}
              <div className="lg:col-span-3 space-y-6">
                
                {/* File Explorer Table */}
                <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-4 shadow-sm">
                  <div className="flex justify-between items-center pb-2 border-b border-borderPrimary">
                    <h3 className="section-header flex items-center gap-1.5"><Terminal className="w-4 h-4 text-accent-primary" /> File Explorer</h3>
                    {filesData && <span className="text-[10px] text-textSecondary font-mono">Showing {currentPage * limit + 1}-{Math.min((currentPage + 1) * limit, filesData.total)} of {filesData.total}</span>}
                  </div>
                  
                  <div className="overflow-x-auto text-xs">
                    <table className="w-full min-w-[600px] text-left border-collapse">
                      <thead>
                        <tr className="border-b border-borderPrimary text-textSecondary font-mono">
                          <th className="py-2.5 px-2 font-semibold">Path</th>
                          <th className="py-2.5 px-2 font-semibold text-right">LOC</th>
                          <th className="py-2.5 px-2 font-semibold text-right">Complexity</th>
                          <th className="py-2.5 px-2 font-semibold text-right">Smells</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200/50 dark:divide-zinc-900/40 text-textSecondary">
                        {filesData?.files?.map(file => (
                          <tr 
                            key={file.id} 
                            className="hover:bg-slate-100/50 dark:hover:bg-zinc-900/20 group cursor-pointer" 
                            onClick={() => router.push(`/repositories/${repoId}/files/${file.id}`)}
                          >
                            <td className="py-2.5 px-2 font-mono text-textPrimary group-hover:text-brand-600 dark:group-hover:text-brand-400 break-all max-w-sm transition-colors">{file.path}</td>
                            <td className="py-2.5 px-2 text-right font-mono">{file.lines_of_code}</td>
                            <td className="py-2.5 px-2 text-right font-mono">{file.complexity}</td>
                            <td className="py-2.5 px-2 text-right font-mono text-rose-500">{file.code_smells_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {filesData && filesData.total > limit && (
                    <div className="flex justify-between items-center pt-4 border-t border-borderPrimary/50">
                      <button onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 0}
                        className="flex items-center gap-1 py-1 px-2.5 rounded-lg border border-slate-200 dark:border-zinc-800 bg-slate-100 dark:bg-zinc-900 hover:bg-slate-200 dark:hover:bg-zinc-800 text-textSecondary disabled:opacity-40 disabled:cursor-not-allowed text-[11px] transition-all font-semibold shadow-sm">
                        <ChevronLeft className="w-3.5 h-3.5" /> Prev
                      </button>
                      <span className="text-[10px] text-textSecondary font-mono">Page {currentPage + 1} of {Math.ceil(filesData.total / limit)}</span>
                      <button onClick={() => handlePageChange(currentPage + 1)} disabled={(currentPage + 1) * limit >= filesData.total}
                        className="flex items-center gap-1 py-1 px-2.5 rounded-lg border border-slate-200 dark:border-zinc-800 bg-slate-100 dark:bg-zinc-900 hover:bg-slate-200 dark:hover:bg-zinc-800 text-textSecondary disabled:opacity-40 disabled:cursor-not-allowed text-[11px] transition-all font-semibold shadow-sm">
                        Next <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>

              </div>

              {/* RIGHT Column (40% width): Language Breakdown + Code Rankings Explorer stacked vertically */}
              <div className="lg:col-span-2 space-y-6">
                
                {/* Language dashboard stack */}
                <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-4 shadow-sm">
                  <h3 className="section-header flex items-center gap-1.5"><Sparkles className="w-4 h-4 text-accent-primary" /> Language Breakdown</h3>
                  
                  <div className="w-full bg-slate-200 dark:bg-zinc-900 rounded-full h-3 flex overflow-hidden border border-slate-300 dark:border-zinc-950">
                    {repo.language_breakdown && Object.entries(repo.language_breakdown).map(([lang, pct], i) => (
                      <div key={lang} style={{ width: `${pct}%` }} className={LANG_COLORS[i % LANG_COLORS.length]} title={`${lang}: ${pct}%`} />
                    ))}
                  </div>
                  
                  <div className="space-y-2 pt-2 text-xs">
                    {repo.language_breakdown && Object.entries(repo.language_breakdown).map(([lang, pct], i) => (
                      <div key={lang} className={`flex items-center justify-between p-2 rounded-xl border ${LANG_TEXT_COLORS[i % LANG_TEXT_COLORS.length]}`}>
                        <div className="flex items-center gap-2">
                          <span className={`w-2.5 h-2.5 rounded-full ${LANG_COLORS[i % LANG_COLORS.length]}`} />
                          <span className="font-bold">{lang}</span>
                        </div>
                        <span className="font-mono font-semibold">{pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Top 5 Code rankings cards */}
                <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-6 shadow-sm text-xs">
                  <h3 className="section-header flex items-center gap-1.5"><Activity className="w-4 h-4 text-accent-primary" /> Code Rankings Explorer</h3>
                  
                  <div className="space-y-4">
                    {/* Largest */}
                    <div className="space-y-2">
                      <span className="text-[10px] text-textSecondary uppercase font-bold block border-b border-borderPrimary pb-1.5">Top 5 Largest (LOC)</span>
                      <div className="space-y-1.5">
                        {largestFiles.map((f, i) => (
                          <div key={i} className="flex justify-between items-center p-2 bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 rounded-lg">
                            <span className="truncate max-w-[150px] font-mono text-[10px] text-textPrimary" title={f.path}>{f.path.split('/').pop()}</span>
                            <span className="font-bold text-textSecondary font-mono">{f.loc}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Complex */}
                    <div className="space-y-2">
                      <span className="text-[10px] text-textSecondary uppercase font-bold block border-b border-borderPrimary pb-1.5">Top 5 Complex (Complexity)</span>
                      <div className="space-y-1.5">
                        {complexFiles.map((f, i) => (
                          <div key={i} className="flex justify-between items-center p-2 bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 rounded-lg">
                            <span className="truncate max-w-[150px] font-mono text-[10px] text-textPrimary" title={f.path}>{f.path.split('/').pop()}</span>
                            <span className="font-bold text-indigo-650 dark:text-indigo-400 font-mono">{f.complexity}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

              </div>

            </div>

            {/* ROW 7: Timing timelines performance analytics */}
            {timing && Object.keys(timing).length > 0 && (
              <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-4 shadow-sm">
                <h3 className="section-header flex items-center gap-1.5"><Clock className="w-4 h-4 text-accent-primary" /> Ingestion Performance Timeline</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 text-center">
                  {Object.entries(timing).filter(([k]) => k !== 'total').map(([stage, val]: [string, any]) => (
                    <div key={stage} className="p-3 bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 rounded-xl space-y-1 text-xs shadow-inner">
                      <span className="text-[9px] text-textSecondary uppercase font-semibold block truncate" title={stage}>{stage}</span>
                      <span className="font-bold text-textPrimary font-mono">{val}s</span>
                    </div>
                  ))}
                  <div className="p-3 bg-brand-500/5 border border-brand-500/15 rounded-xl space-y-1 text-xs col-span-2 sm:col-span-1 shadow-inner">
                    <span className="text-[9px] text-brand-600 dark:text-brand-300 uppercase font-bold block">Total Ingest</span>
                    <span className="font-bold text-textPrimary font-mono">{timing.total || 0}s</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

      {/* Task Details Drawer Overlay (Part 2) */}
      {expandedRecId && (() => {
        const selectedRec = recommendations.find(r => r.id === expandedRecId);
        if (!selectedRec) return null;
        
        const priBg = selectedRec.priority === 'Critical' ? 'bg-red-500/10 border-red-500/20 text-red-500' 
          : selectedRec.priority === 'High' ? 'bg-orange-500/10 border-orange-500/20 text-orange-500' 
          : selectedRec.priority === 'Medium' ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-500' 
          : 'bg-blue-500/10 border-blue-500/20 text-blue-500';

        return (
          <div className="fixed inset-0 z-50 flex justify-end animate-fade-in">
            {/* Backdrop */}
            <div 
              className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity" 
              onClick={() => setExpandedRecId(null)}
            />
            
            {/* Drawer Panel */}
            <div className="relative w-full max-w-lg bg-bgSecondary border-l border-borderPrimary shadow-2xl flex flex-col h-full z-10 animate-slide-in overflow-hidden">
              {/* Header */}
              <div className="p-6 border-b border-borderPrimary flex items-center justify-between bg-slate-50/50 dark:bg-zinc-950/20">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold border uppercase tracking-wider ${priBg}`}>
                      {selectedRec.priority === 'Critical' ? '🔴 Critical' : selectedRec.priority === 'High' ? '🟠 High' : selectedRec.priority === 'Medium' ? '🟡 Medium' : '🔵 Low'}
                    </span>
                    <span className="text-[10px] text-textSecondary font-mono font-medium">{selectedRec.category}</span>
                  </div>
                  <h3 className="text-base font-bold text-textPrimary leading-snug">{selectedRec.title}</h3>
                </div>
                <button 
                  onClick={() => setExpandedRecId(null)}
                  className="p-1.5 rounded-lg border border-borderPrimary hover:bg-slate-100 dark:hover:bg-zinc-900 text-textSecondary transition-all"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>

              {/* Scrollable Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                
                {/* Why it matters */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-textPrimary uppercase tracking-wider">Why this is a problem</h4>
                  <p className="text-xs text-textSecondary leading-relaxed bg-slate-50 dark:bg-zinc-950/40 p-3 rounded-xl border border-borderPrimary/40">
                    {selectedRec.why_it_matters}
                  </p>
                </div>

                {/* Steps / How to fix */}
                {selectedRec.steps && selectedRec.steps.length > 0 && (
                  <div className="space-y-2.5">
                    <h4 className="text-xs font-bold text-textPrimary uppercase tracking-wider">How to fix it</h4>
                    <ol className="space-y-2 text-xs text-textSecondary list-decimal pl-4">
                      {selectedRec.steps.map((step, idx) => (
                        <li key={idx} className="leading-relaxed pl-1">{step}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* Expected Improvement */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-brand-500/5 border border-brand-500/20 rounded-xl space-y-1">
                    <span className="text-[9px] text-brand-600 dark:text-brand-350 uppercase font-bold tracking-wider block">Expected Health Gain</span>
                    <span className="text-base font-black text-textPrimary font-mono">+{selectedRec.health_improvement} Points</span>
                  </div>
                  <div className="p-3 bg-slate-50 dark:bg-zinc-950/40 border border-borderPrimary rounded-xl space-y-1">
                    <span className="text-[9px] text-textSecondary uppercase font-bold tracking-wider block">Estimated Effort</span>
                    <span className="text-base font-black text-textPrimary font-mono flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-slate-400 dark:text-zinc-500" />
                      {selectedRec.effort}
                    </span>
                  </div>
                </div>

                {/* Affected Files */}
                {selectedRec.affected_files && selectedRec.affected_files.length > 0 && (
                  <div className="space-y-2.5">
                    <h4 className="text-xs font-bold text-textPrimary uppercase tracking-wider">Affected Files</h4>
                    <div className="space-y-2">
                      {selectedRec.affected_files.map((file, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2.5 bg-slate-50 dark:bg-zinc-950/40 border border-borderPrimary rounded-xl font-mono text-[10px] text-textPrimary">
                          <span className="truncate flex items-center gap-2">
                            <FileCode className="w-4 h-4 text-indigo-500 shrink-0" />
                            {file}
                          </span>
                          <span className="text-textSecondary text-[9px] bg-slate-100 dark:bg-zinc-900 border border-borderPrimary px-1.5 py-0.5 rounded">
                            {file.split('.').pop()?.toUpperCase()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Related Issues / Lines */}
                {selectedRec.related_issues && selectedRec.related_issues.length > 0 && (
                  <div className="space-y-2.5">
                    <h4 className="text-xs font-bold text-textPrimary uppercase tracking-wider">Vulnerabilities & Smell Detections</h4>
                    <div className="space-y-2">
                      {selectedRec.related_issues.map((issue, idx) => (
                        <div key={idx} className="p-2.5 bg-slate-50 dark:bg-zinc-950/40 border border-borderPrimary rounded-xl text-[10px] space-y-1.5">
                          <div className="flex justify-between font-bold">
                            <span className="text-textPrimary flex items-center gap-1">
                              <AlertCircle className="w-3.5 h-3.5 text-rose-500" />
                              {issue.type}
                            </span>
                            {issue.line_number && <span className="font-mono text-textSecondary text-[9px]">Line {issue.line_number}</span>}
                          </div>
                          <p className="text-textSecondary leading-normal font-mono truncate">{issue.file_path}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Code Snippets */}
                {(selectedRec.before_code || selectedRec.after_code) && (
                  <div className="space-y-4">
                    {selectedRec.before_code && (
                      <div className="space-y-2">
                        <span className="text-[10px] text-rose-600 dark:text-rose-400 font-bold block uppercase tracking-wider">Before Refactoring</span>
                        <pre className="bg-rose-500/5 border border-rose-500/20 p-3 rounded-xl font-mono text-[10px] text-rose-700 dark:text-rose-350 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-48">
                          {selectedRec.before_code}
                        </pre>
                      </div>
                    )}
                    {selectedRec.after_code && (
                      <div className="space-y-2">
                        <span className="text-[10px] text-emerald-600 dark:text-emerald-450 font-bold block uppercase tracking-wider">Proposed Clean Code</span>
                        <pre className="bg-emerald-500/5 border border-emerald-500/20 p-3 rounded-xl font-mono text-[10px] text-emerald-700 dark:text-emerald-350 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-48">
                          {selectedRec.after_code}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Footer Panel Actions */}
              <div className="p-4 border-t border-borderPrimary bg-slate-50 dark:bg-zinc-950/20 flex gap-3">
                <button
                  onClick={() => setExpandedRecId(null)}
                  className="flex-1 py-2 px-4 bg-slate-100 dark:bg-zinc-900 border border-borderPrimary hover:bg-slate-200 dark:hover:bg-zinc-800 text-textPrimary rounded-xl text-xs font-bold transition-all text-center"
                >
                  Close Panel
                </button>
                <button
                  onClick={() => { setExpandedRecId(null); handleAskMentor(selectedRec); }}
                  className="flex-1 py-2 px-4 bg-brand-500 hover:bg-brand-600 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 shadow-sm"
                >
                  <Sparkles className="w-3.5 h-3.5" /> Explain with AI Mentor
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      </main>

      <footer className="w-full text-center py-6 text-xs text-slate-500 dark:text-zinc-500 border-t border-slate-200 dark:border-zinc-900/40 mt-8 font-mono">
        Repository Mentor AI &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
}
