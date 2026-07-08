'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from '../../../../Header';
import { useTheme } from '../../../../ThemeProvider';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ArrowLeft, Code, BarChart3, Bug, FileText, Loader2, ShieldAlert,
  Activity, Layers, ChevronRight, Hash, Compass, ArrowRightLeft, Eye, X, HelpCircle, Sparkles
} from 'lucide-react';
import { LEARNING_DATA } from '../../assessment/learning_data';

interface FileDetail {
  id: string;
  repository_id: string;
  path: string;
  extension: string | null;
  size_bytes: number;
  is_text: boolean;
  lines_of_code: number;
  complexity: number;
  code_smells_count: number;
  status_badge: string;
  module_type: string;
  analysis_metadata: {
    total_lines?: number;
    blank_lines?: number;
    comment_lines?: number;
    functions?: Array<{ name: string; line: number; loc: number; complexity?: number }>;
    classes?: Array<{ name: string; line: number; methods?: number; loc: number }>;
    declarations?: Array<{
      name: string;
      type: string;
      line: number;
      end_line?: number;
      parent?: string | null;
      visibility?: string;
      signature?: string;
      language?: string;
    }>;
    dependencies?: Array<{
      type: string;
      target: string;
      line: number;
    }>;
    metrics?: {
      function_count?: number;
      class_count?: number;
      interface_count?: number;
      enum_count?: number;
      struct_count?: number;
      trait_count?: number;
      average_parameters?: number;
      average_function_length?: number;
      max_complexity?: number;
      max_nesting_depth?: number;
      comment_ratio?: number;
    };
  } | null;
  smells: Array<{
    id: string;
    smell_type: string;
    category: string;
    severity: string;
    line_number: number | null;
    measured_value: number;
    threshold: number;
    reason: string;
  }>;
}

const EXT_TO_LANG: Record<string, string> = {
  '.py': 'Python',
  '.js': 'JavaScript',
  '.jsx': 'React JS',
  '.ts': 'TypeScript',
  '.tsx': 'React TS',
  '.java': 'Java',
  '.go': 'Go',
  '.rs': 'Rust',
  '.cpp': 'C++',
  '.c': 'C',
  '.h': 'C/C++ Header',
  '.cs': 'C#',
  '.php': 'PHP',
  '.rb': 'Ruby',
  '.kt': 'Kotlin',
  '.swift': 'Swift'
};

const SEVERITY_COLORS: Record<string, string> = {
  Critical: 'text-red-500 border-red-500/20 bg-red-500/5',
  High: 'text-orange-500 border-orange-500/25 bg-orange-500/5',
  Medium: 'text-yellow-500 border-yellow-500/25 bg-yellow-500/5',
  Low: 'text-blue-500 border-blue-500/25 bg-blue-500/5',
};

const BADGE_STYLES: Record<string, string> = {
  'Healthy': 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5',
  'Needs Attention': 'text-amber-400 border-amber-500/20 bg-amber-500/5',
  'High Complexity': 'text-rose-400 border-rose-500/20 bg-rose-500/5'
};

