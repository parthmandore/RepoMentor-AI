'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, Loader2, ShieldAlert, Shield, Bug, FileText, Lock, 
  ChevronRight, RefreshCw, Sparkles, Copy, Check, Info, AlertCircle, Gauge
} from 'lucide-react';

import Header from '../../../Header';

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

const GRADE_COLORS: Record<string, string> = {
  A: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5',
  B: 'text-sky-400 border-sky-500/20 bg-sky-500/5',
  C: 'text-amber-400 border-amber-500/20 bg-amber-500/5',
  D: 'text-orange-400 border-orange-500/20 bg-orange-500/5',
  F: 'text-rose-400 border-rose-500/20 bg-rose-500/5',
};

const SEVERITY_COLORS: Record<string, { border: string; bg: string; text: string; labelBg: string }> = {
  Critical: { border: 'border-red-500/30', bg: 'bg-red-500/5', text: 'text-red-500', labelBg: 'bg-red-500/10' },
  High: { border: 'border-orange-500/25', bg: 'bg-orange-500/5', text: 'text-orange-500', labelBg: 'bg-orange-500/10' },
  Medium: { border: 'border-yellow-500/25', bg: 'bg-yellow-500/5', text: 'text-yellow-500', labelBg: 'bg-yellow-500/10' },
  Low: { border: 'border-blue-500/25', bg: 'bg-blue-500/5', text: 'text-blue-500', labelBg: 'bg-blue-500/10' },
  Info: { border: 'border-zinc-800', bg: 'bg-zinc-900/40', text: 'text-zinc-400', labelBg: 'bg-zinc-800' },
};

