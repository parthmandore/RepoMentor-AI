'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Clock, Zap, Database, Cpu, ShieldAlert, Activity,
  Server, Layers, CheckCircle2, Gauge, History, ArrowRight, Scissors
} from 'lucide-react';

import Header from '../../../Header';
import { PageLayoutSkeleton } from '../../../components/Skeletons';

interface RepositoryResponse {
  id: string;
  url: string;
  status: string;
  status_message: string | null;
  knowledge_status: string;
  error_message: string | null;
  total_files: number;
  total_folders: number;
  health_score: number;
  completed_at: string | null;
  duration_seconds: number | null;
  knowledge_summary?: {
    total_chunks?: number;
    code_chunks?: number;
    evidence_documents?: number;
    indexed_files?: number;
    last_commit_hash?: string;
    file_cache_hits?: number;
    file_cache_misses?: number;
    embedding_provider?: string;
    embedding_status?: string;
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
    skipped_files?: Array<{ path: string; reason: string; size?: number }>;
    truncated_files?: Array<{ path: string; reason: string; total_chunks?: number; retained_chunks?: number; dropped_chunks?: number }>;
    timing_metadata?: {
      clone?: number;
      parsing?: number;
      metrics?: number;
      architecture?: number;
      security?: number;
      database?: number;
      phase_a_database?: number;
      total_phase_a?: number;
      cache_hit?: boolean;
    };
    diagnostics?: {
      files_processed?: number;
      chunks_generated?: number;
      embedding_time_sec?: number;
      pgvector_write_time_sec?: number;
      total_duration_sec?: number;
      average_chunk_size?: number;
      largest_chunk?: number;
      embedding_requests?: number;
      pgvector_inserts?: number;
    };
    performance?: {
      clone?: number;
      parser?: number;
      metrics?: number;
      architecture?: number;
      security?: number;
      time_to_first_page?: number;
      model_load?: number;
      chunking?: number;
      embeddings?: number;
      database?: number;
      assessment?: number;
      knowledge?: number;
      total?: number;
      skipped_files?: Array<{ path: string; reason: string; size?: number }>;
      skipped_files_count?: number;
      truncated_files?: Array<{ path: string; reason: string; total_chunks?: number; retained_chunks?: number; dropped_chunks?: number }>;
      truncated_files_count?: number;
    };
  } | null;
}

function formatDuration(sec?: number, stageStatus?: string): string {
  if (stageStatus === 'pending') return 'Pending';
  if (stageStatus === 'running') return 'Running...';
  if (stageStatus === 'skipped') return 'Skipped';
  if (stageStatus === 'interrupted') return 'Interrupted';
  if (stageStatus === 'not_run') return 'Not Executed';
  if (sec === undefined || sec === null) return 'Not Executed';
  if (sec <= 0) {
    if (stageStatus === 'completed') return '<1 ms';
    return 'Not Executed';
  }
  if (sec < 0.001) return '<1 ms';
  if (sec < 0.01) return `${(sec * 1000).toFixed(1)}ms`;
  if (sec < 1) return `${(sec * 1000).toFixed(0)}ms (${sec.toFixed(3)}s)`;
  return `${sec.toFixed(3)}s`;
}

function getExecutionStatus(total: number): { label: string; color: string; desc: string } {
  if (total <= 0) return { label: 'PENDING', color: 'text-textMuted', desc: 'Awaiting execution' };
  if (total < 30) return { label: 'OPTIMIZED', color: 'text-good', desc: 'Sub-30s fast path' };
  if (total <= 60) return { label: 'NOMINAL', color: 'text-[#C4A000]', desc: 'Standard runtime' };
  return { label: 'ELEVATED', color: 'text-signal', desc: 'Resource intensive' };
}