const classifyImport = (target: string, ext: string): { type: string; color: string } => {
  const targetLower = target.toLowerCase();
  
  if (ext === '.java') {
    if (target.startsWith('java.') || target.startsWith('javax.')) {
      return { type: 'Standard Library', color: 'text-sky-400 border-sky-500/20 bg-sky-500/5' };
    }
    if (target.startsWith('org.springframework.') || target.startsWith('jakarta.') || target.startsWith('org.hibernate.')) {
      return { type: 'Framework', color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5' };
    }
    if (target.startsWith('com.example.') || target.includes('repository') || target.includes('service') || target.includes('controller') || target.includes('model')) {
      return { type: 'Internal Module', color: 'text-violet-400 border-violet-500/20 bg-violet-500/5' };
    }
    return { type: 'Third-party Library', color: 'text-amber-400 border-amber-500/20 bg-amber-500/5' };
  }
  
  if (ext === '.py') {
    const stdlibs = ['os', 'sys', 're', 'json', 'datetime', 'typing', 'math', 'time', 'collections', 'hashlib', 'uuid', 'traceback', 'logging', 'argparse', 'shutil', 'tempfile', 'subprocess', 'urllib', 'http'];
    const stdMatch = stdlibs.some(lib => targetLower === lib || targetLower.startsWith(lib + '.'));
    if (stdMatch) {
      return { type: 'Standard Library', color: 'text-sky-400 border-sky-500/20 bg-sky-500/5' };
    }
    const frameworks = ['fastapi', 'django', 'flask', 'sqlalchemy', 'pydantic', 'httpx', 'jinja2', 'pytest'];
    const fwMatch = frameworks.some(fw => targetLower.startsWith(fw));
    if (fwMatch) {
      return { type: 'Framework', color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5' };
    }
    if (target.startsWith('.')) {
      return { type: 'Internal Module', color: 'text-violet-400 border-violet-500/20 bg-violet-500/5' };
    }
    return { type: 'Third-party Library', color: 'text-amber-400 border-amber-500/20 bg-amber-500/5' };
  }
  
  // JS / TS
  if (target.startsWith('.') || target.startsWith('/') || target.startsWith('@/')) {
    return { type: 'Internal Module', color: 'text-violet-400 border-violet-500/20 bg-violet-500/5' };
  }
  const stdlibsNode = ['path', 'fs', 'crypto', 'os', 'http', 'https', 'url', 'events', 'stream', 'util', 'dns'];
  if (stdlibsNode.includes(targetLower)) {
    return { type: 'Standard Library', color: 'text-sky-400 border-sky-500/20 bg-sky-500/5' };
  }
  const frameworksJS = ['react', 'next', 'vue', 'express', 'tailwind', '@nestjs'];
  const fwMatchJS = frameworksJS.some(fw => targetLower === fw || targetLower.startsWith(fw + '/'));
  if (fwMatchJS) {
    return { type: 'Framework', color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5' };
  }
  return { type: 'Third-party Library', color: 'text-amber-400 border-amber-500/20 bg-amber-500/5' };
};

const getSmellMentorship = (smellType: string, reason: string): {
  principle: string;
  whyCare: string;
  suggestedFix: string;
  estimatedGain: string;
} => {
  const type = smellType.toLowerCase();
  if (type.includes('magic')) {
    return {
      principle: "Configuration over Hardcoding",
      whyCare: "Hardcoded literal constants make config changes require rebuilding code, complicating multi-environment deployments.",
      suggestedFix: "Extract the value into a named static constant, environment variable, or configuration properties file (e.g. constants.ts).",
      estimatedGain: "Maintainability +2, Readability +1"
    };
  }
  if (type.includes('long method') || type.includes('length') || type.includes('longmethod')) {
    return {
      principle: "Single Responsibility Principle (SRP)",
      whyCare: "Long methods are highly prone to side effects, harder to cover with unit tests, and difficult to comprehend.",
      suggestedFix: "Apply 'Extract Method' refactoring. Break down distinct blocks into self-documenting sub-functions.",
      estimatedGain: "Maintainability +3, Complexity -4"
    };
  }
  if (type.includes('nesting') || type.includes('complexity')) {
    return {
      principle: "Keep It Simple, Stupid (KISS)",
      whyCare: "Deeply nested conditional constructs create massive cognitive branches, making code extremely bug-prone.",
      suggestedFix: "Apply guard clauses to return early, or extract nested loops into independent helper functions.",
      estimatedGain: "Complexity -5, Readability +2"
    };
  }
  if (type.includes('god') || type.includes('large class') || type.includes('largeclass')) {
    return {
      principle: "Single Responsibility / Low Coupling",
      whyCare: "Monolithic classes containing hundreds of lines of code become single points of failures that require modification for unrelated features.",
      suggestedFix: "Deconstruct the class. Delegate secondary responsibilities into standalone cohesive helper service beans.",
      estimatedGain: "Maintainability +5, Architecture +4"
    };
  }
  if (type.includes('empty catch')) {
    return {
      principle: "Defensive Programming & Fail-Safe Design",
      whyCare: "Swallowing exceptions silently hides system failures, making runtime debugging in production environments nearly impossible.",
      suggestedFix: "Log the exception with details, or rethrow it wrapped inside a custom business exception.",
      estimatedGain: "Robustness +4, Maintainability +1"
    };
  }
  return {
    principle: "Clean Code Engineering Standards",
    whyCare: "Anti-patterns degrade structural quality, increasing maintenance costs and lowering developer velocity.",
    suggestedFix: "Refactor logic to comply with Single Responsibility and high-cohesion design principles.",
    estimatedGain: "Maintainability +1, Readability +1"
  };
};

export default function FileDetailPage({ params }: { params: { id: string; fileId: string } }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { id: repoId, fileId } = params;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';

  const [repo, setRepo] = useState<any>(null);
  const [file, setFile] = useState<FileDetail | null>(null);
  const [codeContent, setCodeContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [isCodeCollapsed, setIsCodeCollapsed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Concept for Interactive Learning Drawer
  const [activeLearningConcept, setActiveLearningConcept] = useState<string | null>(null);
  const [highlightedLine, setHighlightedLine] = useState<number | null>(null);

  const lineRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const fetchFileDetailAndContent = useCallback(async () => {
    try {
      const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
      if (repoRes.ok) {
        const repoData = await repoRes.json();
        setRepo(repoData);
      }

      const res = await fetch(`${apiUrl}/repositories/${repoId}/files/${fileId}`);
      if (!res.ok) throw new Error('File metrics not found.');
      const fileData = await res.json();
      setFile(fileData);

      const contentRes = await fetch(`${apiUrl}/repositories/${repoId}/files/${fileId}/content`);
      if (contentRes.ok) {
        const contentData = await contentRes.json();
        setCodeContent(contentData.content);
      }
      setIsLoading(false);
    } catch (err: any) {
      setError(err.message);
      setIsLoading(false);
    }
  }, [apiUrl, repoId, fileId]);

  useEffect(() => {
    fetchFileDetailAndContent();
  }, [fetchFileDetailAndContent]);

  // Keyboard Navigation
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
        default:
          break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [repoId, router]);

  useEffect(() => {
    if (!isLoading && codeContent) {
      const lineStr = searchParams.get('line');
      if (lineStr) {
        const lineNum = parseInt(lineStr);
        setHighlightedLine(lineNum);
        setTimeout(() => {
          const el = lineRefs.current[lineNum];
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            el.classList.add('bg-yellow-500/10', 'border-l-2', 'border-yellow-500', 'animate-pulse');
            setTimeout(() => {
              el.classList.remove('animate-pulse');
            }, 2000);
          }
        }, 300);
      }
    }
  }, [isLoading, codeContent, searchParams]);

  const handleLineClick = (lineNum: number) => {
    setHighlightedLine(lineNum);
    const el = lineRefs.current[lineNum];
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.add('bg-yellow-500/10', 'border-l-2', 'border-yellow-500', 'animate-pulse');
      setTimeout(() => {
        el.classList.remove('animate-pulse');
      }, 1500);
    }
  };

  const highlightCodeLine = (lineText: string, ext: string) => {
    if (!lineText) return '&nbsp;';
    const escaped = lineText
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    const keywords = /\b(const|let|var|function|return|import|export|from|class|extends|implements|public|private|protected|static|final|new|try|catch|throw|if|else|for|while|await|async|def|elif|lambda|pass|with|as)\b/g;
    const strings = /(["'`])(.*?)\1/g;
    const comments = /(\/\/.*$|#.*$|\/\*[\s\S]*?\*\/)/gm;

    let highlighted = escaped
      .replace(comments, '<span class="text-zinc-550 italic">$1</span>')
      .replace(strings, '<span class="text-emerald-350">$&</span>')
      .replace(keywords, '<span class="text-violet-400 font-semibold">$1</span>');

    return highlighted;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary text-textPrimary font-sans">
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

  if (error || !file) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4 font-sans text-textPrimary">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-6 rounded-2xl shadow-sm text-center space-y-4">
          <ShieldAlert className="w-8 h-8 text-rose-500 mx-auto animate-pulse" />
          <h2 className="text-xl font-bold text-textPrimary">File Not Found</h2>
          <p className="text-sm text-textSecondary leading-relaxed">{error}</p>
          <button onClick={() => router.back()} className="w-full py-2.5 px-4 bg-slate-100 dark:bg-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-700 border border-borderPrimary text-textPrimary rounded-xl text-sm font-semibold transition-all">Go Back</button>
        </div>
      </div>
    );
  }

  const language = file.extension ? EXT_TO_LANG[file.extension] || file.extension : 'Unknown';
  const deps = file.analysis_metadata?.dependencies || [];
  const extMetrics = file.analysis_metadata?.metrics || {};
  const badgeStyle = BADGE_STYLES[file.status_badge] || BADGE_STYLES['Healthy'];

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans selection:bg-brand-500/20 transition-colors duration-300">
      
      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="overview" 
      />

      {/* Main Workspace */}
      <main className="w-full max-w-[1700px] mx-auto px-4 sm:px-6 lg:px-12 pt-[92px] pb-6 space-y-6 flex-grow">
        
        {/* TOP FILE METRICS */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-bgSecondary border border-borderPrimary p-4 rounded-2xl space-y-1 shadow-sm">
            <Code className="w-4 h-4 text-brand-500 dark:text-brand-400" />
            <p className="text-lg font-bold text-textPrimary font-mono">{file.lines_of_code}</p>
            <p className="text-[9px] text-textSecondary uppercase font-semibold">LOC</p>
          </div>
          <div className="bg-bgSecondary border border-borderPrimary p-4 rounded-2xl space-y-1 shadow-sm">
            <BarChart3 className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
            <p className="text-lg font-bold text-textPrimary font-mono">{file.complexity}</p>
            <p className="text-[9px] text-textSecondary uppercase font-semibold">Complexity</p>
          </div>
          <div className="bg-bgSecondary border border-borderPrimary p-4 rounded-2xl space-y-1 shadow-sm">
            <Activity className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
            <p className="text-lg font-bold text-textPrimary font-mono">{extMetrics.function_count || 0}</p>
            <p className="text-[9px] text-textSecondary uppercase font-semibold">Functions</p>
          </div>
          <div className="bg-bgSecondary border border-borderPrimary p-4 rounded-2xl space-y-1 shadow-sm">
            <Layers className="w-4 h-4 text-violet-500 dark:text-violet-400" />
            <p className="text-lg font-bold text-textPrimary font-mono">{extMetrics.class_count || 0}</p>
            <p className="text-[9px] text-textSecondary uppercase font-semibold">Classes</p>
          </div>
          <div className="bg-bgSecondary border border-borderPrimary p-4 rounded-2xl space-y-1 shadow-sm">
            <Hash className="w-4 h-4 text-brand-500 dark:text-brand-400" />
            <p className="text-lg font-bold text-textPrimary font-mono">{extMetrics.comment_ratio ? `${(extMetrics.comment_ratio * 100).toFixed(0)}%` : '0%'}</p>
            <p className="text-[9px] text-textSecondary uppercase font-semibold">Comments</p>
          </div>
          <div className="bg-bgSecondary border border-borderPrimary p-4 rounded-2xl space-y-1 shadow-sm">
            <Compass className="w-4 h-4 text-indigo-500 dark:text-indigo-450" />
            <p className="text-lg font-bold text-textPrimary font-mono capitalize">{file.module_type}</p>
            <p className="text-[9px] text-textSecondary uppercase font-semibold">Layer Type</p>
          </div>
        </div>

        {/* CODE SPLIT EDITOR VIEW */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          
          {/* Monaco-Style Code Inspector (Left) */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex justify-between items-center bg-bgSecondary p-4 border border-borderPrimary rounded-t-2xl border-b-0 shadow-sm">
              <span className="text-xs font-bold text-textPrimary flex items-center gap-1.5 font-mono"><Eye className="w-4 h-4 text-brand-500 dark:text-brand-400" /> Source Inspector</span>
              <button 
                onClick={() => setIsCodeCollapsed(!isCodeCollapsed)} 
                className="text-[10px] text-textSecondary hover:text-textPrimary uppercase font-bold tracking-wider transition-colors"
              >
                {isCodeCollapsed ? 'Expand View' : 'Collapse View'}
              </button>
            </div>

            {!isCodeCollapsed && (
              <div className="border border-borderPrimary bg-bgSecondary rounded-b-2xl overflow-hidden shadow-sm">
                <div className="flex font-mono text-[11px] leading-relaxed max-h-[600px] overflow-y-auto">
                  
                  {/* Line numbers gutter */}
                  <div className="text-right pr-3 pl-4 py-4 bg-slate-50 dark:bg-zinc-950/50 text-slate-400 dark:text-zinc-650 border-r border-slate-200 dark:border-zinc-900 select-none">
                    {codeContent.split('\n').map((_, idx) => {
                      const lineNum = idx + 1;
                      const hasSmell = file.smells.some(s => s.line_number === lineNum);
                      return (
                        <div 
                          key={idx} 
                          className={`cursor-pointer hover:text-textPrimary flex items-center justify-end gap-1 ${
                            highlightedLine === lineNum ? 'text-yellow-600 dark:text-yellow-400 font-bold' : ''
                          }`}
                          onClick={() => handleLineClick(lineNum)}
                        >
                          {hasSmell && <span className="w-1.5 h-1.5 rounded-full bg-rose-500 inline-block animate-pulse" title="Code Smell here" />}
                          {lineNum}
                        </div>
                      );
                    })}
                  </div>
                  
                  {/* Executable Code block */}
                  <div className="flex-grow space-y-0.5 select-text overflow-x-auto py-4 pl-4 pr-4 bg-slate-50/30 dark:bg-[#0a0d18]/40">
                    {codeContent.split('\n').map((line, idx) => {
                      const lineNum = idx + 1;
                      const isHighlighted = highlightedLine === lineNum;
                      return (
                        <div 
                          key={idx} 
                          ref={el => { lineRefs.current[lineNum] = el; }} 
                          className={`px-2 transition-all duration-300 rounded ${
                            isHighlighted ? 'bg-yellow-500/10 border-l-2 border-yellow-500 text-textPrimary font-medium' : 'hover:bg-slate-100/50 dark:hover:bg-zinc-900/30'
                          }`}
                          dangerouslySetInnerHTML={{ __html: highlightCodeLine(line, file.extension || '') }} 
                        />
                      );
                    })}
                  </div>

                </div>
              </div>
            )}
          </div>

          {/* SIDEBAR ANALYSIS & SMELLS PANEL (Right) */}
          <div className="space-y-6 lg:col-span-1">
            
            {/* Dependencies classifier */}
            {/* Dependencies classifier */}
            <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-5 space-y-3 shadow-sm">
              <h3 className="text-xs font-bold text-textSecondary uppercase tracking-wider flex items-center gap-1.5 font-mono">
                <ArrowRightLeft className="w-4 h-4 text-brand-500 dark:text-brand-400" /> Dependencies Tree
              </h3>
              
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {deps.map((dep, i) => {
                  const classification = classifyImport(dep.target, file.extension || '');
                  return (
                    <div key={i} className="p-3 bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900 rounded-xl space-y-1.5 flex flex-col justify-between hover:border-slate-350 dark:hover:border-zinc-800 shadow-inner">
                      <span className="truncate text-textPrimary font-mono text-[10px] font-semibold" title={dep.target}>{dep.target}</span>
                      <span className={`px-2 py-0.5 rounded text-[8px] font-bold border w-fit uppercase tracking-wider ${classification.color}`}>
                        {classification.type}
                      </span>
                    </div>
                  );
                })}
                {deps.length === 0 && (
                  <p className="text-textSecondary text-[10px] font-sans">No external modules imported.</p>
                )}
              </div>
            </div>

            {/* Code smells card with interactive learner */}
            <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-5 space-y-4 shadow-sm text-xs">
              <h3 className="text-xs font-bold text-textSecondary uppercase tracking-wider flex items-center gap-1.5 font-mono">
                <Bug className="w-4 h-4 text-brand-500 dark:text-brand-400" /> Detected Code Smells ({file.smells.length})
              </h3>
              
              <div className="space-y-4 max-h-[380px] overflow-y-auto pr-1">
                {file.smells.map(smell => {
                  const mentorship = getSmellMentorship(smell.smell_type, smell.reason);
                  const isLineSelected = highlightedLine === smell.line_number;
                  
                  return (
                    <div 
                      key={smell.id} 
                      className={`p-3.5 bg-slate-50 dark:bg-zinc-950/60 border rounded-xl space-y-3 transition-all duration-200 shadow-inner ${
                        isLineSelected ? 'border-yellow-500/40 shadow-yellow-505/5 bg-yellow-500/5 dark:bg-yellow-500/5' : 'border-slate-200 dark:border-zinc-900 hover:border-slate-300 dark:hover:border-zinc-800'
                      }`}
                    >
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className={`px-2 py-0.5 rounded text-[9px] font-bold border uppercase tracking-wider ${
                          SEVERITY_COLORS[smell.severity] || SEVERITY_COLORS.Low
                        }`}>
                          {smell.severity}
                        </span>
                        <span className="text-xs font-bold text-textPrimary truncate max-w-[150px]" title={smell.smell_type}>
                          {smell.smell_type}
                        </span>
                        <span 
                          className="text-[9px] text-textSecondary font-mono ml-auto cursor-pointer hover:text-textPrimary hover:underline" 
                          onClick={() => smell.line_number && handleLineClick(smell.line_number)}
                        >
                          Line {smell.line_number || '—'}
                        </span>
                      </div>
                      
                      <p className="text-[10px] text-textSecondary leading-normal">{smell.reason}</p>
                      
                      <div className="pt-3 border-t border-slate-200 dark:border-zinc-900 space-y-2 text-[10px]">
                        <p><span className="text-textSecondary font-bold block uppercase tracking-wider text-[8px]">Principle:</span> <span className="text-indigo-600 dark:text-indigo-400 font-semibold">{mentorship.principle}</span></p>
                        <p><span className="text-textSecondary font-bold block uppercase tracking-wider text-[8px]">Impact:</span> <span className="text-textSecondary">{mentorship.whyCare}</span></p>
                        <p><span className="text-textSecondary font-bold block uppercase tracking-wider text-[8px]">Suggested refactor:</span> <span className="text-emerald-600 dark:text-emerald-400 font-medium">{mentorship.suggestedFix}</span></p>
                        
                        <div className="flex justify-between items-center pt-2 border-t border-slate-200 dark:border-zinc-900/60 text-[9px] text-textSecondary">
                          <span>Impact: {mentorship.estimatedGain}</span>
                          <button
                            onClick={() => {
                              const key = smell.smell_type.toLowerCase().includes("magic") ? "magic" :
                                          smell.smell_type.toLowerCase().includes("complexity") ? "complexity" :
                                          smell.smell_type.toLowerCase().includes("nesting") ? "complexity" :
                                          smell.smell_type.toLowerCase().includes("god") ? "srp" : "coupling";
                              setActiveLearningConcept(key === 'magic' ? 'dry' : key);
                            }}
                            className="text-[9px] text-brand-600 dark:text-indigo-400 hover:text-brand-700 dark:hover:text-indigo-300 font-semibold flex items-center gap-0.5"
                          >
                            Learn Concept <HelpCircle className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {file.smells.length === 0 && (
                  <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-6 text-center space-y-1">
                    <p className="text-xs font-bold text-emerald-650 dark:text-white">🎉 Module Clean!</p>
                    <p className="text-[10px] text-textSecondary">Maintainability looks excellent.</p>
                  </div>
                )}
              </div>
            </div>

          </div>

        </div>

      </main>

      {/* INTERACTIVE LEARNING DRAWER */}
      {activeLearningConcept && LEARNING_DATA[activeLearningConcept] && (
        <div className="fixed top-0 right-0 h-screen max-w-lg w-full bg-bgSecondary border-l border-borderPrimary shadow-2xl p-6 overflow-y-auto space-y-6 z-50 animate-slide-in-right">
          <div className="flex justify-between items-center border-b border-borderPrimary pb-3">
            <h2 className="text-sm font-extrabold text-textPrimary flex items-center gap-1.5 font-mono">
              <HelpCircle className="w-5 h-5 text-indigo-500 dark:text-indigo-400" /> Learn: {LEARNING_DATA[activeLearningConcept].title}
            </h2>
            <button onClick={() => setActiveLearningConcept(null)} className="p-1.5 text-textSecondary hover:text-textPrimary rounded-lg border border-borderPrimary hover:border-slate-300 dark:hover:border-zinc-700 transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          
          <div className="space-y-5 text-xs leading-relaxed">
            <div className="space-y-1">
              <span className="text-[10px] uppercase font-bold text-textSecondary font-mono">Definition</span>
              <p className="text-textSecondary text-[11px] leading-relaxed">{LEARNING_DATA[activeLearningConcept].definition}</p>
            </div>
            
            <div className="space-y-2">
              <span className="text-[10px] uppercase font-bold text-textSecondary font-mono">Code Comparison</span>
              <div className="grid grid-cols-1 gap-3">
                <div className="p-3.5 bg-red-500/5 border border-red-500/15 rounded-xl shadow-inner">
                  <span className="text-[9px] uppercase font-bold text-rose-600 dark:text-rose-400 block mb-1">Bad Pattern</span>
                  <pre className="font-mono text-[9px] text-rose-700 dark:text-rose-350 overflow-x-auto">{LEARNING_DATA[activeLearningConcept].badExample}</pre>
                </div>
                <div className="p-3.5 bg-emerald-500/5 border border-emerald-500/15 rounded-xl shadow-inner">
                  <span className="text-[9px] uppercase font-bold text-emerald-600 dark:text-emerald-400 block mb-1">Good Refactored Pattern</span>
                  <pre className="font-mono text-[9px] text-emerald-700 dark:text-emerald-350 overflow-x-auto">{LEARNING_DATA[activeLearningConcept].goodExample}</pre>
                </div>
              </div>
            </div>

            <div className="space-y-1.5 p-4 bg-slate-50 dark:bg-zinc-950/60 border border-slate-200 dark:border-zinc-900 rounded-xl shadow-inner">
              <span className="text-[10px] uppercase font-bold text-indigo-600 dark:text-indigo-400 block font-mono">Why Industry Uses It</span>
              <p className="text-textSecondary text-[10px] leading-normal">{LEARNING_DATA[activeLearningConcept].whyIndustryUsesIt}</p>
            </div>

            <div className="space-y-2 border-t border-borderPrimary pt-4">
              <span className="text-[10px] uppercase font-bold text-textSecondary block font-mono">Recommended Readings</span>
              <ul className="list-disc pl-4 space-y-1 text-textSecondary text-[10px]">
                {LEARNING_DATA[activeLearningConcept].recommendedReading.map((book, j) => (
                  <li key={j}>{book}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      <footer className="w-full text-center py-6 text-xs text-slate-500 dark:text-zinc-500 border-t border-slate-200 dark:border-zinc-900/40 mt-8 font-mono">
        Repository Mentor AI &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
}
