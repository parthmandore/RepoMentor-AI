'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  Github, Terminal, Sparkles, CheckCircle, ArrowRight,
  Loader2, Clock, Shield, ChevronRight, Activity, 
  Layers, Copy, BookOpen, AlertTriangle, ShieldAlert,
  ChevronDown, ChevronUp, Wrench, Check, ArrowUpRight, Flame,
  FileCode, Zap
} from 'lucide-react';

import Header from '../../Header';
import { PageLayoutSkeleton } from '../../components/Skeletons';

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
  error_message: string | null;
  created_at: string;
  knowledge_summary?: {
    summary_description?: string;
    timing_metadata?: Record<string, number>;
    analysis_budget?: {
      budget_seconds: number;
      elapsed_seconds: number;
      total_files: number;
      eligible_files: number;
      unique_eligible_files: number;
      analyzed_unique_files: number;
      analyzed_total_files: number;
      is_partial: boolean;
      status_display: string;
    };
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

export default function RepositoryOverview({ params }: { params: { id: string } }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  // API states
  const [repo, setRepo] = useState<RepositoryData | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [potentialScore, setPotentialScore] = useState<number>(100);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRetrying, setIsRetrying] = useState(false);
  const [isRetryingKb, setIsRetryingKb] = useState(false);
  const [expandedRecId, setExpandedRecId] = useState<string | null>(null);
  const [isLedgerExpanded, setIsLedgerExpanded] = useState(false);

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
        setPotentialScore(data.potential_score || 100);
      }
    } catch (err) {
      console.error('Error fetching recommendations:', err);
    }
  }, [apiUrl, repoId]);

  const handleRetryKb = useCallback(async () => {
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
      console.error('KB retry failed:', err.message);
    } finally {
      setIsRetryingKb(false);
    }
  }, [apiUrl, repoId, fetchRepository]);

  useEffect(() => {
    fetchRepository().then((status) => {
      if (status === 'ready') {
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
          fetchRecommendations();
        }
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [repoId, fetchRepository, fetchRecommendations, repo?.knowledge_status]);

  // Handle ?reindex=true query parameter from AI Mentor or navigation
  useEffect(() => {
    if (searchParams?.get('reindex') === 'true' && repo && repo.status === 'ready' && repo.knowledge_status !== 'indexing' && !isRetryingKb) {
      handleRetryKb();
    }
  }, [searchParams, repo?.status, repo?.knowledge_status, isRetryingKb, handleRetryKb]);

  const handleAskMentor = (rec: Recommendation) => {
    const promptText = `Explain why the recommendation "${rec.title}" is important for this repository, and walk me through refactoring the affected files: ${rec.affected_files.join(', ')}.`;
    router.push(`/repositories/${repoId}/mentor?q=${encodeURIComponent(promptText)}`);
  };

  if (isLoading) {
    return <PageLayoutSkeleton title="Compiling Field Report..." />;
  }

  if (error || !repo) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4 font-sans">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-8 rounded-lg shadow-report text-center space-y-5">
          <ShieldAlert className="w-10 h-10 text-bad mx-auto" />
          <div className="space-y-2">
            <h2 className="font-serif text-2xl font-bold text-textPrimary tracking-tight">Inspection Interrupted</h2>
            <p className="text-xs text-textSecondary font-mono">{error}</p>
          </div>
          <button 
            onClick={() => router.push('/')} 
            className="w-full py-2.5 px-4 bg-bgTertiary hover:bg-borderPrimary border border-borderPrimary text-textPrimary rounded-md text-xs font-mono font-semibold transition-colors"
          >
            Return to Registry
          </button>
        </div>
      </div>
    );
  }

  const isCompleted = repo.status === 'ready';
  const isFailed = repo.status === 'failed';
  const isProcessing = !isCompleted && !isFailed;

  const isNotAnalysed = repo.total_lines_of_code === 0 || repo.files_analyzed === 0 || repo.health_grade === 'N/A';

  // Synthesis of senior engineer verdict
  const getVerdict = () => {
    if (isNotAnalysed) {
      return "No code scanned: repository contains only notebooks or unrecognised formats.";
    }
    if (repo.health_score >= 90) {
      return "Disciplined architecture with minimal coupling. Ready for production scale with only minor hygiene refactoring.";
    } else if (repo.health_score >= 80) {
      return "Solid structural foundation. Moderate complexity spots detected in core services; address top smells to prevent technical debt.";
    } else if (repo.health_score >= 70) {
      return "Functional codebase with noticeable design drift. Several files exceed healthy cognitive complexity thresholds and lack test boundaries.";
    } else {
      return "Elevated risk profile. Significant architectural coupling and code smells warrant a structured stabilization cycle.";
    }
  };

  // Health Breakdown segments
  const healthMeta = repo.knowledge_summary?.health_metadata;
  const breakdown = healthMeta?.breakdown || {
    structure: { score: Math.round(repo.health_score * 0.3), max: 30 },
    security: { score: Math.round(repo.health_score * 0.25), max: 25 },
    smells: { score: Math.round(repo.health_score * 0.25), max: 25 },
    tests: { score: Math.round(repo.health_score * 0.2), max: 20 },
  };

  // Severity styling helper with WCAG contrast
  const getPriorityStyle = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'critical':
        return 'text-bad bg-bad-bg border-bad-border';
      case 'high':
        return 'text-bad bg-bad-bg border-bad-border';
      case 'medium':
        return 'text-warn bg-warn-bg border-warn-border';
      case 'low':
      default:
        return 'text-good bg-good-bg border-good-border';
    }
  };

  const cleanRepoName = repo.url.replace(/^https?:\/\/github\.com\//, '').replace(/\.git$/, '');
  const repoOwner = cleanRepoName.split('/')[0] || 'repository';
  const repoSlug = cleanRepoName.split('/')[1] || cleanRepoName;

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans transition-colors duration-200">
      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="overview" 
      />

      <main className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-10 pt-[76px] pb-16 space-y-10 flex-grow">

        {/* PROCESSING CHECKLIST VIEW */}
        {isProcessing && (
          <div className="max-w-2xl mx-auto bg-bgSecondary border border-borderPrimary rounded-lg p-8 shadow-report space-y-6 mt-10">
            <div className="flex items-center gap-3 border-b border-borderPrimary pb-4">
              <Loader2 className="w-5 h-5 text-signal animate-spin" />
              <div>
                <h2 className="font-serif text-xl font-bold tracking-tight text-textPrimary">
                  Engineering Inspection in Progress
                </h2>
                <p className="text-xs text-textSecondary font-mono mt-0.5">
                  Static analysis & dependency graph extraction underway...
                </p>
              </div>
            </div>
            
            <div className="divide-y divide-borderPrimary text-xs font-mono">
              {[
                { key: 'clone', label: '1. Clone Repository Tree' },
                { key: 'parse', label: '2. Scan Files & Abstract Syntax' },
                { key: 'tech_detect', label: '3. Detect Language & Build Frameworks' },
                { key: 'metrics', label: '4. Compute Cognitive Complexity & LOC' },
                { key: 'architecture', label: '5. Build Layered Swim-Lane Topology' },
                { key: 'security', label: '6. Check Secret Leaks & Vulnerabilities' }
              ].map((stg) => {
                const info = repo.progress?.[stg.key] || { status: 'pending' };
                const isDone = info.status === 'completed';
                const isRunning = info.status === 'running';
                return (
                  <div key={stg.key} className="py-2.5 flex items-center justify-between">
                    <span className={isDone ? 'text-textPrimary font-semibold' : isRunning ? 'text-signal font-bold' : 'text-textMuted'}>
                      {stg.label}
                    </span>
                    {isDone ? (
                      <span className="text-good font-bold flex items-center gap-1">
                        <Check className="w-3.5 h-3.5" /> DONE
                      </span>
                    ) : isRunning ? (
                      <span className="text-signal font-bold uppercase tracking-wider animate-pulse">RUNNING</span>
                    ) : (
                      <span className="text-textMuted">QUEUED</span>
                    )}
                  </div>
                );
              })}
            </div>
            
            <div className="pt-2 text-[10px] text-textMuted font-mono">
              INSPECTION REF: #{repo.id.slice(0, 8)} // STAGE: {repo.current_stage || 'QUEUED'}
            </div>
          </div>
        )}

        {/* FAILED STATE VIEW */}
        {isFailed && (
          <div className="max-w-2xl mx-auto bg-bgSecondary border border-bad-border rounded-lg p-8 shadow-report space-y-5 mt-10">
            <div className="flex items-center gap-3 pb-3 border-b border-bad-border">
              <ShieldAlert className="w-6 h-6 text-bad" />
              <div>
                <h2 className="font-serif text-xl font-bold text-textPrimary">Analysis Interrupted</h2>
                <p className="text-xs text-textSecondary font-mono">The pipeline could not complete parsing.</p>
              </div>
            </div>
            <pre className="bg-bgTertiary p-4 rounded text-xs font-mono text-bad overflow-x-auto whitespace-pre-wrap border border-borderPrimary">
              {repo.error_message || 'Unknown execution failure.'}
            </pre>
            <button 
              onClick={() => router.push('/')} 
              className="py-2 px-4 bg-bgTertiary hover:bg-borderPrimary border border-borderPrimary text-textPrimary rounded text-xs font-mono font-semibold"
            >
              Return Home
            </button>
          </div>
        )}

        {/* READY DASHBOARD OVERVIEW */}
        {isCompleted && (
          <div className="space-y-10 animate-fade-in">

            {/* 1. REPORT HERO: Large Serif Stamp + Target Verdict */}
            <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-10 shadow-report relative overflow-hidden">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8">
                
                {/* Left: Metadata & Editorial Verdict */}
                <div className="space-y-4 max-w-3xl">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="section-header px-2 py-0.5 rounded bg-bgTertiary border border-borderPrimary text-[10px]">
                      FIELD INSPECTION REPORT
                    </span>
                    <span className="text-textMuted text-xs font-mono">•</span>
                    <span className="text-xs font-mono text-textSecondary">
                      {new Date(repo.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
                    </span>
                    <span className="text-textMuted text-xs font-mono">•</span>
                    <span className="text-xs font-mono text-textMuted uppercase">
                      REF: {repo.id.slice(0, 8)}
                    </span>
                    {repo.knowledge_summary?.analysis_budget?.status_display && (
                      <>
                        <span className="text-textMuted text-xs font-mono">•</span>
                        <span className={`text-xs font-mono font-semibold ${
                          repo.knowledge_summary.analysis_budget.is_partial ? 'text-[#C4A000]' : 'text-good'
                        }`}>
                          {repo.knowledge_summary.analysis_budget.status_display}
                          {repo.knowledge_summary.analysis_budget.is_partial ? ' (PARTIAL BUDGET)' : ''}
                        </span>
                      </>
                    )}
                  </div>

                  <div>
                    <h1 className="font-serif text-3xl sm:text-5xl font-bold tracking-tight text-textPrimary leading-[1.08]">
                      {repoSlug}
                    </h1>
                    <p className="text-xs sm:text-sm font-mono text-textSecondary mt-1">
                      Target repository: <span className="text-textPrimary">{repoOwner}/{repoSlug}</span>
                    </p>
                  </div>

                  <div className="border-l-2 border-signal pl-4 py-1">
                    <p className="text-xs sm:text-sm text-textPrimary leading-relaxed font-sans font-medium">
                      "{getVerdict()}"
                    </p>
                    <span className="text-[10px] font-mono text-textSecondary block mt-1 uppercase tracking-wider">
                      Staff Engineer Assessment
                    </span>
                  </div>
                </div>

                {/* Right: The Huge Grade Stamp */}
                <div className="shrink-0 flex items-center lg:justify-end">
                  <div className="p-6 sm:p-8 rounded-lg border-2 border-borderStrong bg-bgPrimary flex flex-col items-center justify-center min-w-[200px] text-center shadow-report">
                    <span className="section-header text-[10px] mb-1">COMPOSITE GRADE</span>
                    <div className="inspection-stamp text-7xl sm:text-8xl font-black text-textPrimary">
                      {isNotAnalysed ? "—" : repo.health_grade}
                    </div>
                    <div className="mt-2 text-xs font-mono font-bold text-textSecondary">
                      {isNotAnalysed ? (
                        <span className="text-textMuted text-xs font-mono">0 LOC SCANNED</span>
                      ) : (
                        <>
                          <span className="text-textPrimary text-base font-extrabold">{repo.health_score}</span> / 100 PTS
                        </>
                      )}
                    </div>
                    <div className="mt-1">
                      {isNotAnalysed ? (
                        <span className="inline-block px-2 py-0.5 text-[9px] font-mono font-bold uppercase rounded border text-textMuted bg-bgTertiary border-borderPrimary">
                          Not Analysed
                        </span>
                      ) : (
                        <span className={`inline-block px-2 py-0.5 text-[9px] font-mono font-bold uppercase rounded border ${
                          repo.health_score >= 80 ? 'text-good bg-good-bg border-good-border' : 'text-warn bg-warn-bg border-warn-border'
                        }`}>
                          {repo.health_score >= 90 ? 'Production Grade' : repo.health_score >= 80 ? 'Passing / Minor Debt' : 'Attention Required'}
                        </span>
                      )}
                    </div>
                    <div className="mt-2 text-[10px] font-mono text-textMuted border-t border-borderPrimary/60 pt-1.5 w-full text-center">
                      analyzed {repo.files_analyzed} of {repo.total_files} files
                    </div>
                  </div>
                </div>

              </div>

              {/* 2. SEGMENTED HEALTH BAR: Score broken into distinct components */}
              <div className="mt-8 pt-8 border-t border-borderPrimary space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between text-xs font-mono gap-1">
                  <span className="section-header">HEALTH PROFILE SEGMENTS</span>
                  <span className="text-textSecondary">
                    Baseline: <strong className="text-textPrimary">{repo.health_score}</strong> → Potential with remediation: <strong className="text-signal">{potentialScore}</strong> (+{potentialScore - repo.health_score} pts)
                  </span>
                </div>

                {/* Segmented Progress Bar */}
                <div className="grid grid-cols-4 gap-1.5 h-3 bg-bgTertiary p-1 rounded border border-borderPrimary">
                  {Object.entries(breakdown).map(([key, val]: [string, any], idx) => {
                    const pct = Math.min(100, Math.round((val.score / (val.max || 25)) * 100));
                    return (
                      <div key={key} className="h-full bg-bgPrimary rounded-sm overflow-hidden relative" title={`${key}: ${val.score}/${val.max}`}>
                        <div 
                          className="h-full bg-signal/80 transition-all duration-500 rounded-sm" 
                          style={{ width: `${pct}%` }} 
                        />
                      </div>
                    );
                  })}
                </div>

                {/* Segment Labels */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1 text-xs font-mono">
                  {Object.entries(breakdown).map(([key, val]: [string, any]) => (
                    <div key={key} className="flex justify-between items-center text-[11px] border-b border-borderPrimary/60 pb-1">
                      <span className="capitalize text-textSecondary">{key}</span>
                      <span className="font-semibold text-textPrimary">{val.score}/{val.max}</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {/* Knowledge Base Status Notice */}
            {(repo.knowledge_status === 'interrupted' || repo.knowledge_status === 'failed' || repo.knowledge_status === 'indexing') && (
              <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-4 font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-report">
                <div className="flex items-center gap-2.5">
                  {repo.knowledge_status === 'indexing' ? (
                    <Loader2 className="w-4 h-4 text-signal animate-spin shrink-0" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-[#C4A000] shrink-0" />
                  )}
                  <div>
                    <span className="font-bold text-textPrimary">
                      {repo.knowledge_status === 'indexing'
                        ? 'Knowledge Base Indexing in Progress'
                        : 'Knowledge Base Incomplete (Summary Only)'}
                    </span>
                    <p className="text-[11px] text-textSecondary font-sans mt-0.5">
                      {repo.knowledge_status === 'indexing'
                        ? 'Chunking AST nodes and generating vector embeddings in background for AI Mentor.'
                        : 'Only architectural evidence summaries are indexed. Re-index code to enable source-level grounded answers in AI Mentor.'}
                    </p>
                  </div>
                </div>
                {repo.knowledge_status !== 'indexing' && (
                  <button
                    onClick={handleRetryKb}
                    disabled={isRetryingKb}
                    className="px-3 py-1.5 bg-signal/10 hover:bg-signal/20 text-signal border border-signal/30 rounded font-bold transition-colors shrink-0 flex items-center gap-1.5"
                  >
                    {isRetryingKb && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    <span>{isRetryingKb ? 'Triggering...' : 'Re-index Code Chunks'}</span>
                  </button>
                )}
              </section>
            )}

            {/* 3. NUMBERED ONBOARDING PATH (Reading Guide with "You Are Here") */}
            <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 shadow-report space-y-4">
              <div className="flex items-center justify-between border-b border-borderPrimary pb-3">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-signal" />
                  <span className="section-header">FIELD REPORT READING ORDER</span>
                </div>
                <span className="text-[11px] font-mono text-textMuted">8-Step Senior Engineer Audit</span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
                {[
                  { num: '01', label: 'Overview', path: `/repositories/${repoId}`, active: true, desc: 'Score & stats' },
                  { num: '02', label: 'Assessment', path: `/repositories/${repoId}/assessment`, active: false, desc: 'Smell audit' },
                  { num: '03', label: 'Architecture', path: `/repositories/${repoId}/architecture`, active: false, desc: 'Swim-lanes' },
                  { num: '04', label: 'Security', path: `/repositories/${repoId}/security`, active: false, desc: 'Leak scan' },
                  { num: '05', label: 'Performance', path: `/repositories/${repoId}/performance`, active: false, desc: 'Hotspots' },
                  { num: '06', label: 'AI Mentor', path: `/repositories/${repoId}/mentor`, active: false, desc: 'Grounded Q&A' },
                  { num: '07', label: 'Knowledge', path: `/repositories/${repoId}/knowledge`, active: false, desc: 'Vector index' },
                ].map((step) => (
                  <button
                    key={step.num}
                    onClick={() => router.push(step.path)}
                    className={`p-3 text-left rounded border transition-all text-xs font-mono relative flex flex-col justify-between h-20 ${
                      step.active
                        ? 'bg-signal/5 border-signal text-textPrimary'
                        : 'bg-bgPrimary border-borderPrimary text-textSecondary hover:border-textMuted hover:text-textPrimary'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className={`text-[10px] font-bold ${step.active ? 'text-signal' : 'text-textMuted'}`}>
                        {step.num}
                      </span>
                      {step.active && (
                        <span className="text-[8px] px-1 py-0.2 bg-signal text-white rounded font-bold uppercase tracking-tight">
                          YOU ARE HERE
                        </span>
                      )}
                    </div>
                    <div>
                      <span className="font-bold text-xs block text-textPrimary">{step.label}</span>
                      <span className="text-[10px] text-textMuted block">{step.desc}</span>
                    </div>
                  </button>
                ))}
              </div>
            </section>

            {/* 4. ASYMMETRIC STATS GRID (Different sizes, editorial hierarchy) */}
            <section className="grid grid-cols-1 md:grid-cols-12 gap-5">
              
              {/* Stat A (5 cols): Repository Volume & Scale */}
              <div className="md:col-span-4 bg-bgSecondary border border-borderPrimary rounded-lg p-6 shadow-report flex flex-col justify-between space-y-4">
                <span className="section-header">01 // CODEBASE VOLUME</span>
                <div>
                  <div className="data-mono text-4xl sm:text-5xl font-black text-textPrimary">
                    {repo.total_lines_of_code.toLocaleString()}
                  </div>
                  <span className="text-xs font-mono text-textSecondary block mt-1">Total Clean Lines of Code (LOC)</span>
                </div>
                <div className="pt-3 border-t border-borderPrimary flex flex-col gap-1 text-xs font-mono text-textSecondary">
                  <div className="flex items-center justify-between">
                    <span>
                      {repo.knowledge_summary?.analysis_budget?.status_display ? (
                        <span className={repo.knowledge_summary.analysis_budget.is_partial ? 'text-[#C4A000] font-semibold' : 'text-good font-semibold'}>
                          {repo.knowledge_summary.analysis_budget.status_display}
                        </span>
                      ) : (
                        <span>{repo.total_files} Files</span>
                      )}
                    </span>
                    <span>•</span>
                    <span>{repo.total_folders} Folders</span>
                    <span>•</span>
                    <span>{repo.total_smells} Smells</span>
                  </div>
                  {repo.knowledge_summary?.analysis_budget?.is_partial && (
                    <div className="text-[10px] text-[#C4A000] font-semibold flex items-center gap-1">
                      <span>⚠️ Partial analysis ({repo.knowledge_summary.analysis_budget.budget_seconds}s limit reached)</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Stat B (4 cols): Technology Stack & Runtime */}
              <div className="md:col-span-4 bg-bgSecondary border border-borderPrimary rounded-lg p-6 shadow-report flex flex-col justify-between space-y-4">
                <span className="section-header">02 // TECH STACK DETECTED</span>
                <div>
                  <div className="font-serif text-2xl sm:text-3xl font-bold text-textPrimary truncate" title={repo.tech_stack?.frameworks?.join(', ') || ''}>
                    {repo.tech_stack?.frameworks?.length ? repo.tech_stack.frameworks[0] : 'Standard Runtime'}
                  </div>
                  <span className="text-xs font-mono text-textSecondary block mt-1">
                    {repo.tech_stack?.frameworks?.slice(1).join(', ') || 'No secondary dependencies'}
                  </span>
                </div>
                <div className="pt-3 border-t border-borderPrimary text-xs font-mono text-textSecondary flex justify-between">
                  <span>Package Manager:</span>
                  <span className="text-textPrimary font-bold">{repo.tech_stack?.package_manager || 'None'}</span>
                </div>
              </div>

              {/* Stat C (4 cols): Top Prioritized Risk (NO contradiction - verified severity) */}
              <div className="md:col-span-4 bg-bgSecondary border border-borderPrimary rounded-lg p-6 shadow-report flex flex-col justify-between space-y-4">
                <span className="section-header">03 // HIGHEST PRIORITY FINDING</span>
                {recommendations[0] ? (
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className={`px-2 py-0.5 text-[9px] font-mono font-bold uppercase rounded border ${getPriorityStyle(recommendations[0].priority)}`}>
                        {recommendations[0].priority} Severity
                      </span>
                      <span className="text-[10px] font-mono text-textMuted">{recommendations[0].effort} effort</span>
                    </div>
                    <h3 className="font-serif text-lg font-bold text-textPrimary line-clamp-2" title={recommendations[0].title}>
                      {recommendations[0].title}
                    </h3>
                  </div>
                ) : (
                  <div>
                    <span className="text-xs font-mono text-good font-bold">✓ No High Severity Findings</span>
                    <p className="text-xs text-textSecondary mt-1">Repository conforms to baseline hygiene rules.</p>
                  </div>
                )}
                <div className="pt-3 border-t border-borderPrimary flex items-center justify-between text-xs font-mono">
                  <span className="text-textSecondary">Potential gain:</span>
                  <span className="text-signal font-bold">+{recommendations[0]?.health_improvement || 3} pts</span>
                </div>
              </div>

            </section>

            {/* 5. ROADMAP: Vertical "Treatment Plan" Timeline */}
            <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-borderPrimary pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <Wrench className="w-4 h-4 text-signal" />
                    <span className="section-header">REMEDIATION TREATMENT PLAN</span>
                  </div>
                  <h2 className="font-serif text-2xl font-bold text-textPrimary mt-1">
                    Path to Score {potentialScore}
                  </h2>
                </div>
                <div className="text-xs font-mono text-textSecondary flex items-center gap-2">
                  <span>Current: <strong className="text-textPrimary">{repo.health_score}</strong></span>
                  <span>→</span>
                  <span>Goal: <strong className="text-signal">{potentialScore}</strong></span>
                </div>
              </div>

              {/* Vertical Timeline */}
              <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-px before:bg-borderPrimary">
                {recommendations.slice(0, 5).map((rec, idx) => {
                  const isExpanded = expandedRecId === rec.id;
                  const stepPoints = rec.health_improvement || (idx === 0 ? 4 : 2);
                  return (
                    <div key={rec.id || idx} className="relative group">
                      {/* Timeline dot */}
                      <div className="absolute -left-[27px] sm:-left-[35px] top-1.5 w-3 h-3 rounded-full bg-bgSecondary border-2 border-signal" />

                      <div className="bg-bgPrimary border border-borderPrimary rounded-lg p-5 transition-colors duration-150 hover:border-textMuted">
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-[10px] font-mono text-textMuted uppercase font-bold">
                                PHASE {idx + 1}
                              </span>
                              <span className={`px-2 py-0.5 text-[9px] font-mono font-bold uppercase rounded border ${getPriorityStyle(rec.priority)}`}>
                                {rec.priority}
                              </span>
                              <span className="text-[10px] font-mono text-textSecondary">
                                Effort: {rec.effort}
                              </span>
                              <span className="text-[10px] font-mono text-signal font-semibold">
                                +{stepPoints} Pts
                              </span>
                            </div>
                            <h3 className="font-serif text-lg font-bold text-textPrimary">
                              {rec.title}
                            </h3>
                            <p className="text-xs text-textSecondary font-sans leading-relaxed">
                              {rec.why_it_matters}
                            </p>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              onClick={() => handleAskMentor(rec)}
                              className="px-3 py-1.5 rounded bg-bgTertiary hover:bg-borderPrimary border border-borderPrimary text-textPrimary text-xs font-mono flex items-center gap-1 transition-colors"
                              title="Ask Mentor about this refactor"
                            >
                              <Sparkles className="w-3 h-3 text-signal" />
                              <span>Mentor</span>
                            </button>
                            <button
                              onClick={() => setExpandedRecId(isExpanded ? null : rec.id)}
                              className="p-1.5 rounded hover:bg-bgTertiary text-textSecondary transition-colors"
                              aria-label="Toggle details"
                            >
                              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </button>
                          </div>
                        </div>

                        {/* Collapsible Action Steps & Affected Files */}
                        {isExpanded && (
                          <div className="mt-4 pt-4 border-t border-borderPrimary space-y-4 text-xs font-mono animate-fade-in">
                            {rec.affected_files && rec.affected_files.length > 0 && (
                              <div>
                                <span className="text-[10px] text-textMuted uppercase block mb-1">AFFECTED SOURCE FILES:</span>
                                <div className="flex flex-wrap gap-1.5">
                                  {rec.affected_files.map((file, fIdx) => (
                                    <span key={fIdx} className="px-2 py-0.5 bg-bgTertiary border border-borderPrimary rounded text-[11px] text-textPrimary">
                                      {file}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {rec.steps && rec.steps.length > 0 && (
                              <div>
                                <span className="text-[10px] text-textMuted uppercase block mb-1">REMEDIATION CHECKLIST:</span>
                                <ul className="space-y-1 text-textSecondary">
                                  {rec.steps.map((st, sIdx) => (
                                    <li key={sIdx} className="flex items-start gap-2">
                                      <span className="text-signal font-bold">•</span>
                                      <span>{st}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* 6. EXPANDABLE SCORING ADJUSTMENT LEDGER */}
            <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 shadow-report space-y-4">
              <div className="flex items-center justify-between border-b border-borderPrimary pb-3">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-signal" />
                  <span className="section-header">SCORING ADJUSTMENTS & CRITERIA LEDGER</span>
                </div>
                <button
                  onClick={() => setIsLedgerExpanded(!isLedgerExpanded)}
                  className="px-2.5 py-1 text-xs font-mono rounded bg-bgTertiary hover:bg-borderPrimary border border-borderPrimary text-textPrimary transition-colors"
                >
                  {isLedgerExpanded ? 'Collapse Ledger' : 'Expand All Deductions'}
                </button>
              </div>

              {isLedgerExpanded && repo.knowledge_summary?.health_metadata?.details && (
                <div className="space-y-2 animate-fade-in text-xs font-mono max-h-80 overflow-y-auto">
                  {repo.knowledge_summary.health_metadata.details.map((item, idx) => (
                    <div key={idx} className="p-3 bg-bgPrimary border border-borderPrimary rounded flex items-center justify-between gap-4">
                      <div className="space-y-0.5">
                        <span className="font-semibold text-textPrimary block">{item.rule}</span>
                        <span className="text-[11px] text-textSecondary block">{item.reason}</span>
                      </div>
                      <div className="text-right shrink-0">
                        <span className={`font-bold ${item.impact < 0 ? 'text-bad' : 'text-good'}`}>
                          {item.impact > 0 ? `+${item.impact}` : item.impact} pts
                        </span>
                        <span className="text-[10px] text-textMuted block capitalize">{item.dimension}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

          </div>
        )}

      </main>
    </div>
  );
}
