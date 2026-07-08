'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, RefreshCw, Cpu, Database, HardDrive, ShieldAlert,
  CheckCircle2, AlertTriangle, Play, Loader2, Server, GitBranch, ListTodo, Activity
} from 'lucide-react';

interface DiagnosticInfo {
  status: string;
  services: {
    database: string;
    chromadb: string;
    ollama: string;
    git: string;
  };
  ollama_models: string[];
  queue: {
    queued_count: number;
    active_count: number;
    active_tasks: Array<{
      id: string;
      url: string;
      status: string;
      status_message: string;
      elapsed_seconds: number;
    }>;
  };
  system: {
    total_mb?: number;
    used_mb?: number;
    percent?: number;
    cpu_percent?: number;
    status?: string;
  };
}

export default function DiagnosticsPage() {
  const router = useRouter();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';

  const [diagnostics, setDiagnostics] = useState<DiagnosticInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchDiagnostics = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch(`${apiUrl}/diagnostics`);
      if (!res.ok) throw new Error('Failed to fetch diagnostics.');
      const data = await res.json();
      setDiagnostics(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Diagnostics service offline');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
    const interval = setInterval(fetchDiagnostics, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-darkbg-950 text-gray-100 font-sans">
        <div className="text-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 mx-auto" />
          <p className="text-sm text-gray-400">Querying platform status...</p>
        </div>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    if (status === 'online' || status === 'available' || status === 'healthy') {
      return (
        <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 font-bold uppercase rounded border border-emerald-500/20 bg-emerald-500/5 text-emerald-400">
          <CheckCircle2 className="w-3 h-3" /> Online
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 font-bold uppercase rounded border border-rose-500/20 bg-rose-500/5 text-rose-400">
        <ShieldAlert className="w-3 h-3" /> Offline
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-darkbg-950 text-gray-100 flex flex-col font-sans">
      <div className="max-w-5xl w-full mx-auto px-4 py-8 space-y-8 flex-grow">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 border-b border-gray-900 pb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push('/')} className="p-2 bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-xl text-gray-400 hover:text-white transition-all" title="Back to home">
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
                <Server className="w-6 h-6 text-brand-400" /> Internal System Diagnostics
              </h1>
              <p className="text-xs text-gray-505 mt-0.5">Developer panel to monitor backend services, database status, and active job queue.</p>
            </div>
          </div>
          <button
            disabled={isRefreshing}
            onClick={fetchDiagnostics}
            className="px-4 py-2 bg-gray-900 border border-gray-800 hover:border-gray-700 text-xs font-semibold rounded-xl flex items-center gap-2 hover:text-white transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-brand-400' : 'text-gray-405'}`} />
            Refresh Status
          </button>
        </div>

        {error && (
          <div className="p-4 bg-rose-500/5 border border-rose-500/10 rounded-xl flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs">
              <span className="font-bold text-rose-400 block mb-0.5">Diagnostics Error</span>
              <p className="text-gray-400">{error}. Ensure the backend service container is running on port 8080.</p>
            </div>
          </div>
        )}

        {diagnostics && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Core Services Card */}
            <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 space-y-6 md:col-span-2">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-brand-400" /> Core Dependencies Status
              </h3>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 bg-darkbg-950/40 border border-gray-900 rounded-xl flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <Database className="w-5 h-5 text-sky-400" />
                    <div className="text-xs">
                      <span className="font-bold text-white block">PostgreSQL</span>
                      <span className="text-[10px] text-gray-500">Relational DB</span>
                    </div>
                  </div>
                  {getStatusBadge(diagnostics.services.database)}
                </div>

                <div className="p-4 bg-darkbg-950/40 border border-gray-900 rounded-xl flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <HardDrive className="w-5 h-5 text-violet-400" />
                    <div className="text-xs">
                      <span className="font-bold text-white block">pgvector (Supabase)</span>
                      <span className="text-[10px] text-gray-500">Vector Storage</span>
                    </div>
                  </div>
                  {getStatusBadge(diagnostics.services.chromadb)}
                </div>

                <div className="p-4 bg-darkbg-950/40 border border-gray-900 rounded-xl flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <Server className="w-5 h-5 text-indigo-400" />
                    <div className="text-xs">
                      <span className="font-bold text-white block">Groq LLM</span>
                      <span className="text-[10px] text-gray-500">Cloud LPU inference</span>
                    </div>
                  </div>
                  {getStatusBadge(diagnostics.services.ollama)}
                </div>

                <div className="p-4 bg-darkbg-950/40 border border-gray-900 rounded-xl flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <GitBranch className="w-5 h-5 text-emerald-400" />
                    <div className="text-xs">
                      <span className="font-bold text-white block">Git CLI</span>
                      <span className="text-[10px] text-gray-500">Cloning runtime</span>
                    </div>
                  </div>
                  {getStatusBadge(diagnostics.services.git)}
                </div>
              </div>

              {/* Ollama Models Sub-panel */}
              <div className="pt-4 border-t border-gray-900/60 space-y-2 text-xs">
                <span className="text-[10px] text-gray-500 uppercase font-bold block">Active AI Models</span>
                <div className="flex flex-wrap gap-2">
                  {diagnostics.ollama_models.map(model => (
                    <span key={model} className="px-2.5 py-1 bg-darkbg-950 border border-gray-900 font-mono text-[10px] rounded-lg text-gray-300">
                      {model}
                    </span>
                  ))}
                  {diagnostics.ollama_models.length === 0 && (
                    <span className="text-gray-650 italic">No active AI models registered. Check your API configuration.</span>
                  )}
                </div>
              </div>
            </div>

            {/* System Resources Card */}
            <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 space-y-6">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-emerald-400" /> Container Resources
              </h3>

              {diagnostics.system.total_mb ? (
                <div className="space-y-4 text-xs">
                  <div className="space-y-1.5">
                    <div className="flex justify-between font-mono">
                      <span className="text-gray-500">Memory Usage:</span>
                      <span className="font-bold text-white">{diagnostics.system.used_mb}MB / {diagnostics.system.total_mb}MB</span>
                    </div>
                    <div className="w-full bg-gray-950 h-1.5 rounded-full overflow-hidden">
                      <div className="bg-brand-500 h-full" style={{ width: `${diagnostics.system.percent}%` }} />
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex justify-between font-mono">
                      <span className="text-gray-500">CPU Usage:</span>
                      <span className="font-bold text-white">{diagnostics.system.cpu_percent?.toFixed(1) || '0.0'}%</span>
                    </div>
                    <div className="w-full bg-gray-950 h-1.5 rounded-full overflow-hidden">
                      <div className="bg-emerald-500 h-full" style={{ width: `${diagnostics.system.cpu_percent || 0}%` }} />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-xs text-gray-600 italic">Resource tracking stats not loaded.</div>
              )}
            </div>

            {/* Job Queue Status Card */}
            <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 space-y-6 md:col-span-3">
              <div className="flex justify-between items-center pb-3 border-b border-gray-900">
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                  <ListTodo className="w-4 h-4 text-indigo-400" /> Ingestion Queue Length
                </h3>
                <span className="font-mono text-xs text-brand-400 font-bold">{diagnostics.queue.queued_count} queued, {diagnostics.queue.active_count} processing</span>
              </div>

              <div className="space-y-3 font-mono text-[11px] leading-relaxed max-h-[300px] overflow-y-auto">
                {diagnostics.queue.active_tasks.map(task => (
                  <div key={task.id} className="p-3 bg-darkbg-950 border border-gray-900 rounded-xl space-y-1">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-white truncate max-w-[250px] font-sans font-semibold" title={task.url}>{task.url.split('/').pop()}</span>
                      <span className="px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 text-[9px] font-bold uppercase tracking-wider border border-brand-500/20">{task.status}</span>
                    </div>
                    <p className="text-gray-500 font-sans">{task.status_message}</p>
                    <span className="text-gray-600 text-[10px] block pt-1 border-t border-gray-900/40 mt-1">Elapsed Time: {task.elapsed_seconds}s</span>
                  </div>
                ))}
                {diagnostics.queue.active_tasks.length === 0 && (
                  <div className="text-center py-10 font-sans text-xs text-gray-650 italic">
                    ✓ All pipelines are idle. No repositories currently processing.
                  </div>
                )}
              </div>
            </div>

          </div>
        )}

      </div>
      
      <footer className="w-full text-center py-6 text-xs text-slate-500 dark:text-zinc-500 border-t border-slate-200 dark:border-zinc-900/40 mt-8 font-mono">
        Repository Mentor AI &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
}