export default function PerformanceDashboard({ params }: { params: { id: string } }) {
  const router = useRouter();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  const [repo, setRepo] = useState<RepositoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRepoDetails = useCallback(async () => {
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}`);
      if (!res.ok) throw new Error('Repository details not found.');
      const data = await res.json();
      setRepo(data);
      setIsLoading(false);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch details');
      setIsLoading(false);
    }
  }, [apiUrl, repoId]);

  useEffect(() => {
    fetchRepoDetails();
  }, [fetchRepoDetails]);

  if (isLoading) {
    return <PageLayoutSkeleton title="Compiling Pipeline Latency Report..." />;
  }

  if (error || !repo) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4 font-sans">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-8 rounded-lg shadow-report text-center space-y-4">
          <ShieldAlert className="w-8 h-8 text-bad mx-auto" />
          <h2 className="font-serif text-xl font-bold text-textPrimary">Performance Profile Unavailable</h2>
          <p className="text-xs text-textSecondary font-mono">{error || 'Data could not be compiled.'}</p>
          <button onClick={() => router.push(`/repositories/${repoId}`)} className="py-2 px-4 rounded bg-bgTertiary text-xs font-mono font-bold">
            Return to Overview
          </button>
        </div>
      </div>
    );
  }

  const summary = repo.knowledge_summary || {};
  const timing = summary.timing_metadata || {};
  const diagnostics = summary.diagnostics || {};
  const perf = (summary as any).performance || {};

  const skippedFiles: Array<{ path: string; reason: string; size?: number }> =
    summary.skipped_files || perf.skipped_files || [];
  const truncatedFiles: Array<{ path: string; reason: string; total_chunks?: number; retained_chunks?: number; dropped_chunks?: number }> =
    summary.truncated_files || perf.truncated_files || [];

  const cloneTime = perf.clone ?? timing.clone ?? 0;
  const parseTime = perf.parser ?? timing.parsing ?? 0;
  const metricsTime = perf.metrics ?? timing.metrics ?? 0;
  const archTime = perf.architecture ?? timing.architecture ?? 0;
  const secTime = perf.security ?? timing.security ?? 0;
  const modelLoadTime = perf.model_load ?? 0;
  const chunkingTime = perf.chunking ?? 0;
  const embedTime = perf.embeddings ?? diagnostics.embedding_time_sec ?? 0;
  const vectorDbTime = perf.vector_database ?? (perf.embeddings !== undefined ? (perf.database ?? 0) : 0);
  const phaseADbTime = perf.phase_a_database ?? timing.database ?? 0;
  const assessTime = perf.assessment ?? 0;
  const otherUnaccounted = perf.other_unaccounted ?? 0;

  const providerLabel = summary.embedding_provider || summary.embedding_status || 'Local FastEmbed';

  const timeToFirstPage = perf.time_to_first_page ?? timing.total_phase_a ?? (cloneTime + parseTime + metricsTime + archTime + secTime);
  const totalTime = perf.total ?? diagnostics.total_duration_sec ?? repo.duration_seconds ?? (timeToFirstPage + embedTime + vectorDbTime + assessTime);

  const statusInfo = getExecutionStatus(totalTime);

  const isPhaseADone = repo.status === 'ready' || repo.status === 'completed';
  const isKbDone = repo.knowledge_status === 'completed';
  const isKbIndexing = repo.knowledge_status === 'indexing';
  const isKbFailed = repo.knowledge_status === 'failed' || repo.knowledge_status === 'interrupted';
  const hasCodeChunks = (summary?.code_chunks ?? 0) > 0;
  const hasSummaryOnly = !hasCodeChunks && (isKbDone || (summary?.evidence_documents ?? 0) > 0);

  const stages = [
    { label: '01. Git Tree Clone', time: cloneTime, desc: 'Fetch branch commits and tree blobs', status: isPhaseADone ? 'completed' : 'pending' },
    { label: '02. Syntax Parsing', time: parseTime, desc: 'Tokenize files and generate AST nodes', status: isPhaseADone ? 'completed' : 'pending' },
    { label: '03. Complexity Engine', time: metricsTime, desc: 'Calculate cognitive & cyclomatic scores', status: isPhaseADone ? 'completed' : 'pending' },
    { label: '04. Swim-Lane Topology', time: archTime, desc: 'Extract import trees and circular cycles', status: isPhaseADone ? 'completed' : 'pending' },
    { label: '05. Security Review', time: secTime, desc: 'Pattern-matched credential & vulnerability scans', status: isPhaseADone ? 'completed' : 'pending' },
    { label: '06. Metadata & Code Persistence', time: phaseADbTime, desc: 'PostgreSQL storage of repository files, code smells & security issues', status: isPhaseADone ? 'completed' : 'pending' },
    { 
      label: '07. AST Code Chunking', 
      time: chunkingTime, 
      desc: 'Function/class AST boundaries and priority tiering', 
      status: chunkingTime > 0 ? 'completed' : (isKbDone ? (hasCodeChunks ? 'completed' : 'skipped') : (isKbIndexing ? 'running' : (isKbFailed ? 'interrupted' : 'pending'))) 
    },
    { 
      label: '08. Vector Embedding', 
      time: embedTime, 
      desc: `${providerLabel} remote embedding API`, 
      status: embedTime > 0 ? 'completed' : (isKbDone ? (hasCodeChunks ? 'completed' : 'skipped') : (isKbIndexing ? 'running' : (isKbFailed ? 'interrupted' : 'pending'))) 
    },
    { 
      label: '09. Vector Database Write', 
      time: vectorDbTime, 
      desc: 'Supabase pgvector multi-row bulk insertions', 
      status: vectorDbTime > 0 ? 'completed' : (isKbDone ? (hasCodeChunks ? 'completed' : 'skipped') : (isKbIndexing ? 'running' : (isKbFailed ? 'interrupted' : 'pending'))) 
    },
    { 
      label: '10. Assessment Compilation', 
      time: assessTime, 
      desc: 'AI mentor & architecture evaluation generation', 
      status: assessTime > 0 ? 'completed' : (isKbDone ? 'completed' : (isKbIndexing ? 'running' : 'pending')) 
    },
    ...(otherUnaccounted > 0 ? [{ 
      label: '11. WAN Network & Queue Overhead', 
      time: otherUnaccounted, 
      desc: 'Database connection round-trips & worker queue synchronizations',
      status: 'completed'
    }] : [])
  ];

  const maxStageTime = Math.max(0.001, ...stages.map(s => s.time));

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans transition-colors duration-200">
      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="performance" 
      />

      <main className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-10 pt-[76px] pb-16 space-y-8 flex-grow">
        
        {/* HERO / OVERVIEW */}
        <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="section-header px-2 py-0.5 rounded bg-bgTertiary border border-borderPrimary text-[10px]">
                  SECTION 05 // LATENCY & EXECUTION PROFILE
                </span>
                <span className="text-xs font-mono text-textMuted">•</span>
                <span className="text-xs font-mono text-textSecondary">{repo.total_files} files in tree</span>
                {summary?.analysis_budget?.status_display && (
                  <>
                    <span className="text-xs font-mono text-textMuted">•</span>
                    <span className={`text-xs font-mono font-semibold ${
                      summary.analysis_budget.is_partial ? 'text-[#C4A000]' : 'text-good'
                    }`}>
                      {summary.analysis_budget.status_display}
                      {summary.analysis_budget.is_partial ? ' (PARTIAL BUDGET)' : ''}
                    </span>
                  </>
                )}
                {skippedFiles.length > 0 && (
                  <>
                    <span className="text-xs font-mono text-textMuted">•</span>
                    <span className="text-xs font-mono text-signal/90 font-semibold">
                      {skippedFiles.length} file{skippedFiles.length > 1 ? 's' : ''} skipped
                    </span>
                  </>
                )}
                {truncatedFiles.length > 0 && (
                  <>
                    <span className="text-xs font-mono text-textMuted">•</span>
                    <span className="text-xs font-mono text-signal font-semibold">
                      {truncatedFiles.length} file{truncatedFiles.length > 1 ? 's' : ''} capped
                    </span>
                  </>
                )}
              </div>
              <h1 className="font-serif text-3xl sm:text-4xl font-bold text-textPrimary">
                Pipeline Execution Timings
              </h1>
              <p className="text-xs sm:text-sm text-textSecondary max-w-2xl font-sans leading-relaxed">
                Measured wall-clock duration across every deterministic analysis phase and knowledge index stage.
              </p>
            </div>

            {/* Total Duration Stamp */}
            <div className="shrink-0 p-4 sm:p-6 rounded border-2 border-borderStrong bg-bgPrimary text-center min-w-[160px] shadow-report">
              <span className="section-header text-[9px] block">TOTAL DURATION</span>
              <div className="inspection-stamp text-4xl sm:text-5xl font-black text-textPrimary mt-1">
                {totalTime > 0 ? `${totalTime.toFixed(2)}s` : '<1s'}
              </div>
              <span className="text-[10px] font-mono text-textSecondary block mt-0.5">
                End-to-End Pipeline
              </span>
            </div>
          </div>

          {/* Quick Metrics Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6 mt-6 border-t border-borderPrimary text-xs font-mono">
            <div className="p-3 bg-bgPrimary border border-borderPrimary rounded">
              <span className="text-[10px] text-textMuted uppercase block">TIME TO FIRST USABLE PAGE</span>
              <strong className="text-base text-textPrimary">
                {timeToFirstPage > 0 ? (timeToFirstPage < 1 ? `${(timeToFirstPage * 1000).toFixed(0)}ms` : `${timeToFirstPage.toFixed(2)}s`) : '<1s'}
              </strong>
            </div>
            <div className="p-3 bg-bgPrimary border border-borderPrimary rounded">
              <span className="text-[10px] text-textMuted uppercase block">STATIC CODE ANALYSIS</span>
              <strong className="text-base text-textPrimary">
                {(metricsTime + parseTime + archTime + secTime).toFixed(2)}s
              </strong>
            </div>
            <div className="p-3 bg-bgPrimary border border-borderPrimary rounded">
              <span className="text-[10px] text-textMuted uppercase block">VECTOR INDEXING (WALL)</span>
              <strong className="text-base text-textPrimary">
                {embedTime > 0
                  ? `${embedTime.toFixed(2)}s`
                  : isKbIndexing
                    ? 'Indexing...'
                    : isKbFailed
                      ? 'Interrupted'
                      : (summary.code_chunks ?? 0) === 0 && (isKbDone || (summary.evidence_documents ?? 0) > 0)
                        ? 'Summary Only'
                        : isKbDone && (summary.file_cache_hits ?? 0) > 0
                          ? 'Cached'
                          : 'Pending'}
              </strong>
            </div>
            <div className="p-3 bg-bgPrimary border border-borderPrimary rounded">
              <span className="text-[10px] text-textMuted uppercase block">EXECUTION STATUS</span>
              <strong className={`text-base font-bold ${statusInfo.color}`}>
                {statusInfo.label}
              </strong>
            </div>
            {summary?.analysis_budget && (
              <div className="p-3 bg-bgPrimary border border-borderPrimary rounded col-span-2 sm:col-span-4 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-textMuted uppercase block">AST METRICS FILE ANALYSIS BUDGET (90s LIMIT)</span>
                  <span className={`text-sm font-bold ${summary.analysis_budget.is_partial ? 'text-[#C4A000]' : 'text-good'}`}>
                    {summary.analysis_budget.status_display}
                  </span>
                  <span className="text-[10px] text-textSecondary font-mono ml-2">
                    ({summary.analysis_budget.elapsed_seconds}s used of {summary.analysis_budget.budget_seconds}s limit)
                  </span>
                  <p className="text-[10px] text-textMuted font-sans mt-0.5">
                    Constrains AST cognitive & cyclomatic complexity evaluation pass. Full Phase A (parsing, architecture graph, security scanning) ran to completion.
                  </p>
                </div>
                {summary.analysis_budget.is_partial ? (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-warn-bg text-warn border border-warn-border shrink-0">
                    Partial Budget Reached
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-good-bg text-good border border-good-border shrink-0">
                    Complete Analysis
                  </span>
                )}
              </div>
            )}
          </div>
        </section>

        {/* FAILURE BANNER */}
        {(repo.status === 'failed' || repo.knowledge_status === 'failed' || (summary as any)?.build_status === 'failed') && (
          <section className="bg-bad/10 border-2 border-bad/40 rounded-lg p-6 shadow-report font-mono space-y-2">
            <div className="flex items-center gap-2 text-bad font-bold text-sm">
              <ShieldAlert className="w-5 h-5 shrink-0" />
              <span>PIPELINE EXECUTION FAILURE DETECTED</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-2">
              <div className="p-3 bg-bgPrimary border border-bad/30 rounded">
                <span className="text-[10px] text-textMuted uppercase block">FAILURE STAGE</span>
                <strong className="text-bad font-bold text-sm">
                  {(summary as any)?.failure_stage || perf.failure_stage || repo.status_message || 'Unknown Stage'}
                </strong>
              </div>
              <div className="p-3 bg-bgPrimary border border-bad/30 rounded">
                <span className="text-[10px] text-textMuted uppercase block">FAILURE REASON</span>
                <span className="text-textPrimary font-sans text-xs break-words">
                  {(summary as any)?.failure_reason || repo.error_message || 'Worker thread raised an uncaught exception.'}
                </span>
              </div>
            </div>
          </section>
        )}

        {/* STAGES BREAKDOWN TABLE */}
        <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report space-y-6">
          <div className="border-b border-borderPrimary pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <span className="section-header">STAGE LATENCY BREAKDOWN</span>
              <h2 className="font-serif text-xl font-bold text-textPrimary mt-0.5">
                Individual Phase Benchmarks
              </h2>
            </div>
            <span className="text-[11px] font-mono text-textMuted">
              All timings reflect true elapsed wall-clock duration
            </span>
          </div>

          <div className="space-y-4">
            {stages.map((stg, idx) => {
              const pct = (maxStageTime > 0 && stg.time > 0) ? Math.max(1, Math.round((stg.time / maxStageTime) * 100)) : 0;
              return (
                <div key={idx} className="p-4 bg-bgPrimary border border-borderPrimary rounded space-y-2 font-mono text-xs">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <div>
                      <strong className="text-textPrimary">{stg.label}</strong>
                      <span className="text-textMuted text-[11px] font-sans sm:ml-2 block sm:inline">
                        — {stg.desc}
                      </span>
                    </div>
                    <span className="font-bold text-signal text-sm">
                      {formatDuration(stg.time, (stg as any).status)}
                    </span>
                  </div>

                  {/* Latency Bar */}
                  <div className="w-full h-2 bg-bgTertiary rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-signal/70 rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* TRUNCATED FILES (20-CHUNK BUDGET CAP) */}
        {truncatedFiles.length > 0 && (
          <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report space-y-4">
            <div className="flex items-center justify-between border-b border-borderPrimary pb-3">
              <div>
                <span className="section-header flex items-center gap-1.5">
                  <Scissors className="w-3.5 h-3.5 text-signal" />
                  BUDGET CAPPING // TRUNCATED FILES ({truncatedFiles.length})
                </span>
                <h2 className="font-serif text-xl font-bold text-textPrimary mt-0.5">
                  Files Capped at 20 Chunks
                </h2>
              </div>
              <span className="text-[11px] font-mono text-textMuted">
                Preserved highest-salience structural blocks
              </span>
            </div>
            <div className="divide-y divide-borderPrimary font-mono text-xs">
              {truncatedFiles.map((tf, idx) => (
                <div key={idx} className="py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <span className="text-textPrimary font-semibold truncate">{tf.path}</span>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-signal text-[11px] font-mono">
                      {tf.dropped_chunks ? `-${tf.dropped_chunks} chunks dropped` : 'Capped'}
                    </span>
                    <span className="text-textMuted text-[11px] font-sans">{tf.reason}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* SKIPPED FILES (GUARD FILTERING) */}
        {skippedFiles.length > 0 && (
          <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report space-y-4">
            <div className="flex items-center justify-between border-b border-borderPrimary pb-3">
              <div>
                <span className="section-header">DATA & ASSET GUARDS</span>
                <h2 className="font-serif text-xl font-bold text-textPrimary mt-0.5">
                  Skipped Files ({skippedFiles.length})
                </h2>
              </div>
              <span className="text-[11px] font-mono text-textMuted">
                Excluded from vector embeddings
              </span>
            </div>
            <div className="divide-y divide-borderPrimary font-mono text-xs">
              {skippedFiles.map((sf, idx) => (
                <div key={idx} className="py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                  <span className="text-textPrimary font-semibold truncate">{sf.path}</span>
                  <span className="text-textMuted text-[11px] shrink-0 font-sans">{sf.reason}</span>
                </div>
              ))}
            </div>
          </section>
        )}

      </main>
    </div>
  );
}
