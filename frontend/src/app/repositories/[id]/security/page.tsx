'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  ShieldAlert, Shield, ShieldCheck, Bug, FileText, Lock, 
  ChevronRight, RefreshCw, Sparkles, Copy, Check, Info,
  AlertCircle, ChevronDown, ChevronUp, FileCode, CheckCircle2
} from 'lucide-react';

import Header from '../../../Header';
import { PageLayoutSkeleton } from '../../../components/Skeletons';
import EmptyState from '../../../components/EmptyState';

interface DependencyStats {
  total_dependencies: number;
  safe_dependencies: number;
  vulnerable_dependencies: number;
  most_severe_vulnerability: string;
  total_known_cves: number;
}

interface ScanStats {
  files_scanned: number;
  files_skipped: number;
  dependencies_parsed: number;
  secrets_checked: number;
  issues_found: number;
}

interface SecuritySummary {
  score: number;
  grade: string;
  severity_counts: Record<string, number>;
  category_counts: Record<string, number>;
  badges: string[];
  dependency_stats: DependencyStats;
  scan_stats: ScanStats;
}

interface SecurityIssue {
  id: string;
  file_path: string;
  line_number: number | null;
  severity: string;
  category: string;
  title: string;
  evidence: string;
  snippet: string | null;
  reason: string;
  recommendation: string;
  created_at: string;
}

interface IssuesResponse {
  total: number;
  skip: number;
  limit: number;
  issues: SecurityIssue[];
}