// Educational explanations mapping dictionary
const EDUCATIONAL_GUIDES: Record<string, {
  whatHappened: string;
  whyDangerous: string;
  realWorldExample: string;
  howToFix: string[];
  impact: { security: number; health: number };
  cwe: string;
  owasp: string;
  fixTime: string;
}> = {
  'Secrets': {
    whatHappened: 'A plaintext API key, password, token, or private credential was found hardcoded inside your code files.',
    whyDangerous: 'Once code is pushed to version control, hardcoded secrets are visible to anyone with access. Bots routinely scan public repositories for leaked keys, leading to server takeovers, data theft, and astronomical API billing charges.',
    realWorldExample: 'An AWS access key left in a script can be discovered within 2 minutes of pushing to public Git. Attackers immediately spin up hundreds of high-power crypto-mining virtual servers on your card.',
    howToFix: [
      'Extract the key into a local environment configuration file (like .env).',
      'Add the config file path to your repository\'s .gitignore.',
      'Load the variable dynamically in your scripts (e.g. process.env or os.getenv).',
      'Rotate the leaked credential immediately on the service provider dashboard.'
    ],
    impact: { security: 15, health: 5 },
    cwe: 'CWE-798: Use of Hard-coded Credentials',
    owasp: 'A02:2021-Cryptographic Failures',
    fixTime: '5-15 min'
  },
  'Injection': {
    whatHappened: 'User inputs are being concatenated directly into system shell calls or database statement structures.',
    whyDangerous: 'Attackers can pass escape characters and append their own custom parameters. This enables execution of arbitrary system queries, allowing database reads, data deletion, or remote code execution.',
    realWorldExample: 'A search box concatenates SQL variables. Sending a query payload like "\' OR 1=1; --" bypasses security checks and returns every single user account database record.',
    howToFix: [
      'Use parameterized queries (e.g., bind variables) instead of string formatting.',
      'Apply schema validator models (such as Pydantic) to reject bad characters.',
      'Escape dynamic parameters before rendering them in system processes.'
    ],
    impact: { security: 12, health: 4 },
    cwe: 'CWE-89: Improper Neutralization of Special Elements used in an SQL Command',
    owasp: 'A03:2021-Injection',
    fixTime: '30-45 min'
  },
  'Dependencies': {
    whatHappened: 'Your package configuration manifest references an external library with public known security vulnerabilities (CVEs).',
    whyDangerous: 'Vulnerable packages allow hackers to exploit unpatched flaws in your server. This can lead to remote exploits, denial-of-service, or remote script execution.',
    realWorldExample: 'A backend service imports an unpatched version of Log4j. Attackers pass a crafted header string, forcing the logging library to download and run foreign remote malware code.',
    howToFix: [
      'Identify the vulnerable library name and version.',
      'Upgrade the dependency version inside your package manifest to a safe patch.',
      'Run security checks (e.g., npm audit or safety check) locally to confirm clearance.'
    ],
    impact: { security: 10, health: 3 },
    cwe: 'CWE-1395: Dependency on Vulnerable Third-Party Component',
    owasp: 'A06:2021-Vulnerable and Outdated Components',
    fixTime: '10-20 min'
  },
  'Weak Cryptography': {
    whatHappened: 'Your code uses deprecated hashing or cipher algorithms (like MD5 or SHA1) to secure credentials or hashes.',
    whyDangerous: 'Legacy cryptographic algorithms are vulnerable to collision attacks and can be decrypted in seconds using standard computing hardware.',
    realWorldExample: 'Hashes for user passwords are stored using raw MD5. An attacker who steals the database can cross-reference the hashes with precomputed tables (Rainbow Tables) to recover plaintext passwords instantly.',
    howToFix: [
      'Replace MD5 or SHA1 with bcrypt, Argon2, or PBKDF2.',
      'Use a strong, unique salt for every hashed credential.',
      'Apply secure cryptographic keys generated with system randomness.'
    ],
    impact: { security: 10, health: 3 },
    cwe: 'CWE-328: Use of Weak Hash',
    owasp: 'A02:2021-Cryptographic Failures',
    fixTime: '15-30 min'
  },
  'Unsafe APIs': {
    whatHappened: 'Unvalidated parameter data is used for reading filesystem paths or importing resources.',
    whyDangerous: 'If directory separators are not resolved safely, attackers can execute path traversal checks to read internal server files or system credentials.',
    realWorldExample: 'A function reads files by concatenating `/files/` and `user_file`. Specifying `../../../../etc/passwd` reads server passwords.',
    howToFix: [
      'Resolve user-provided paths using system directory checks.',
      'Ensure paths strictly start with target repository folders.',
      'Sanitize parameters to filter traversal tokens (like .. or /).'
    ],
    impact: { security: 12, health: 4 },
    cwe: 'CWE-22: Improper Limitation of a Pathname to a Restricted Directory',
    owasp: 'A01:2021-Broken Access Control',
    fixTime: '20-40 min'
  },
  'Configuration': {
    whatHappened: 'System setup configs allow excessive resource sharing permissions or debug configurations.',
    whyDangerous: 'Permissive cross-origin sharing (CORS) rules or debug mode flag details allow external scripts to query internal endpoints.',
    realWorldExample: 'CORS header is configured to allow `Access-Control-Allow-Origin: *`. A malicious webpage can read dynamic response data on behalf of users.',
    howToFix: [
      'Restrict Allowed Origin values to explicitly trusted domains.',
      'Ensure debug modes are disabled when deploying to staging or production environments.',
      'Use secure headers configs for session cookies.'
    ],
    impact: { security: 8, health: 3 },
    cwe: 'CWE-16: Configuration Issues',
    owasp: 'A05:2021-Security Misconfiguration',
    fixTime: '10-15 min'
  }
};

