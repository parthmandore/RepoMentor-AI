'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, ArrowRight, Loader2, ShieldAlert, BookOpen, CheckCircle2,
  FileText, Database, Server, RefreshCw, Search, Shield, Info,
  Layers, Sparkles, Terminal, FileCode, Check, X
} from 'lucide-react';

import Header from '../../../Header';
import { PageLayoutSkeleton } from '../../../components/Skeletons';
import EmptyState from '../../../components/EmptyState';

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
  wiki_data?: Record<string, { items: string[]; reason_if_empty: string }>;
}

export default function KnowledgeBasePage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  const [repo, setRepo] = useState<any>(null);
  const [summary, setSummary] = useState<KnowledgeSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const fetchRepoAndSummary = useCallback(async () => {
    try {
      const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
      if (!repoRes.ok) throw new Error('Repository detail not found.');
      const repoData = await repoRes.json();
      setRepo(repoData);

      const summaryRes = await fetch(`${apiUrl}/repositories/${repoId}/knowledge/summary`);
      if (summaryRes.ok) {
        setSummary(await summaryRes.json());
      }
      setIsLoading(false);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch details');
      setIsLoading(false);
    }
  }, [apiUrl, repoId]);

  useEffect(() => {
    fetchRepoAndSummary();
  }, [fetchRepoAndSummary]);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setHasSearched(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/knowledge/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery.trim(), limit: 6 })
      });

      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  if (isLoading) {
    return <PageLayoutSkeleton title="Accessing Knowledge Base Vector Store..." />;
  }

  if (error || !repo) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4 font-sans">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-8 rounded-lg shadow-report text-center space-y-4">
          <ShieldAlert className="w-8 h-8 text-bad mx-auto" />
          <h2 className="font-serif text-xl font-bold text-textPrimary">Knowledge Index Unavailable</h2>
          <p className="text-xs text-textSecondary font-mono">{error || 'Data could not be compiled.'}</p>
          <button onClick={() => router.push(`/repositories/${repoId}`)} className="py-2 px-4 rounded bg-bgTertiary text-xs font-mono font-bold">
            Return to Overview
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans transition-colors duration-200">
      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="knowledge" 
      />

      <main className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-10 pt-[76px] pb-16 space-y-8 flex-grow">
        
        {/* HERO SECTION */}
        <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="section-header px-2 py-0.5 rounded bg-bgTertiary border border-borderPrimary text-[10px]">
                  SECTION 07 // VECTOR KNOWLEDGE INDEX
                </span>
                <span className="text-xs font-mono text-textMuted">•</span>
                <span className="text-xs font-mono text-textSecondary">{summary?.indexed_files || 0} files indexed</span>
              </div>
              <h1 className="font-serif text-3xl sm:text-4xl font-bold text-textPrimary">
                Repository Semantic Index
              </h1>
              <p className="text-xs sm:text-sm text-textSecondary max-w-2xl font-sans leading-relaxed">
                Pre-computed embeddings and chunked source facts used to ground the AI Repository Mentor in verifiable evidence.
              </p>
            </div>

            {/* Index Status Stamp */}
            <div className="shrink-0 p-4 sm:p-6 rounded border-2 border-borderStrong bg-bgPrimary text-center min-w-[160px] shadow-report">
              <span className="section-header text-[9px] block">VECTOR CHUNKS</span>
              <div className="inspection-stamp text-4xl sm:text-5xl font-black text-textPrimary mt-1">
                {summary?.total_chunks || 0}
              </div>
              <span className="text-[10px] font-mono text-good font-bold block mt-0.5">
                ● COMPILED & ACTIVE
              </span>
            </div>
          </div>

          {/* Metrics Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6 mt-6 border-t border-borderPrimary text-xs font-mono">
            <div className="p-3 bg-bgPrimary border border-borderPrimary rounded">
              <span className="text-[10px] text-textMuted uppercase block">INDEXED SOURCE FILES</span>
              <strong className="text-base text-textPrimary">{summary?.indexed_files || 0}</strong>
            </div>
            <div className="p-3 bg-bgPrimary border border-borderPrimary rounded">
              <span className="text-[10px] text-textMuted uppercase block">CODE CHUNKS</span>
              <strong className="text-base text-textPrimary">{summary?.code_chunks || 0}</strong>
            </div>
            <div className="p-3 bg-bgPrimary border border-borderPrimary rounded">
              <span className="text-[10px] text-textMuted uppercase block">EMBEDDING ENGINE</span>
              <strong className="text-base text-textPrimary font-mono">bge-small-en</strong>
            </div>
            <div className="p-3 bg-bgPrimary border border-borderPrimary rounded">
              <span className="text-[10px] text-textMuted uppercase block">INDEX STATUS</span>
              <strong className="text-base text-good font-bold">READY FOR RAG</strong>
            </div>
          </div>
        </section>

        {/* SEMANTIC EVIDENCE SEARCH */}
        <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report space-y-6">
          <div className="border-b border-borderPrimary pb-4 space-y-1">
            <span className="section-header">GROUNDED EVIDENCE RETRIEVER</span>
            <h2 className="font-serif text-xl font-bold text-textPrimary">
              Search Codebase Vectors
            </h2>
            <p className="text-xs text-textSecondary font-sans">
              Perform semantic vector retrieval against parsed function chunks and class definitions.
            </p>
          </div>

          {/* Search Bar Form */}
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-grow">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-textMuted" />
              <input
                type="text"
                placeholder="Query vector index (e.g. 'url encoding algorithm', 'database transaction rollback')..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-bgPrimary border border-borderPrimary rounded pl-10 pr-4 py-2.5 text-xs sm:text-sm font-mono text-textPrimary focus:outline-none focus:border-signal"
              />
            </div>
            <button
              type="submit"
              disabled={isSearching || !searchQuery.trim()}
              className="px-5 py-2.5 bg-signal hover:bg-signal-hover disabled:opacity-40 text-white rounded font-mono font-bold text-xs flex items-center gap-1.5 transition-colors shadow-sm"
            >
              {isSearching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
              <span>Retrieve Chunks</span>
            </button>
          </form>

          {/* Search Results */}
          {hasSearched && (
            <div className="space-y-4 pt-2">
              <span className="section-header block">
                RETRIEVED EVIDENCE CHUNKS ({searchResults.length})
              </span>

              {searchResults.length === 0 ? (
                <div className="p-8 text-center text-xs font-mono text-textMuted bg-bgPrimary border border-borderPrimary rounded">
                  No matching vector chunks met the similarity threshold for "{searchQuery}".
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {searchResults.map((res, i) => (
                    <div key={i} className="p-4 bg-bgPrimary border border-borderPrimary rounded space-y-2 font-mono text-xs shadow-sm">
                      <div className="flex items-center justify-between border-b border-borderPrimary pb-2">
                        <span className="font-bold text-textPrimary truncate max-w-[240px]" title={res.metadata?.source}>
                          {res.metadata?.source?.split('/').pop() || 'chunk'}
                        </span>
                        <span className="text-[10px] text-good font-bold">
                          {res.distance !== undefined ? `${Math.round((1 - res.distance) * 100)}% Match` : 'Evidence'}
                        </span>
                      </div>
                      <span className="text-[10px] text-textMuted block truncate">
                        {res.metadata?.source} {res.metadata?.line_start && `(Line ${res.metadata.line_start})`}
                      </span>
                      <pre className="p-3 bg-bgTertiary rounded border border-borderPrimary text-[11px] text-textPrimary overflow-x-auto leading-relaxed max-h-36 whitespace-pre">
                        <code>{res.document}</code>
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

      </main>
    </div>
  );
}
