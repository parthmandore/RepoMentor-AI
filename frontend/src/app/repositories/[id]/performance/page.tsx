'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, Clock, Zap, Database, Cpu, ShieldAlert,
  ChevronRight, Activity, Sparkles, Layers, Terminal,
  CheckCircle2, Gauge, History, Server
} from 'lucide-react';
import Header from '../../../Header';

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
    timing_metadata?: {
      clone?: number;
      parsing?: number;
      metrics?: number;
      architecture?: number;
      security?: number;
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
  } | null;
}

export default function PerformanceDashboard({ params }: { params: { id: string } }) {
  const router = useRouter();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';

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
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#070913] text-gray-100">
        <div className="text-center space-y-4">
          <div className="w-8 h-8 animate-spin border-4 border-brand-500 border-t-transparent rounded-full mx-auto" />
          <p className="text-xs text-gray-400">Loading Performance Metrics...</p>
        </div>
      </div>
    );
  }

  if (error || !repo) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#070913] px-4">
        <div className="max-w-md w-full bg-[#0d1224] border border-zinc-800 p-6 rounded-2xl shadow-xl text-center space-y-6">
          <ShieldAlert className="w-8 h-8 text-rose-400 mx-auto" />
          <h2 className="text-xl font-bold text-white">Error</h2>
          <p className="text-sm text-gray-400">{error}</p>
          <button onClick={() => router.push(`/repositories/${repoId}`)} className="w-full py-2.5 px-4 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl text-sm font-semibold transition-all">
            Return to Overview
          </button>
        </div>
      </div>
    );
  }

  const summary = repo.knowledge_summary || {};
  const timing = summary.timing_metadata || {};
  const diagnostics = summary.diagnostics || {};
  const performance = (summary as any).performance || {};
  
  const cacheHit = timing.cache_hit || false;
  const fileCacheHits = summary.file_cache_hits || 0;
  const fileCacheMisses = summary.file_cache_misses || 0;
  const totalCachedFiles = fileCacheHits + fileCacheMisses;
  const fileCacheEfficiency = totalCachedFiles > 0 ? (fileCacheHits / totalCachedFiles) * 100 : 0;

  const cloneTime = performance.clone || timing.clone || 0;
  const parseTime = performance.parser || timing.parsing || 0;
  const metricsTime = performance.metrics || timing.metrics || 0;
  const archTime = performance.architecture || timing.architecture || 0;
  const secTime = performance.security || timing.security || 0;
  const chunkTime = performance.chunking || 0;
  const embedTime = performance.embeddings || diagnostics.embedding_time_sec || 0;
  const vectorTime = performance.database || diagnostics.pgvector_write_time_sec || 0;
  const totalTime = performance.total || diagnostics.total_duration_sec || repo.duration_seconds || 0;

  // Vector speed vectors/sec
  const chunksCount = diagnostics.chunks_generated || summary.total_chunks || 0;
  const embedSpeed = embedTime > 0 ? Math.round(chunksCount / embedTime) : 0;

  // Render timing bar widths
  const maxTimeVal = Math.max(0.1, cloneTime, parseTime, metricsTime, archTime, secTime, chunkTime, embedTime, vectorTime);
  const getPctWidth = (val: number) => `${Math.max(3, (val / maxTimeVal) * 100)}%`;

  return (
    <div className="min-h-screen bg-[#070913] text-zinc-100 flex flex-col font-sans selection:bg-brand-500/20">
      {/* Background glow effects */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-brand-500/5 rounded-full blur-[120px] pointer-events-none -z-10" />
      <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-[120px] pointer-events-none -z-10" />

      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="performance" 
      />

      {/* Main Content Viewport */}
      <main className="w-full max-w-[1700px] mx-auto px-4 sm:px-6 lg:px-12 pt-[92px] pb-6 space-y-6 flex-grow animate-fade-in">
        
        {/* Core KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-[#0c0f1e]/60 border border-zinc-900 rounded-2xl p-5 shadow-lg flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold block">Total Index Time</span>
              <h2 className="text-xl font-bold text-white">
                {cacheHit ? '0.00s' : `${totalTime.toFixed(2)}s`}
              </h2>
            </div>
            <div className="p-3 bg-brand-500/10 border border-brand-500/20 rounded-xl text-brand-300">
              <Clock className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-[#0c0f1e]/60 border border-zinc-900 rounded-2xl p-5 shadow-lg flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold block">Embedding Speed</span>
              <h2 className="text-xl font-bold text-emerald-400">
                {cacheHit ? 'Cached' : `${embedSpeed} vectors/s`}
              </h2>
            </div>
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-300">
              <Zap className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-[#0c0f1e]/60 border border-zinc-900 rounded-2xl p-5 shadow-lg flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold block">Commit Cache Hit</span>
              <h2 className={`text-xl font-bold ${cacheHit ? 'text-brand-400 animate-pulse' : 'text-zinc-400'}`}>
                {cacheHit ? 'YES' : 'NO'}
              </h2>
            </div>
            <div className={`p-3 rounded-xl border ${cacheHit ? 'bg-brand-500/10 border-brand-500/20 text-brand-300' : 'bg-zinc-950 border-zinc-900 text-zinc-500'}`}>
              <History className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-[#0c0f1e]/60 border border-zinc-900 rounded-2xl p-5 shadow-lg flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold block">File Vector Reuse</span>
              <h2 className="text-xl font-bold text-white">
                {fileCacheHits} / {totalCachedFiles} files
              </h2>
            </div>
            <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-300">
              <Database className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Detailed Timings Breakdowns */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Timing Pipeline Progress */}
          <div className="lg:col-span-2 bg-[#0c0f1e]/40 border border-zinc-900 rounded-2xl p-6 shadow-xl space-y-6">
            <div className="border-b border-zinc-900 pb-3 flex justify-between items-center">
              <h3 className="text-sm font-bold text-white tracking-wide uppercase">Pipeline Phase Durations</h3>
              <span className="text-[10px] text-zinc-500 font-mono">Max scale: {maxTimeVal.toFixed(1)}s</span>
            </div>

            <div className="space-y-4 text-xs">
              {/* Clone */}
              <div className="space-y-1.5">
                <div className="flex justify-between font-medium text-zinc-300">
                  <span className="flex items-center gap-1.5">
                    <Server className="w-3.5 h-3.5 text-zinc-500" />
                    Git Clone (depth=1, lazy-load)
                  </span>
                  <span className="font-mono text-zinc-400">{cloneTime.toFixed(2)}s</span>
                </div>
                <div className="w-full bg-zinc-950 h-2.5 rounded-full overflow-hidden border border-zinc-900/60">
                  <div className="bg-sky-500 h-full rounded-full transition-all duration-500" style={{ width: getPctWidth(cloneTime) }} />
                </div>
              </div>

              {/* Parsing */}
              <div className="space-y-1.5">
                <div className="flex justify-between font-medium text-zinc-300">
                  <span className="flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-zinc-500" />
                    AST Parser & File Filter
                  </span>
                  <span className="font-mono text-zinc-400">{parseTime.toFixed(2)}s</span>
                </div>
                <div className="w-full bg-zinc-950 h-2.5 rounded-full overflow-hidden border border-zinc-900/60">
                  <div className="bg-indigo-500 h-full rounded-full transition-all duration-500" style={{ width: getPctWidth(parseTime) }} />
                </div>
              </div>

              {/* Parallel metrics */}
              <div className="space-y-1.5">
                <div className="flex justify-between font-medium text-zinc-300">
                  <span className="flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5 text-zinc-500" />
                    Codebase Metrics Scan (Parallel)
                  </span>
                  <span className="font-mono text-zinc-400">{metricsTime.toFixed(2)}s</span>
                </div>
                <div className="w-full bg-zinc-950 h-2.5 rounded-full overflow-hidden border border-zinc-900/60">
                  <div className="bg-emerald-500 h-full rounded-full transition-all duration-500" style={{ width: getPctWidth(metricsTime) }} />
                </div>
              </div>

              {/* Parallel Architecture */}
              <div className="space-y-1.5">
                <div className="flex justify-between font-medium text-zinc-300">
                  <span className="flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-zinc-500" />
                    Dependency Graph Analyzer (Parallel)
                  </span>
                  <span className="font-mono text-zinc-400">{archTime.toFixed(2)}s</span>
                </div>
                <div className="w-full bg-zinc-950 h-2.5 rounded-full overflow-hidden border border-zinc-900/60">
                  <div className="bg-teal-500 h-full rounded-full transition-all duration-500" style={{ width: getPctWidth(archTime) }} />
                </div>
              </div>

              {/* Parallel Security */}
              <div className="space-y-1.5">
                <div className="flex justify-between font-medium text-zinc-300">
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-zinc-500" />
                    Security Vulnerability Audit (Parallel)
                  </span>
                  <span className="font-mono text-zinc-400">{secTime.toFixed(2)}s</span>
                </div>
                <div className="w-full bg-zinc-950 h-2.5 rounded-full overflow-hidden border border-zinc-900/60">
                  <div className="bg-amber-500 h-full rounded-full transition-all duration-500" style={{ width: getPctWidth(secTime) }} />
                </div>
              </div>

              {/* Chunker */}
              <div className="space-y-1.5">
                <div className="flex justify-between font-medium text-zinc-300">
                  <span className="flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-zinc-500" />
                    AST Chunker & Cache Matcher
                  </span>
                  <span className="font-mono text-zinc-400">{chunkTime.toFixed(2)}s</span>
                </div>
                <div className="w-full bg-zinc-950 h-2.5 rounded-full overflow-hidden border border-zinc-900/60">
                  <div className="bg-orange-500 h-full rounded-full transition-all duration-500" style={{ width: getPctWidth(chunkTime) }} />
                </div>
              </div>

              {/* Embedding */}
              <div className="space-y-1.5">
                <div className="flex justify-between font-medium text-zinc-300">
                  <span className="flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-zinc-500" />
                    Local Embedding Vectorizer (FastEmbed ONNX)
                  </span>
                  <span className="font-mono text-zinc-400">{embedTime.toFixed(2)}s</span>
                </div>
                <div className="w-full bg-zinc-950 h-2.5 rounded-full overflow-hidden border border-zinc-900/60">
                  <div className="bg-violet-500 h-full rounded-full transition-all duration-500" style={{ width: getPctWidth(embedTime) }} />
                </div>
              </div>

              {/* pgvector Write */}
              <div className="space-y-1.5">
                <div className="flex justify-between font-medium text-zinc-300">
                  <span className="flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-zinc-500" />
                    Supabase pgvector Bulk Store (Batch size = 500)
                  </span>
                  <span className="font-mono text-zinc-400">{vectorTime.toFixed(2)}s</span>
                </div>
                <div className="w-full bg-zinc-950 h-2.5 rounded-full overflow-hidden border border-zinc-900/60">
                  <div className="bg-pink-500 h-full rounded-full transition-all duration-500" style={{ width: getPctWidth(vectorTime) }} />
                </div>
              </div>
            </div>
          </div>

          {/* Cache Analytics & Statistics */}
          <div className="space-y-6">
            
            {/* Cache Efficiency Ring */}
            <div className="bg-[#0c0f1e]/40 border border-zinc-900 rounded-2xl p-6 shadow-xl flex flex-col items-center justify-center text-center space-y-4">
              <h3 className="text-sm font-bold text-white tracking-wide uppercase w-full text-left border-b border-zinc-900 pb-3">
                File Cache Efficiency
              </h3>

              <div className="relative w-36 h-36 flex items-center justify-center">
                {/* SVG Circular Ring */}
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" className="stroke-zinc-900 fill-none" strokeWidth="6" />
                  <circle 
                    cx="50" 
                    cy="50" 
                    r="40" 
                    className="stroke-brand-500 fill-none transition-all duration-1000" 
                    strokeWidth="6" 
                    strokeDasharray="251.2" 
                    strokeDashoffset={251.2 - (fileCacheEfficiency / 100) * 251.2}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute text-center space-y-0.5">
                  <p className="text-2xl font-black text-white">{fileCacheEfficiency.toFixed(1)}%</p>
                  <p className="text-[9px] text-zinc-500 uppercase tracking-wider font-semibold">Reuse Ratio</p>
                </div>
              </div>

              <div className="w-full text-left text-xs grid grid-cols-2 gap-4 border-t border-zinc-900/60 pt-3">
                <div>
                  <span className="text-[10px] text-zinc-500 uppercase font-semibold">Reused files</span>
                  <p className="font-bold text-brand-300 mt-0.5">{fileCacheHits}</p>
                </div>
                <div>
                  <span className="text-[10px] text-zinc-500 uppercase font-semibold">Re-embedded</span>
                  <p className="font-bold text-indigo-400 mt-0.5">{fileCacheMisses}</p>
                </div>
              </div>
            </div>

            {/* Ingestion Pipeline stats */}
            <div className="bg-[#0c0f1e]/40 border border-zinc-900 rounded-2xl p-6 shadow-xl space-y-4">
              <h3 className="text-sm font-bold text-white tracking-wide uppercase border-b border-zinc-900 pb-3">
                Pipeline Diagnostics
              </h3>

              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between py-1 border-b border-zinc-900/40">
                  <span className="text-zinc-400">Total Chunks Index</span>
                  <span className="font-mono text-white font-semibold">{chunksCount}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-zinc-900/40">
                  <span className="text-zinc-400">Average Chunk Size</span>
                  <span className="font-mono text-white font-semibold">
                    {Math.round(diagnostics.average_chunk_size || 0)} chars
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-zinc-900/40">
                  <span className="text-zinc-400">Largest Chunk Size</span>
                  <span className="font-mono text-white font-semibold">
                    {diagnostics.largest_chunk || 0} chars
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-zinc-900/40">
                  <span className="text-zinc-400">Embedding Requests</span>
                  <span className="font-mono text-white font-semibold">
                    {diagnostics.embedding_requests || 0}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-zinc-400">pgvector Batch inserts</span>
                  <span className="font-mono text-white font-semibold">
                    {diagnostics.pgvector_inserts || 0}
                  </span>
                </div>
              </div>
            </div>

          </div>

        </div>

      </main>

    </div>
  );
}