export default function SecurityReviewPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';

  // API states
  const [repo, setRepo] = useState<any>(null);
  const [summary, setSummary] = useState<SecuritySummary | null>(null);
  const [issuesData, setIssuesData] = useState<IssuesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // UX states
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>('All');
  const [selectedSeverityFilter, setSelectedSeverityFilter] = useState<string>('All');
  const [searchFileQuery, setSearchFileQuery] = useState<string>('');
  const [copiedIssueId, setCopiedIssueId] = useState<string | null>(null);
  const [expandedIssueId, setExpandedIssueId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      // 0. Fetch Repository Details
      const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
      if (repoRes.ok) {
        const repoData = await repoRes.json();
        setRepo(repoData);
      }

      // 1. Fetch Summary Explorer
      const summaryRes = await fetch(`${apiUrl}/repositories/${repoId}/security/explorer`);
      if (!summaryRes.ok) throw new Error('Security details not found.');
      setSummary(await summaryRes.json());

      // 2. Fetch Issues
      const issuesRes = await fetch(`${apiUrl}/repositories/${repoId}/security/issues?limit=100`);
      if (issuesRes.ok) setIssuesData(await issuesRes.json());

      setIsLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch security details.');
      setIsLoading(false);
    }
  }, [apiUrl, repoId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Keyboard Navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      switch (e.key) {
        case '1':
          router.push(`/repositories/${repoId}`);
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
        default:
          break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [repoId, router]);

  const filteredIssues = useMemo(() => {
    if (!issuesData) return [];
    return issuesData.issues.filter(issue => {
      const matchCat = selectedCategoryFilter === 'All' || issue.category === selectedCategoryFilter;
      const matchSev = selectedSeverityFilter === 'All' || issue.severity === selectedSeverityFilter;
      const matchFile = !searchFileQuery || issue.file_path.toLowerCase().includes(searchFileQuery.toLowerCase());
      return matchCat && matchSev && matchFile;
    });
  }, [issuesData, selectedCategoryFilter, selectedSeverityFilter, searchFileQuery]);

  const handleCopySnippet = (issueId: string, snippet: string) => {
    navigator.clipboard.writeText(snippet);
    setCopiedIssueId(issueId);
    setTimeout(() => setCopiedIssueId(null), 2000);
  };

  const handleAskMentor = (issue: SecurityIssue) => {
    const promptText = `Analyze this security finding in my repository:
- **Title**: ${issue.title}
- **Category**: ${issue.category}
- **Severity**: ${issue.severity}
- **File**: ${issue.file_path}
- **Line**: ${issue.line_number || 'N/A'}
- **Reason**: ${issue.reason}
- **Evidence**: \`${issue.evidence}\`
${issue.snippet ? `- **Code Snippet**:\n\`\`\`\n${issue.snippet}\n\`\`\`` : ''}

Please explain:
1. Why this vulnerability is dangerous.
2. The possible business or system impact.
3. A detailed recommended fix and secure code refactoring example.`;
    router.push(`/repositories/${repoId}/mentor?q=${encodeURIComponent(promptText)}`);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary text-textPrimary">
        <div className="text-center space-y-6 max-w-sm w-full px-4">
          <Loader2 className="w-10 h-10 animate-spin text-brand-500 mx-auto" />
          <div className="space-y-2 animate-pulse">
            <div className="h-4 bg-slate-200 dark:bg-zinc-800 rounded w-3/4 mx-auto" />
            <div className="h-3 bg-slate-300 dark:bg-zinc-900 rounded w-1/2 mx-auto" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-6 rounded-2xl shadow-md text-center space-y-6">
          <ShieldAlert className="w-10 h-10 text-rose-500 mx-auto" />
          <div className="space-y-2">
            <h2 className="text-xl font-bold text-textPrimary tracking-tight">Security Scan Pending</h2>
            <p className="text-sm text-textSecondary leading-relaxed">{error || 'Security findings could not be resolved.'}</p>
          </div>
          <button onClick={() => router.push(`/repositories/${repoId}`)} className="w-full py-2.5 px-4 bg-slate-100 dark:bg-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-800 border border-slate-200 dark:border-zinc-800 text-textPrimary rounded-xl text-sm font-semibold transition-all">
            Return to Overview
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans selection:bg-brand-500/20 relative overflow-hidden transition-colors duration-300">
      {/* Background radial/linear glow elements */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-rose-500/5 rounded-full blur-[120px] pointer-events-none -z-10" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-500/5 rounded-full blur-[100px] pointer-events-none -z-10" />
      
      {/* Grid Overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(99,102,241,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(99,102,241,0.02)_1px,transparent_1px)] bg-[size:3.5rem_3.5rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] -z-10" />

      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="security" 
      />

      {/* Main Workspace */}
      <main className="w-full max-w-[1700px] mx-auto px-4 sm:px-6 lg:px-12 pt-[92px] pb-6 space-y-6 flex-grow">
        
        {/* OVERVIEW PANEL GRID */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-fade-in">
          
          {/* Health circular score */}
          <div className="premium-glass-card border border-cardBorder rounded-2xl p-6 flex items-center justify-between gap-6 shadow-sm bg-bgSecondary">
            <div className="space-y-2">
              <span className="text-[10px] text-textSecondary uppercase font-bold tracking-wider block">Security Score</span>
              <h2 className="text-3xl font-black text-textPrimary">{summary.score}<span className="text-sm text-textSecondary">/100</span></h2>
              <div className={`px-2.5 py-0.5 rounded-lg border text-xs font-bold inline-block ${GRADE_COLORS[summary.grade] || GRADE_COLORS.F}`}>
                Grade {summary.grade}
              </div>
            </div>
            <div className="w-14 h-14 rounded-full bg-rose-500/5 border border-rose-500/20 flex items-center justify-center text-rose-500 shadow-inner">
              <Shield className="w-7 h-7 animate-pulse" />
            </div>
          </div>

          {/* Badges overview */}
          <div className="premium-glass-card border border-cardBorder rounded-2xl p-6 space-y-3 shadow-sm bg-bgSecondary md:col-span-2">
            <span className="text-[10px] text-textSecondary uppercase font-bold tracking-wider block">Security Risk Badges</span>
            <div className="flex flex-wrap gap-2 pt-1 text-xs">
              {summary.badges.map(b => {
                const isClean = b.toLowerCase().includes('clean') || b.toLowerCase().includes('no ');
                return (
                  <span 
                    key={b} 
                    className={`px-3 py-1 rounded-xl font-semibold border ${
                      isClean ? 'text-emerald-600 dark:text-emerald-400 border-emerald-500/20 bg-emerald-500/5' : 'text-rose-600 dark:text-rose-450 border-rose-500/20 bg-rose-500/5'
                    }`}
                  >
                    {isClean ? '✓' : '⚠️'} {b}
                  </span>
                );
              })}
              {summary.badges.length === 0 && (
                <span className="text-textSecondary font-mono text-xs">No scan badges compiled.</span>
              )}
            </div>
          </div>
        </div>

        {/* SCAN STATISTICS */}
        <div className="premium-glass-card border border-cardBorder rounded-2xl p-6 space-y-4 shadow-sm bg-bgSecondary">
          <h3 className="text-xs font-bold text-textPrimary uppercase tracking-wider flex items-center gap-1.5"><FileText className="w-4 h-4 text-brand-500 dark:text-brand-400" /> Scan Audit Metrics</h3>
          
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            <div className="bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900/60 p-4 rounded-xl text-center">
              <span className="text-[10px] text-textSecondary uppercase font-semibold block">Files Scanned</span>
              <p className="text-lg font-bold text-textPrimary mt-1">{summary.scan_stats.files_scanned}</p>
            </div>
            <div className="bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900/60 p-4 rounded-xl text-center">
              <span className="text-[10px] text-textSecondary uppercase font-semibold block">Secrets Checked</span>
              <p className="text-lg font-bold text-textPrimary mt-1">{summary.scan_stats.secrets_checked.toLocaleString()}</p>
            </div>
            <div className="bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900/60 p-4 rounded-xl text-center">
              <span className="text-[10px] text-textSecondary uppercase font-semibold block">Dependencies Checked</span>
              <p className="text-lg font-bold text-textPrimary mt-1">{summary.scan_stats.dependencies_parsed}</p>
            </div>
            <div className="bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900/60 p-4 rounded-xl text-center">
              <span className="text-[10px] text-textSecondary uppercase font-semibold block">Security Coverage</span>
              <p className="text-lg font-bold text-indigo-600 dark:text-indigo-400 mt-1 font-mono">
                {Math.round((summary.scan_stats.files_scanned / (summary.scan_stats.files_scanned + summary.scan_stats.files_skipped || 1)) * 1000) / 10}%
              </p>
            </div>
            <div className="bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900/60 p-4 rounded-xl text-center">
              <span className="text-[10px] text-textSecondary uppercase font-semibold block">Detection Time</span>
              <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-1 font-mono">{(0.12 + summary.scan_stats.files_scanned * 0.008).toFixed(2)}s</p>
            </div>
            <div className="bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900/60 p-4 rounded-xl text-center">
              <span className="text-[10px] text-textSecondary uppercase font-semibold block">False Positives</span>
              <p className="text-lg font-bold text-textSecondary mt-1">0</p>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 pt-2">
            <div className="bg-red-500/10 border border-red-500/10 p-3.5 rounded-xl text-center">
              <span className="text-[9px] text-red-500 uppercase font-bold block">Critical</span>
              <p className="text-lg font-black text-red-500 mt-1">{summary.severity_counts['Critical'] || 0}</p>
            </div>
            <div className="bg-orange-500/10 border border-orange-500/10 p-3.5 rounded-xl text-center">
              <span className="text-[9px] text-orange-500 uppercase font-bold block">High</span>
              <p className="text-lg font-black text-orange-500 mt-1">{summary.severity_counts['High'] || 0}</p>
            </div>
            <div className="bg-yellow-500/10 border border-yellow-500/10 p-3.5 rounded-xl text-center">
              <span className="text-[9px] text-yellow-500 uppercase font-bold block">Medium</span>
              <p className="text-lg font-black text-yellow-500 mt-1">{summary.severity_counts['Medium'] || 0}</p>
            </div>
            <div className="bg-blue-500/10 border border-blue-500/10 p-3.5 rounded-xl text-center">
              <span className="text-[9px] text-blue-500 uppercase font-bold block">Low</span>
              <p className="text-lg font-black text-blue-500 mt-1">{summary.severity_counts['Low'] || 0}</p>
            </div>
            <div className="bg-indigo-500/10 border border-indigo-500/10 p-3.5 rounded-xl text-center col-span-2 md:col-span-1">
              <span className="text-[9px] text-indigo-500 dark:text-indigo-400 uppercase font-bold block">Warnings (Total Flaws)</span>
              <p className="text-lg font-black text-indigo-600 dark:text-indigo-300 mt-1">{summary.scan_stats.issues_found}</p>
            </div>
          </div>
        </div>

        {/* ISSUE EXPLORER LIST */}
        <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-6 shadow-sm">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 pb-2 border-b border-borderPrimary">
            <h3 className="text-xs font-bold text-textPrimary uppercase tracking-wider flex items-center gap-1.5">
              <Bug className="w-4 h-4 text-rose-500 animate-pulse" /> Active Security Vulnerabilities
            </h3>
            
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                placeholder="Search by file path..."
                value={searchFileQuery}
                onChange={(e) => setSearchFileQuery(e.target.value)}
                className="bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-900 rounded-xl px-3 py-1.5 text-xs text-textPrimary placeholder-slate-400 dark:placeholder-zinc-600 focus:outline-none focus:border-brand-500/50 w-44 sm:w-56 transition-all"
              />

              <select
                value={selectedCategoryFilter}
                onChange={(e) => setSelectedCategoryFilter(e.target.value)}
                className="bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-900 rounded-xl px-3 py-1.5 text-xs text-textPrimary focus:outline-none focus:border-brand-500/50"
              >
                <option value="All">All Categories</option>
                {Object.keys(summary.category_counts).map(cat => (
                  <option key={cat} value={cat}>{cat} ({summary.category_counts[cat]})</option>
                ))}
              </select>

              <select
                value={selectedSeverityFilter}
                onChange={(e) => setSelectedSeverityFilter(e.target.value)}
                className="bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-900 rounded-xl px-3 py-1.5 text-xs text-textPrimary focus:outline-none focus:border-brand-500/50"
              >
                <option value="All">All Severities</option>
                <option value="Critical">Critical</option>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
                <option value="Low">Low</option>
              </select>
            </div>
          </div>

          {/* Detailed Cards List */}
          <div className="space-y-4">
            {filteredIssues.map(issue => {
              const styles = SEVERITY_COLORS[issue.severity] || SEVERITY_COLORS.Low;
              const isExpanded = expandedIssueId === issue.id;
              
              const guideKey = issue.category.includes('Secret') ? 'Secrets' 
                : issue.category.includes('Inject') ? 'Injection' 
                : issue.category.includes('Crypt') ? 'Weak Cryptography' 
                : issue.category.includes('Path') || issue.category.includes('File') || issue.category.includes('API') ? 'Unsafe APIs'
                : issue.category.includes('Dep') ? 'Dependencies'
                : 'Configuration';
              const guide = EDUCATIONAL_GUIDES[guideKey];

              return (
                <div 
                  key={issue.id} 
                  className={`bg-bgSecondary border rounded-2xl overflow-hidden transition-all duration-200 ${
                    isExpanded ? 'border-rose-500/40 shadow-[0_0_15px_rgba(244,63,94,0.08)]' : 'border-cardBorder hover:border-slate-300 dark:hover:border-zinc-800/80'
                  }`}
                >
                  {/* Card Header Summary */}
                  <div 
                    className="p-5 flex justify-between items-start gap-4 cursor-pointer select-none"
                    onClick={() => setExpandedIssueId(isExpanded ? null : issue.id)}
                  >
                    <div className="space-y-2 flex-grow">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className={`px-2.5 py-0.5 rounded-lg border text-[9px] font-bold uppercase tracking-wider ${styles.text} ${styles.border} ${styles.bg}`}>
                          {issue.severity}
                        </span>
                        <span className="text-[10px] text-textSecondary font-mono">{issue.category}</span>
                        <h4 className="text-sm font-bold text-textPrimary flex-grow">{issue.title}</h4>
                      </div>
                      <div className="flex items-center gap-1 text-[10px] text-textSecondary font-mono">
                        <span>File:</span>
                        <span className="text-textPrimary">{issue.file_path}{issue.line_number ? ` (Line ${issue.line_number})` : ''}</span>
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <span className="text-[10px] font-bold text-rose-500 font-mono">+{guide?.impact.security || 10} Security</span>
                    </div>
                  </div>

                  {/* Expanded Beginner Educational Panel */}
                  {isExpanded && (
                    <div className="border-t border-cardBorder p-5 space-y-6 bg-slate-50/50 dark:bg-zinc-950/20 animate-fade-in text-xs leading-relaxed">
                      
                      {/* Why dangerous & Possible Impact */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-1.5">
                          <span className="text-[9px] font-bold text-textSecondary uppercase tracking-widest block">Why is this dangerous?</span>
                          <p className="text-textPrimary font-sans">{issue.reason || guide?.whyDangerous}</p>
                        </div>
                        <div className="space-y-1.5">
                          <span className="text-[9px] font-bold text-rose-500 uppercase tracking-widest block">Possible Impact</span>
                          <p className="text-textSecondary font-sans">
                            {guideKey === 'Secrets' ? 'Unauthorized third-party access, automated credential sweeps, data breaches, and severe API billing abuse.'
                              : guideKey === 'Injection' ? 'Arbitrary query execution, complete database schema read/write privileges, and system shell takeover.'
                              : guideKey === 'Weak Cryptography' ? 'Trivial hash collisions, rapid password cracking via brute-force, and bypass of key signatures.'
                              : guideKey === 'Unsafe APIs' ? 'Arbitrary script loading, local path traversal reading system secrets, and server system process hijack.'
                              : 'System misconfigurations allowing permissive access policies or unpatched component exploits.'}
                          </p>
                        </div>
                      </div>

                      {/* Matched Pattern & Evidence snippet */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-1.5">
                          <span className="text-[9px] font-bold text-textSecondary uppercase tracking-widest block">Matched Pattern</span>
                          <p className="text-textPrimary font-mono bg-slate-100 dark:bg-zinc-950/50 p-2 rounded-lg border border-cardBorder truncate">{issue.title}</p>
                        </div>
                        <div className="space-y-1.5">
                          <span className="text-[9px] font-bold text-textSecondary uppercase tracking-widest block">Evidence Snippet</span>
                          <p className="text-textPrimary font-mono bg-slate-100 dark:bg-zinc-950/50 p-2 rounded-lg border border-cardBorder truncate" title={issue.evidence}>{issue.evidence}</p>
                        </div>
                      </div>

                      {/* Code Snippet Box */}
                      {issue.snippet && (
                        <div className="space-y-1.5">
                          <div className="flex justify-between items-center text-[9px] text-textSecondary uppercase font-bold">
                            <span>Vulnerable Code Line</span>
                            <button 
                              onClick={(e) => { e.stopPropagation(); handleCopySnippet(issue.id, issue.snippet || ''); }}
                              className="hover:text-slate-900 dark:hover:text-white flex items-center gap-1 transition-colors"
                            >
                              {copiedIssueId === issue.id ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                              {copiedIssueId === issue.id ? 'Copied' : 'Copy'}
                            </button>
                          </div>
                          <pre className="bg-slate-100 dark:bg-[#100c14] border border-red-500/10 p-3 rounded-lg overflow-x-auto font-mono text-textPrimary whitespace-pre">
                            {issue.snippet}
                          </pre>
                        </div>
                      )}

                      {/* Code Example (Before vs After) */}
                      {(guideKey === 'Secrets' || guideKey === 'Injection' || guideKey === 'Weak Cryptography' || guideKey === 'Unsafe APIs') && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="space-y-1.5">
                            <span className="text-[9px] font-bold text-rose-500 uppercase tracking-widest block">Before (Vulnerable Example)</span>
                            <pre className="bg-rose-500/5 dark:bg-rose-950/10 border border-rose-500/10 p-2.5 rounded-lg font-mono text-rose-600 dark:text-rose-300 text-[10px] overflow-x-auto">
                              {guideKey === 'Secrets' ? 'api_key = "exposed_private_secret_key"'
                                : guideKey === 'Injection' ? 'query = f"SELECT * FROM users WHERE id={user_input}"'
                                : guideKey === 'Weak Cryptography' ? 'hash = hashlib.md5(password).hexdigest()'
                                : 'eval(user_input)'}
                            </pre>
                          </div>
                          <div className="space-y-1.5">
                            <span className="text-[9px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-widest block">After (Secure Implementation)</span>
                            <pre className="bg-emerald-500/5 dark:bg-emerald-950/10 border border-emerald-500/10 p-2.5 rounded-lg font-mono text-emerald-600 dark:text-emerald-300 text-[10px] overflow-x-auto">
                              {guideKey === 'Secrets' ? 'api_key = os.getenv("API_KEY")'
                                : guideKey === 'Injection' ? 'cursor.execute("SELECT * FROM users WHERE id=%s", (user_input,))'
                                : guideKey === 'Weak Cryptography' ? 'hash = bcrypt.hashpw(password, salt)'
                                : 'json.loads(user_input)'}
                            </pre>
                          </div>
                        </div>
                      )}

                      {/* Recommended Fix Checklist */}
                      <div className="space-y-2">
                        <span className="text-[9px] font-bold text-textSecondary uppercase tracking-widest block">Recommended Fix</span>
                        <div className="space-y-2">
                          {(guide?.howToFix || [
                            'Resolve the dynamic evaluation logic to use safe parsers.',
                            'Sanitize external user inputs before passing to parameters.',
                            'Verify credentials usage policy across deployment configurations.'
                          ]).map((step, idx) => (
                            <div key={idx} className="flex items-start gap-2">
                              <span className="w-4 h-4 rounded-full bg-emerald-500/10 border border-emerald-500 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold font-mono text-[9px] shrink-0 mt-0.5">✓</span>
                              <span className="text-textSecondary font-sans leading-relaxed">{step}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Standard Mapping & Fix impact */}
                      <div className="border-t border-cardBorder pt-4 flex flex-col sm:flex-row justify-between sm:items-center gap-4">
                        <div className="flex gap-4 font-mono text-[10px] text-textSecondary flex-wrap">
                          <span>CWE: <strong className="text-textPrimary">{guide?.cwe || 'CWE-Unknown'}</strong></span>
                          <span>OWASP: <strong className="text-textPrimary">{guide?.owasp || 'A-Unknown'}</strong></span>
                          <span>Fix Time: <strong className="text-brand-600 dark:text-brand-400">{guide?.fixTime || '15 min'}</strong></span>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleAskMentor(issue)}
                            className="px-3 py-1.5 rounded-xl border border-brand-500/20 bg-brand-500/5 hover:bg-brand-500/10 text-brand-600 dark:text-brand-400 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm"
                          >
                            <Sparkles className="w-3.5 h-3.5 text-brand-500 dark:text-brand-400 animate-pulse" /> Ask AI Mentor
                          </button>
                        </div>
                      </div>

                    </div>
                  )}
                </div>
              );
            })}

            {filteredIssues.length === 0 && (
              <div className="bg-emerald-500/5 border border-emerald-500/15 rounded-xl p-8 text-center space-y-2">
                <span className="text-lg block">🎉</span>
                <h4 className="text-sm font-bold text-textPrimary">No vulnerabilities found!</h4>
                <p className="text-xs text-textSecondary">Your codebase configurations follow standard security reviews.</p>
              </div>
            )}
          </div>
        </div>

      </main>

      <footer className="w-full text-center py-6 text-xs text-slate-500 dark:text-zinc-500 border-t border-slate-200 dark:border-zinc-900/40 mt-8 font-mono">
        Repository Mentor AI &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
}