export default function SecurityAuditPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  const [repo, setRepo] = useState<any>(null);
  const [summary, setSummary] = useState<SecuritySummary | null>(null);
  const [issuesData, setIssuesData] = useState<IssuesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Interactivity
  const [selectedSeverityFilter, setSelectedSeverityFilter] = useState('All');
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState('All');
  const [searchFileQuery, setSearchFileQuery] = useState('');
  const [expandedIssueId, setExpandedIssueId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
      if (!repoRes.ok) throw new Error('Repository detail not found.');
      setRepo(await repoRes.json());

      const summaryRes = await fetch(`${apiUrl}/repositories/${repoId}/security/summary`);
      if (!summaryRes.ok) throw new Error('Security summary not found.');
      setSummary(await summaryRes.json());

      const issuesRes = await fetch(`${apiUrl}/repositories/${repoId}/security/issues?limit=100`);
      if (issuesRes.ok) {
        setIssuesData(await issuesRes.json());
      }
      setIsLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch security report.');
      setIsLoading(false);
    }
  }, [apiUrl, repoId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Filter issues
  const filteredIssues = useMemo(() => {
    if (!issuesData?.issues) return [];
    return issuesData.issues.filter(issue => {
      const matchesSeverity = selectedSeverityFilter === 'All' || issue.severity.toLowerCase() === selectedSeverityFilter.toLowerCase();
      const matchesCategory = selectedCategoryFilter === 'All' || issue.category.toLowerCase() === selectedCategoryFilter.toLowerCase();
      const matchesQuery = !searchFileQuery || issue.file_path.toLowerCase().includes(searchFileQuery.toLowerCase()) || issue.title.toLowerCase().includes(searchFileQuery.toLowerCase());
      return matchesSeverity && matchesCategory && matchesQuery;
    });
  }, [issuesData, selectedSeverityFilter, selectedCategoryFilter, searchFileQuery]);

  const getSeverityStyle = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'high':
        return 'text-bad bg-bad-bg border-bad-border';
      case 'medium':
        return 'text-warn bg-warn-bg border-warn-border';
      case 'low':
      default:
        return 'text-good bg-good-bg border-good-border';
    }
  };

  if (isLoading) {
    return <PageLayoutSkeleton title="Running Security Leak Audit..." />;
  }

  if (error || !summary) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-8 rounded-lg shadow-report text-center space-y-4">
          <ShieldAlert className="w-8 h-8 text-bad mx-auto" />
          <h2 className="font-serif text-xl font-bold text-textPrimary">Security Audit Unavailable</h2>
          <p className="text-xs text-textSecondary font-mono">{error || 'Data could not be compiled.'}</p>
          <button onClick={() => router.push('/')} className="py-2 px-4 rounded bg-bgTertiary text-xs font-mono font-bold">
            Return Home
          </button>
        </div>
      </div>
    );
  }

  const allIssues = issuesData?.issues || [];

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans transition-colors duration-200">
      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="security" 
      />

      <main className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-10 pt-[76px] pb-16 space-y-8 flex-grow">
        
        {/* REPORT HEADER / SECURITY HERO */}
        <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="section-header px-2 py-0.5 rounded bg-bgTertiary border border-borderPrimary text-[10px]">
                  SECTION 04 // VULNERABILITY & LEAK AUDIT
                </span>
                <span className="text-xs font-mono text-textMuted">•</span>
                <span className="text-xs font-mono text-textSecondary">{summary.scan_stats.files_scanned} files inspected</span>
              </div>
              <h1 className="font-serif text-3xl sm:text-4xl font-bold text-textPrimary">
                Security Profile & Leak Review
              </h1>
              <p className="text-xs sm:text-sm text-textSecondary max-w-2xl font-sans leading-relaxed">
                Automated static scan for exposed credentials, injection vulnerabilities, insecure cryptographic primitives, and unpatched third-party CVEs.
              </p>
            </div>

            {/* Score & Stamp */}
            <div className="flex items-center gap-4 shrink-0">
              <div className="p-4 sm:p-6 rounded border-2 border-borderStrong bg-bgPrimary text-center min-w-[160px] shadow-report">
                <span className="section-header text-[9px] block">SECURITY SCORE</span>
                <div className="inspection-stamp text-5xl font-black text-textPrimary mt-1">
                  {summary.score}
                </div>
                <span className="text-[10px] font-mono font-bold text-textSecondary block mt-0.5">
                  GRADE {summary.grade}
                </span>
              </div>
            </div>
          </div>

          {/* Scan Stats Metrics Strip (NO fake data) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6 mt-6 border-t border-borderPrimary text-xs font-mono">
            <div className="p-3 bg-bgPrimary border border-borderPrimary rounded">
              <span className="text-[10px] text-textMuted uppercase block">FILES INSPECTED</span>
              <strong className="text-lg text-textPrimary">{summary.scan_stats.files_scanned}</strong>
            </div>
            <div className="p-3 bg-bgPrimary border border-borderPrimary rounded">
              <span className="text-[10px] text-textMuted uppercase block">SECRETS CHECKED</span>
              <strong className="text-lg text-textPrimary">{summary.scan_stats.secrets_checked.toLocaleString()}</strong>
            </div>
            <div className="p-3 bg-bgPrimary border border-borderPrimary rounded">
              <span className="text-[10px] text-textMuted uppercase block">DEPENDENCIES PARSED</span>
              <strong className="text-lg text-textPrimary">{summary.scan_stats.dependencies_parsed}</strong>
            </div>
            <div className="p-3 bg-bgPrimary border border-borderPrimary rounded">
              <span className="text-[10px] text-textMuted uppercase block">TOTAL FINDINGS</span>
              <strong className={`text-lg ${allIssues.length > 0 ? 'text-bad' : 'text-good'}`}>
                {allIssues.length}
              </strong>
            </div>
          </div>
        </section>

        {/* FINDINGS LIST OR EMPTY STATE */}
        <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-borderPrimary pb-4">
            <div>
              <span className="section-header">SECURITY AUDIT LOG</span>
              <h2 className="font-serif text-xl font-bold text-textPrimary mt-0.5">
                Identified Vulnerabilities ({allIssues.length})
              </h2>
            </div>

            {/* Filter controls */}
            {allIssues.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                <input
                  type="text"
                  placeholder="Filter by file path..."
                  value={searchFileQuery}
                  onChange={(e) => setSearchFileQuery(e.target.value)}
                  className="px-3 py-1.5 bg-bgPrimary border border-borderPrimary rounded text-xs text-textPrimary focus:outline-none focus:border-signal w-40 sm:w-52"
                />

                <select
                  value={selectedSeverityFilter}
                  onChange={(e) => setSelectedSeverityFilter(e.target.value)}
                  className="px-2.5 py-1.5 bg-bgPrimary border border-borderPrimary rounded text-xs text-textPrimary focus:outline-none focus:border-signal"
                >
                  <option value="All">All Severities</option>
                  <option value="Critical">Critical</option>
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                </select>
              </div>
            )}
          </div>

          {allIssues.length === 0 ? (
            /* DESIGNED EMPTY STATE: Clean security audit */
            <EmptyState
              icon={ShieldCheck}
              title="No Security Vulnerabilities Detected"
              description="Static AST analysis and regex credential scanners found zero leaked API keys, injection points, or deprecated cryptographic patterns."
              badge="AUDIT CLEAR"
              variant="success"
            />
          ) : filteredIssues.length === 0 ? (
            <div className="p-8 text-center text-xs font-mono text-textMuted bg-bgPrimary border border-borderPrimary rounded">
              No security issues match your active filter criteria.
            </div>
          ) : (
            /* ISSUE ROWS (Severity, file, line, why it matters, how to fix expander) */
            <div className="divide-y divide-borderPrimary">
              {filteredIssues.map((issue) => {
                const isExpanded = expandedIssueId === issue.id;
                return (
                  <div key={issue.id} className="py-4 first:pt-0 last:pb-0 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase border ${getSeverityStyle(issue.severity)}`}>
                            {issue.severity}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-bgTertiary border border-borderPrimary text-[9px] font-mono text-textSecondary uppercase">
                            {issue.category}
                          </span>
                          <span className="text-xs font-mono text-textPrimary font-semibold">
                            {issue.file_path}
                            {issue.line_number && <span className="text-textMuted font-normal">:{issue.line_number}</span>}
                          </span>
                        </div>

                        <h3 className="font-serif text-base font-bold text-textPrimary pt-0.5">
                          {issue.title}
                        </h3>

                        <p className="text-xs text-textSecondary font-sans leading-relaxed">
                          <strong>Why it matters:</strong> {issue.reason || 'This pattern presents security exploitation or unauthorized access risks.'}
                        </p>
                      </div>

                      <button
                        onClick={() => setExpandedIssueId(isExpanded ? null : issue.id)}
                        className="px-3 py-1.5 rounded bg-bgTertiary hover:bg-borderPrimary border border-borderPrimary text-textPrimary text-xs font-mono flex items-center gap-1.5 shrink-0 transition-colors"
                      >
                        <span>{isExpanded ? 'Hide Fix' : 'How to Fix'}</span>
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>
                    </div>

                    {/* Collapsible How-To-Fix Expander */}
                    {isExpanded && (
                      <div className="mt-3 p-4 bg-bgPrimary border border-borderPrimary rounded space-y-3 text-xs font-mono animate-fade-in">
                        <div className="space-y-1">
                          <span className="text-[10px] text-textMuted uppercase font-bold block">REMEDIATION GUIDANCE:</span>
                          <p className="text-textPrimary leading-relaxed font-sans">
                            {issue.recommendation || 'Refactor this code to use environment variables or parameterized queries.'}
                          </p>
                        </div>

                        {issue.snippet && (
                          <div className="space-y-1 pt-2">
                            <span className="text-[10px] text-textMuted uppercase font-bold block">CODE CONTEXT:</span>
                            <pre className="p-3 bg-bgTertiary border border-borderPrimary rounded text-[11px] text-bad overflow-x-auto whitespace-pre">
                              <code>{issue.snippet}</code>
                            </pre>
                          </div>
                        )}

                        <div className="pt-2 flex justify-end">
                          <button
                            onClick={() => {
                              const prompt = `Explain how to fix the security issue "${issue.title}" in file \`${issue.file_path}\`. Show exact refactored code.`;
                              router.push(`/repositories/${repoId}/mentor?q=${encodeURIComponent(prompt)}`);
                            }}
                            className="px-3 py-1.5 bg-signal text-white rounded text-[11px] font-bold flex items-center gap-1 hover:bg-signal-hover transition-colors"
                          >
                            <Sparkles className="w-3 h-3" />
                            <span>Ask Mentor for Patch</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

      </main>
    </div>
  );
}
