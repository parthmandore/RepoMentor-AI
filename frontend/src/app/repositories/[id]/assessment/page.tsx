'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, Loader2, Sparkles, CheckCircle2, AlertCircle, Clock,
  Shield, Cpu, FileText, BarChart3, HelpCircle, ChevronDown, ChevronUp,
  Activity, Info, RefreshCw, Layers, Bug, Zap, Bookmark, Sliders, Play, Award,
  Check, X, FileJson, FileCode, ExternalLink, HelpCircle as HelpIcon, TrendingUp, History, ShieldAlert, ChevronRight
} from 'lucide-react';
import { LEARNING_DATA, ConceptDetails } from './learning_data';
import Header from '../../../Header';

interface EvidenceRef {
  type: string;
  path: string;
  line: number;
  detail: string;
}

interface BonusEntry {
  name: string;
  score: number;
  reason: string;
  evidence?: EvidenceRef;
}

interface DeductionEntry {
  name: string;
  score: number;
  reason: string;
  rule_triggered: string;
  threshold: string | number;
  measured: string | number;
  affected_files: string[];
  evidence_references: EvidenceRef[];
}

interface DimensionDetails {
  score: number;
  grade: string;
  bonuses: BonusEntry[];
  deductions: DeductionEntry[];
}

interface Contributor {
  file: string;
  impact: number;
  reason: string;
  evidence: EvidenceRef;
}

interface RoadmapItem {
  id: string;
  title: string;
  gain: number;
  difficulty: string;
  effort: string;
  priority: string;
  engineering_principle: string;
  affected_files: string[];
  evidence: EvidenceRef;
}

interface HistoryItem {
  generated_at: string;
  overall_score: number;
  dimension_scores: Record<string, number>;
  smells_count: number;
  vulnerabilities_count: number;
}

interface SOLIDPrinciple {
  principle: string;
  status: string;
  explanation: string;
  why_it_matters: string;
  where_occurs: string;
  evidence: string[];
  how_to_fix: string;
  estimated_impact: string;
  severity_text: string;
}

interface AssessmentData {
  metadata: {
    version: string;
    generated_at: string;
    engine_version: string;
    llm_model: string;
    knowledge_version: string;
    assessment_duration_ms: number;
    stage_durations_ms?: Record<string, number>;
    warnings?: string[];
  };
  scores: {
    overall: number;
    grade: string;
    dimensions: Record<string, any>;
  };
  explanations: {
    overall_score: number;
    overall_breakdown: Array<{
      type: string;
      name: string;
      value: number;
      symbol: string;
    }>;
    explanations: Record<string, DimensionDetails>;
  };
  contributors: {
    positive_contributors: Contributor[];
    negative_contributors: Contributor[];
  };
  roadmap: RoadmapItem[];
  confidence: {
    confidence_percentage: number;
    reasons: string[];
  };
  benchmarks: {
    categories: Record<string, { name: string; min: number; max: number; description: string }>;
    explanation: string;
  };
  principles?: SOLIDPrinciple[];
  narrative: {
    executive_summary: string;
    architecture_review: string;
    maintainability_review: string;
    security_review: string;
    documentation_review: string;
    testing_review: string;
    engineering_strengths: string;
    engineering_weaknesses: string;
    risk_assessment: string;
    production_readiness: string;
    engineering_maturity: string;
    final_verdict: string;
  };
}

export default function Assessment({ params }: { params: { id: string } }) {
  const router = useRouter();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';

  const [assessment, setAssessment] = useState<AssessmentData | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<any>(null);
  
  // Pipeline loader stage simulation during generation
  const [pipelineStage, setPipelineStage] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Simulator state: set of recommendation IDs that the user simulates fixing
  const [simulatedFixes, setSimulatedFixes] = useState<Record<string, boolean>>({});

  // UI interaction states
  const [expandedDimension, setExpandedDimension] = useState<string | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceRef | null>(null);
  const [resolvedFileId, setResolvedFileId] = useState<string | null>(null);
  
  // Interactive learning drawer concept name
  const [activeLearningConcept, setActiveLearningConcept] = useState<string | null>(null);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isGenerating) {
      timer = setInterval(() => {
        setElapsedSeconds(prev => prev + 1);
        setPipelineStage(prev => {
          if (prev < 6) return prev + 1;
          return prev;
        });
      }, 2500);
    } else {
      setElapsedSeconds(0);
      setPipelineStage(0);
    }
    return () => clearInterval(timer);
  }, [isGenerating]);

  const PIPELINE_STAGES = [
    "Cloning repository source",
    "Running structural parsing & AST analysis",
    "Calculating complexity & smells metrics",
    "Constructing project dependency graph",
    "Performing local security review scan",
    "Indexing vector knowledge base collection",
    "Compiling final explainable assessment report"
  ];

  useEffect(() => {
    if (!selectedEvidence || !selectedEvidence.path) {
      setResolvedFileId(null);
      return;
    }
    const resolveFile = async () => {
      try {
        const res = await fetch(`${apiUrl}/repositories/${repoId}/files?limit=1000`);
        if (res.ok) {
          const data = await res.json();
          const file = data.files.find((f: any) => f.path === selectedEvidence.path);
          if (file) {
            setResolvedFileId(file.id);
          }
        }
      } catch (err) {
        console.error(err);
      }
    };
    resolveFile();
  }, [selectedEvidence, repoId, apiUrl]);

  const [repo, setRepo] = useState<any>(null);
  const [isRetryingKb, setIsRetryingKb] = useState(false);

  const handleRetryKb = async () => {
    setIsRetryingKb(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/knowledge/retry`, {
        method: 'POST'
      });
      if (res.ok) {
        setError(null);
        await fetchAssessment(false);
      } else {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to trigger retry');
      }
    } catch (err: any) {
      alert(err.message || 'KB retry failed');
    } finally {
      setIsRetryingKb(false);
    }
  };

  const fetchAssessment = useCallback(async (forceGenerate = false) => {
    if (forceGenerate) {
      setIsGenerating(true);
    } else {
      setIsLoading(true);
    }
    setError(null);
    try {
      // 1. Fetch Repository status first
      const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
      if (!repoRes.ok) throw new Error('Repository details not found.');
      const repoData = await repoRes.json();
      setRepo(repoData);
      
      if (repoData.knowledge_summary?.history) {
        setHistory(repoData.knowledge_summary.history);
      }
      
      // 2. Bypass assessment loading if repo is not ready or is indexing
      if (repoData.status !== 'ready') {
        setIsLoading(false);
        setIsGenerating(false);
        return;
      }
      
      if (repoData.knowledge_status === 'indexing' || repoData.knowledge_status === 'pending') {
        setIsLoading(false);
        setIsGenerating(false);
        return;
      }
      
      // 3. Fetch Assessment
      const url = `${apiUrl}/repositories/${repoId}/assessment`;
      const method = forceGenerate ? 'POST' : 'GET';
      const res = await fetch(url, { method });
      
      const data = await res.json();
      if (!res.ok) {
        throw data.detail || { problem: "Failed to compile assessment", reason: "An unknown error occurred." };
      }
      
      setAssessment(data);
      
      // Initialize simulator fixes
      const initFixes: Record<string, boolean> = {};
      if (data.roadmap) {
        data.roadmap.forEach((item: RoadmapItem) => {
          initFixes[item.id] = false;
        });
      }
      setSimulatedFixes(initFixes);
      
      setIsLoading(false);
      setIsGenerating(false);
    } catch (err: any) {
      setError(err);
      setIsLoading(false);
      setIsGenerating(false);
    }
  }, [apiUrl, repoId]);

  useEffect(() => {
    fetchAssessment(false);
  }, [fetchAssessment]);

  // Set up polling while indexing is active to unlock assessment automatically (Component 4)
  useEffect(() => {
    if (repo && (repo.knowledge_status === 'indexing' || repo.knowledge_status === 'pending' || repo.status !== 'ready')) {
      const interval = setInterval(async () => {
        const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
        if (repoRes.ok) {
          const repoData = await repoRes.json();
          setRepo(repoData);
          if (repoData.status === 'ready' && repoData.knowledge_status === 'completed') {
            clearInterval(interval);
            fetchAssessment(false);
          }
        }
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [repo, repoId, apiUrl, fetchAssessment]);

  const handleGenerate = async () => {
    await fetchAssessment(true);
  };

  // Score simulator: predicted score updates instantly
  const predictedScore = useMemo(() => {
    if (!assessment) return 0;
    const initialScore = assessment.scores.overall;
    let extraPoints = 0;
    assessment.roadmap.forEach(item => {
      if (simulatedFixes[item.id]) {
        extraPoints += item.gain;
      }
    });
    return Math.min(100, initialScore + extraPoints);
  }, [assessment, simulatedFixes]);

  // SVG Custom Radar Chart coords calculation
  const radarChartSvg = useMemo(() => {
    if (!assessment) return null;
    const dims = [
      { key: 'architecture', label: 'Architecture' },
      { key: 'maintainability', label: 'Maintainability' },
      { key: 'organization', label: 'Organization' },
      { key: 'consistency', label: 'Consistency' },
      { key: 'security', label: 'Security' },
      { key: 'testing', label: 'Testing' },
      { key: 'documentation', label: 'Documentation' }
    ];
    
    const size = 300;
    const center = size / 2;
    const r = center - 40;
    const totalPoints = dims.length;
    
    const gridBands = [0.2, 0.4, 0.6, 0.8, 1.0];
    const gridPaths = gridBands.map(band => {
      const points = [];
      for (let i = 0; i < totalPoints; i++) {
        const angle = (i * 2 * Math.PI) / totalPoints - Math.PI / 2;
        const x = center + r * band * Math.cos(angle);
        const y = center + r * band * Math.sin(angle);
        points.push(`${x},${y}`);
      }
      return points.join(' ');
    });
    
    const axes = dims.map((dim, i) => {
      const angle = (i * 2 * Math.PI) / totalPoints - Math.PI / 2;
      const xOuter = center + r * Math.cos(angle);
      const yOuter = center + r * Math.sin(angle);
      
      const labelOffset = 22;
      const xLabel = center + (r + labelOffset) * Math.cos(angle);
      const yLabel = center + (r + labelOffset) * Math.sin(angle) + 4;
      
      const score = assessment.scores.dimensions[dim.key]?.score || 0;
      const xScore = center + r * (score / 100) * Math.cos(angle);
      const yScore = center + r * (score / 100) * Math.sin(angle);
      
      return {
        key: dim.key,
        label: dim.label,
        xOuter,
        yOuter,
        xLabel,
        yLabel,
        xScore,
        yScore,
        score
      };
    });
    
    const dataPolygonPath = axes.map(a => `${a.xScore},${a.yScore}`).join(' ');
    
    return (
      <svg className="w-full max-w-[320px] h-[320px] mx-auto text-gray-700" viewBox={`0 0 ${size} ${size}`}>
        {gridPaths.map((path, i) => (
          <polygon key={i} points={path} fill="none" stroke="#1f2937" strokeWidth="1" />
        ))}
        {axes.map((axis, i) => (
          <line key={i} x1={center} y1={center} x2={axis.xOuter} y2={axis.yOuter} stroke="#1f2937" strokeWidth="1" />
        ))}
        <polygon points={dataPolygonPath} fill="rgba(139, 92, 246, 0.15)" stroke="#8b5cf6" strokeWidth="2.5" />
        {axes.map((axis, i) => (
          <circle key={i} cx={axis.xScore} cy={axis.yScore} r="4.5" className="fill-violet-400 stroke-darkbg-950 stroke-2" />
        ))}
        {axes.map((axis, i) => {
          let textAnchor: "start" | "middle" | "end" = 'middle';
          if (axis.xLabel < center - 10) textAnchor = 'end';
          if (axis.xLabel > center + 10) textAnchor = 'start';
          return (
            <text
              key={i}
              x={axis.xLabel}
              y={axis.yLabel}
              textAnchor={textAnchor}
              className="text-[9px] font-bold fill-gray-400 hover:fill-white cursor-pointer transition-colors"
              onClick={() => setExpandedDimension(expandedDimension === axis.key ? null : axis.key)}
            >
              {axis.label} ({axis.score})
            </text>
          );
        })}
      </svg>
    );
  }, [assessment, expandedDimension]);

  // 1. Ingestion Pipeline Active
  if (repo && repo.status !== 'ready') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-darkbg-950 text-gray-100 font-sans">
        <div className="max-w-md w-full p-6 bg-darkbg-900 border border-gray-900 rounded-2xl space-y-6 shadow-2xl">
          <div className="text-center space-y-2">
            <Loader2 className="w-8 h-8 animate-spin text-brand-500 mx-auto" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">Repository Ingestion Active</h2>
            <p className="text-xs text-gray-500">Deterministic scanning and analysis are running...</p>
          </div>
          
          <div className="bg-darkbg-950 border border-gray-950 p-4 rounded-xl space-y-3 text-xs">
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
                
                return (
                  <div key={stg.key} className="flex items-center gap-3">
                    {isCompleted ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : isRunning ? (
                      <Loader2 className="w-4 h-4 animate-spin text-brand-405" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-gray-800" />
                    )}
                    <span className={isCompleted ? 'text-gray-400' : isRunning ? 'text-white font-semibold' : 'text-gray-600'}>
                      {stg.label}
                    </span>
                  </div>
                );
              });
            })()}
          </div>
          <button
            onClick={() => router.push(`/repositories/${repoId}`)}
            className="w-full py-2.5 px-4 bg-gray-900 border border-gray-800 hover:bg-gray-800 text-white rounded-xl text-xs font-semibold transition-all"
          >
            Back to Overview
          </button>
        </div>
      </div>
    );
  }

  // 2. Knowledge Indexing in Progress (Component 4)
  if (repo && (repo.knowledge_status === 'indexing' || repo.knowledge_status === 'pending')) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-darkbg-950 px-4 font-sans text-center">
        <div className="max-w-md w-full bg-darkbg-900 border border-gray-900 p-8 rounded-2xl shadow-xl space-y-6">
          <Loader2 className="w-10 h-10 animate-spin text-brand-450 mx-auto" />
          <div className="space-y-2">
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center justify-center gap-2">
              AI Indexing in Progress
            </h2>
            <p className="text-xs text-gray-400">
              The vector knowledge index is currently compiling. The narrative review and SOLID principles analysis will unlock immediately after completion.
            </p>
          </div>
          <div className="bg-darkbg-950/40 border border-gray-900/60 p-4 rounded-xl text-xs space-y-2 text-left">
            <div className="flex justify-between items-center text-gray-400">
              <span>Knowledge Base Indexing</span>
              <span className="text-[10px] text-brand-400 font-bold uppercase tracking-wider animate-pulse">Running</span>
            </div>
            <div className="flex justify-between items-center text-gray-500">
              <span>Narrative Assessment Compilation</span>
              <span>Pending</span>
            </div>
          </div>
          <p className="text-[10px] text-gray-600 font-mono">Current Stage: {repo.status_message || 'Indexing'}</p>
          <div className="flex gap-2">
            <button
              onClick={() => router.push(`/repositories/${repoId}`)}
              className="w-full py-2.5 px-4 bg-gray-900 border border-gray-800 hover:bg-gray-850 text-white rounded-xl text-xs font-semibold transition-all"
            >
              Back to Overview
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 3. Knowledge Indexing Failed (Component 8 & Retry options)
  if (repo && (repo.knowledge_status === 'failed' || repo.knowledge_status === 'interrupted')) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4 font-sans text-center">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-8 rounded-2xl shadow-xl space-y-6">
          <ShieldAlert className="w-10 h-10 text-rose-500 mx-auto" />
          <div className="space-y-2">
            <h2 className="text-lg font-bold text-textPrimary tracking-tight">AI Indexing Failed</h2>
            <p className="text-xs text-textSecondary text-left">
              The AI Knowledge Base indexing could not be completed. Re-indexing is required to query the AI Mentor and generate SOLID principles and narrative reviews.
            </p>
          </div>
          <div className="bg-slate-50 dark:bg-zinc-950 border border-borderPrimary p-4 rounded-xl text-left">
            <span className="text-textSecondary font-bold block mb-1 text-[10px]">Error Details:</span>
            <p className="text-rose-500 font-mono text-[10px] leading-relaxed break-all">
              {repo.error_message || 'Timeout exceeded during embedding generation.'}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => router.push(`/repositories/${repoId}`)}
              className="flex-1 py-2.5 px-4 bg-slate-100 dark:bg-zinc-900 border border-borderPrimary hover:bg-slate-200 dark:hover:bg-zinc-800 text-textPrimary rounded-xl text-xs font-semibold transition-all"
            >
              Back to Overview
            </button>
            <button
              disabled={isRetryingKb}
              onClick={handleRetryKb}
              className="flex-1 py-2.5 px-4 bg-rose-600 hover:bg-rose-550 text-white text-xs font-semibold rounded-xl transition-all flex items-center justify-center gap-1.5"
            >
              {isRetryingKb && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Retry Indexing
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 4. Default loading spinner
  if (isLoading || isGenerating) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary text-textPrimary font-sans">
        <div className="text-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 mx-auto" />
          <p className="text-sm text-textSecondary">Loading Assessment...</p>
        </div>
      </div>
    );
  }

  // Pending Assessment State or API error (Task 13 Custom error banner)
  if (error || !assessment) {
    const errorDetail = error || {};
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4 font-sans">
        <div className="max-w-lg w-full bg-bgSecondary border border-borderPrimary p-6 rounded-2xl shadow-xl space-y-6">
          <div className="flex items-center gap-3 pb-3 border-b border-borderPrimary">
            <AlertCircle className="w-6 h-6 text-rose-500" />
            <h2 className="text-md font-bold text-textPrimary uppercase tracking-wider">
              {errorDetail.problem || 'Assessment Compilation Failed'}
            </h2>
          </div>
          <div className="space-y-4 text-xs leading-relaxed">
            <div>
              <span className="text-textSecondary font-bold block mb-1">Reason:</span>
              <p className="bg-slate-50 dark:bg-zinc-950 border border-borderPrimary p-3 rounded-xl text-rose-500 font-mono">
                {errorDetail.reason || 'An unknown network error has occurred during vector compilation.'}
              </p>
            </div>
            <div>
              <span className="text-textSecondary font-bold block mb-1">Suggested Fix:</span>
              <p className="text-textSecondary">
                {errorDetail.suggested_fix || 'Ensure that the backend container is running, the database is reachable, and the Groq API key is valid.'}
              </p>
            </div>
            {errorDetail.log_id && (
              <div className="flex justify-between text-[10px] text-textSecondary font-mono">
                <span>Log ID: {errorDetail.log_id}</span>
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => router.push(`/repositories/${repoId}`)}
              className="flex-grow py-2.5 px-4 bg-slate-100 dark:bg-zinc-900 border border-borderPrimary hover:bg-slate-200 dark:hover:bg-zinc-800 text-textPrimary rounded-xl text-xs font-semibold transition-all"
            >
              Back to Overview
            </button>
            <button
              onClick={handleGenerate}
              className="flex-grow py-2.5 px-4 bg-brand-500 hover:bg-brand-600 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Retry Compilation
            </button>
          </div>
        </div>
      </div>
    );
  }

  const { overall, grade } = assessment.scores;
  
  // Percentile Estimation (Component 8)
  const getPercentile = (score: number) => {
    if (score >= 95) return "Top 2% Enterprise Grade";
    if (score >= 90) return "Top 8% Open Source Quality";
    if (score >= 80) return "Top 18% Portfolio Quality";
    if (score >= 70) return "Top 35% Production Ready";
    return "Typical Student/MVP Project";
  };

  const getGradeStyle = (letter: string) => {
    if (letter.startsWith('A')) return 'border-emerald-500/30 text-emerald-600 dark:text-emerald-450 bg-emerald-500/5';
    if (letter.startsWith('B')) return 'border-violet-500/30 text-violet-650 dark:text-violet-400 bg-violet-500/5';
    if (letter.startsWith('C')) return 'border-amber-500/30 text-amber-650 dark:text-amber-400 bg-amber-500/5';
    return 'border-rose-500/30 text-rose-650 dark:text-rose-450 bg-rose-500/5';
  };

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans selection:bg-brand-500/20 transition-colors duration-300">
      {/* Background glow */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-brand-500/5 rounded-full blur-[120px] pointer-events-none -z-10 animate-pulse" />

      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="assessment" 
      />

      {/* Main Workspace */}
      <main className="w-full max-w-[1700px] mx-auto px-4 sm:px-6 lg:px-12 pt-[92px] pb-6 space-y-6 flex-grow">

        {/* OVERALL SCORE & RADAR CHART & EXECUTIVE NARRATIVE */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 flex flex-col items-center justify-between space-y-6">
            <h3 className="text-xs text-gray-500 uppercase font-bold tracking-wider text-center w-full">Overall Assessment</h3>
            
            <div className="relative w-36 h-36 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path className="text-gray-800/80" strokeWidth="2.5" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path className="text-brand-500" strokeDasharray={`${overall}, 100`} strokeWidth="2.5" strokeLinecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <div className="absolute text-center space-y-0.5">
                <span className="text-4xl font-extrabold text-white font-mono">{overall}</span>
                <span className="text-xs text-gray-500 block">/ 100</span>
              </div>
            </div>

            <div className="text-center space-y-2 w-full">
              <div className="flex justify-center gap-3">
                <span className={`px-4 py-1.5 rounded-full border text-sm font-bold tracking-wider ${getGradeStyle(grade)}`}>
                  Grade {grade}
                </span>
              </div>
              <p className="text-[10px] text-brand-400 font-bold uppercase tracking-wider">
                {getPercentile(overall)}
              </p>
            </div>
          </div>

          <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 flex flex-col items-center justify-center">
            <h3 className="text-xs text-gray-500 uppercase font-bold tracking-wider text-center w-full mb-2">Dimensions Radar Graph</h3>
            {radarChartSvg}
          </div>

          <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <h3 className="text-xs text-brand-400 uppercase font-bold tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-4 h-4" /> Executive Summary
              </h3>
              <p className="text-xs text-gray-300 leading-relaxed font-medium">
                {assessment.narrative.executive_summary}
              </p>
            </div>
            <div className="border-t border-gray-900 pt-4 flex justify-between items-center text-[10px] text-gray-500">
              <span>Engine: {assessment.metadata.engine_version}</span>
              <span>Model: {assessment.metadata.llm_model}</span>
            </div>
          </div>
        </div>

        {/* WHY THIS REPOSITORY SCORED X/100 (LEDGER WITH RULES & WHY EXISTS) */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 space-y-6">
            <div className="flex justify-between items-center border-b border-gray-900 pb-3">
              <h3 className="text-xs text-gray-400 uppercase font-bold tracking-wider flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-brand-400" /> Why This Repository Scored {overall}/100
              </h3>
              <span className="text-[10px] text-gray-500">Scoring Ledger</span>
            </div>

            {/* Score Ledger Steps (Component 1) */}
            <div className="space-y-3 font-mono text-xs">
              {assessment.explanations.overall_breakdown.map((step, idx) => {
                const isDeduction = step.symbol === '-';
                const isBonus = step.symbol === '+';
                const color = isDeduction ? 'text-rose-400' : isBonus ? 'text-emerald-400' : 'text-white';
                
                return (
                  <div key={idx} className="p-3 bg-darkbg-950/20 border border-gray-900 rounded-xl space-y-2 hover:border-gray-800 transition-colors">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-200 font-sans font-semibold flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${isDeduction ? 'bg-rose-500' : isBonus ? 'bg-emerald-500' : 'bg-white'}`} />
                        {step.name}
                      </span>
                      <span className={`font-bold ${color}`}>
                        {step.symbol === 'start' ? '' : step.symbol}{Math.abs(step.value)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Interactive Score Simulator (Component 7) */}
          <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 space-y-6 flex flex-col justify-between">
            <div className="space-y-4">
              <h3 className="text-xs text-gray-400 uppercase font-bold tracking-wider flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-indigo-400" /> Score Simulator Sandbox
              </h3>
              <p className="text-[11px] text-gray-500 leading-normal">
                Toggle refactoring recommendations to forecast score gains. Hypothetical calculations are client-side only.
              </p>

              <div className="space-y-3 pt-2 max-h-[220px] overflow-y-auto pr-1">
                {assessment.roadmap.map(item => (
                  <label key={item.id} className="flex items-start gap-3 p-3 bg-darkbg-950/50 border border-gray-900 rounded-xl cursor-pointer hover:border-gray-800 transition-all select-none">
                    <input
                      type="checkbox"
                      className="mt-0.5 rounded border-gray-800 text-brand-500 focus:ring-brand-500/30 bg-gray-950"
                      checked={simulatedFixes[item.id] || false}
                      onChange={(e) => setSimulatedFixes({ ...simulatedFixes, [item.id]: e.target.checked })}
                    />
                    <div className="text-xs leading-normal">
                      <span className="font-semibold text-gray-300 block">{item.title}</span>
                      <span className="text-[9px] text-indigo-400 block font-mono mt-0.5">Principle: {item.engineering_principle}</span>
                      <span className="text-[10px] text-emerald-400 font-mono mt-0.5 block">+{item.gain} points gain ({item.priority} Priority)</span>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div className="border-t border-gray-900 pt-5 space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-400 font-semibold">Simulated Score Result:</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-gray-500 font-mono">{overall}</span>
                  <span className="text-xs text-gray-600">→</span>
                  <span className={`text-2xl font-extrabold font-mono ${predictedScore > overall ? 'text-brand-400' : 'text-white'}`}>{predictedScore}</span>
                </div>
              </div>
              <div className="w-full bg-gray-900 h-1.5 rounded-full overflow-hidden">
                <div className="bg-brand-500 h-full transition-all duration-300" style={{ width: `${predictedScore}%` }} />
              </div>
            </div>
          </div>
        </div>

        {/* SOLID PRINCIPLES ENGINE (Component 4) */}
        {assessment.principles && assessment.principles.length > 0 && (
          <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 space-y-4">
            <h3 className="text-xs text-gray-400 uppercase font-bold tracking-wider flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-brand-400" /> Engineering Principles engine
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {assessment.principles.map((pr, i) => (
                <div key={i} className="p-4 bg-darkbg-950/20 border border-gray-900 rounded-xl space-y-3 flex flex-col justify-between">
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-bold text-white">{pr.principle}</span>
                      <span className={`px-2 py-0.5 rounded font-mono text-[9px] font-bold uppercase tracking-wider ${
                        pr.status === 'passed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>{pr.status}</span>
                    </div>
                    <p className="text-[11px] text-gray-400 leading-normal">{pr.explanation}</p>
                    {pr.status !== 'passed' && (
                      <div className="space-y-1 pt-1.5 text-[10px] text-gray-500">
                        <p><span className="font-bold text-gray-450 block">Why it matters:</span> {pr.why_it_matters}</p>
                        <p><span className="font-bold text-gray-450 block">Suggested Fix:</span> {pr.how_to_fix}</p>
                        {pr.evidence.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-1.5">
                            {pr.evidence.map(f => (
                              <span key={f} className="px-2 py-0.5 bg-darkbg-950 border border-gray-900 text-gray-400 font-mono text-[8px] rounded select-all truncate max-w-[150px]" title={f}>{f.split('/').pop()}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  
                  {/* Learn More link triggering Component 11 learning drawer */}
                  <button
                    onClick={() => {
                      const key = pr.principle.toLowerCase().includes("single responsibility") ? "srp" :
                                  pr.principle.toLowerCase().includes("dependency inversion") ? "dip" :
                                  pr.principle.toLowerCase().includes("dry") ? "dry" : "coupling";
                      setActiveLearningConcept(key);
                    }}
                    className="w-fit text-[10px] text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1 mt-2"
                  >
                    Learn More <HelpIcon className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* DETAILED DIMENSIONS DRILL-DOWN */}
        <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 space-y-4">
          <h3 className="text-xs text-gray-400 uppercase font-bold tracking-wider">Detailed Dimensions Breakdown</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(assessment.explanations.explanations).map(([dim, data]) => {
              const isExpanded = expandedDimension === dim;
              
              return (
                <div key={dim} className="border border-gray-900 hover:border-gray-800 rounded-xl overflow-hidden bg-darkbg-950/20 flex flex-col justify-between transition-colors">
                  <div className="p-4 flex justify-between items-center border-b border-gray-900/60 bg-darkbg-950/40">
                    <span className="text-xs font-bold text-white capitalize">{dim}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-gray-500 font-semibold">Grade {data.grade}</span>
                      <span className="text-xs font-bold text-brand-400 font-mono">{data.score}</span>
                    </div>
                  </div>
                  
                  <div className="p-4 space-y-3">
                    <div className="flex justify-between text-[11px] text-gray-500">
                      <span>Bonuses</span>
                      <span className="text-emerald-400 font-bold font-mono">+{data.bonuses.length}</span>
                    </div>
                    <div className="flex justify-between text-[11px] text-gray-500">
                      <span>Deductions</span>
                      <span className="text-rose-400 font-bold font-mono">-{data.deductions.length}</span>
                    </div>
                    
                    <button
                      onClick={() => setExpandedDimension(isExpanded ? null : dim)}
                      className="w-full py-1.5 border border-gray-900 hover:border-gray-800 rounded-lg text-[10px] text-gray-400 hover:text-white transition-all flex items-center justify-center gap-1 font-semibold"
                    >
                      {isExpanded ? 'Collapse Ledger' : 'Expand Ledger'}
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                  
                  {isExpanded && (
                    <div className="p-4 border-t border-gray-900 bg-darkbg-950/80 space-y-3 text-xs leading-relaxed max-h-[300px] overflow-y-auto">
                      {data.bonuses.map((bonus, i) => (
                        <div key={i} className="p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-xl space-y-1">
                          <div className="flex justify-between items-center">
                            <span className="font-bold text-emerald-400">{bonus.name}</span>
                            <span className="font-bold text-emerald-400 font-mono">+{bonus.score}</span>
                          </div>
                          <p className="text-[11px] text-gray-400 leading-normal">{bonus.reason}</p>
                        </div>
                      ))}
                      
                      {data.deductions.map((ded, i) => (
                        <div key={i} className="p-3 bg-rose-500/5 border border-rose-500/10 rounded-xl space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="font-bold text-rose-400">{ded.name}</span>
                            <span className="font-bold text-rose-400 font-mono">{ded.score}</span>
                          </div>
                          <p className="text-[11px] text-gray-400 leading-normal">{ded.reason}</p>
                          {ded.affected_files && ded.affected_files.length > 0 && (
                            <div className="pt-1.5 border-t border-rose-500/10 space-y-1 text-[10px]">
                              <span className="text-gray-500 font-bold block">Affected Files:</span>
                              <div className="flex flex-wrap gap-1.5">
                                {ded.affected_files.map(f => (
                                  <span
                                    key={f}
                                    onClick={() => setSelectedEvidence({ type: 'file', path: f, line: 1, detail: ded.reason })}
                                    className="px-2 py-0.5 bg-darkbg-950 border border-gray-900 hover:border-gray-800 rounded text-gray-450 hover:text-white cursor-pointer truncate font-mono text-[9px] transition-colors"
                                  >
                                    {f.split('/').pop()}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* EVOLUTION & TIMELINE & BENCHMARKS */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Evolution tracking (Component 9) */}
          <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 space-y-4 flex flex-col justify-between">
            <div className="space-y-3">
              <h3 className="text-xs text-gray-400 uppercase font-bold tracking-wider flex items-center gap-1.5">
                <History className="w-4 h-4 text-brand-400" /> Repository Evolution History
              </h3>
              
              <div className="space-y-2.5 max-h-[160px] overflow-y-auto pr-1">
                {history.map((h, i) => (
                  <div key={i} className="flex justify-between items-center p-2.5 bg-darkbg-950/40 border border-gray-900 rounded-xl text-xs">
                    <div className="space-y-0.5">
                      <span className="font-bold text-gray-300">Run #{i + 1}</span>
                      <span className="text-[10px] text-gray-505 block">{new Date(h.generated_at).toLocaleDateString()}</span>
                    </div>
                    <span className="font-extrabold text-white font-mono text-sm">{h.overall_score}</span>
                  </div>
                ))}
                {history.length <= 1 && (
                  <p className="text-xs text-gray-500 italic">Evolution tracking begins after subsequent assessment scans.</p>
                )}
              </div>
            </div>
            
            {history.length > 1 && (
              <div className="border-t border-gray-900 pt-3 flex justify-between items-center text-xs">
                <span className="text-gray-450">Delta from last run:</span>
                <span className={`font-bold font-mono ${
                  history[history.length - 1].overall_score >= history[history.length - 2].overall_score ? 'text-emerald-400' : 'text-rose-400'
                }`}>
                  {history[history.length - 1].overall_score - history[history.length - 2].overall_score >= 0 ? '+' : ''}
                  {history[history.length - 1].overall_score - history[history.length - 2].overall_score} points
                </span>
              </div>
            )}
          </div>

          {/* Explainable Confidence checklist (Component 6) */}
          <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 space-y-4">
            <h3 className="text-xs text-gray-400 uppercase font-bold tracking-wider flex items-center gap-1.5">
              <Bookmark className="w-4 h-4 text-emerald-400" /> Assessment Verification Status: Complete
            </h3>
            <div className="space-y-2 text-xs leading-normal">
              {assessment.confidence.reasons.map((r, i) => (
                <div key={i} className="flex items-center gap-2 text-gray-400 font-medium">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{r}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Benchmarks comparison (Component 8) */}
          <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 space-y-5">
            <h3 className="text-xs text-gray-400 uppercase font-bold tracking-wider flex items-center gap-1.5">
              <BarChart3 className="w-4 h-4 text-brand-400" /> Grading Benchmarks
            </h3>
            
            <div className="space-y-3">
              {[
                { name: "Enterprise Quality", min: 90, max: 100, desc: "Slight technical debt, production-grade security." },
                { name: "Production Repository", min: 75, max: 89, desc: "Balanced metrics, acceptable coverage." },
                { name: "Student Portfolio", min: 55, max: 74, desc: "Typically contains logic duplication, low tests." }
              ].map(val => {
                const isActive = overall >= val.min && overall <= val.max;
                return (
                  <div key={val.name} className={`p-2.5 rounded-xl border text-[11px] ${isActive ? 'bg-brand-500/5 border-brand-500/25' : 'bg-darkbg-950/20 border-gray-900'} space-y-0.5`}>
                    <div className="flex justify-between items-center">
                      <span className={`font-bold ${isActive ? 'text-brand-400' : 'text-gray-300'}`}>{val.name}</span>
                      <span className="font-bold font-mono text-gray-500 text-[10px]">{val.min}–{val.max}</span>
                    </div>
                    <p className="text-[10px] text-gray-500 leading-normal">{val.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* FULL AI REVIEW NARRATIVE (Component 12) */}
        <div className="bg-darkbg-900/40 border border-gray-900 rounded-2xl p-6 space-y-6">
          <h3 className="text-xs text-gray-400 uppercase font-bold tracking-wider flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-brand-400" /> Full Engineering Assessment Narrative
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs leading-relaxed text-gray-300">
            <div className="space-y-4">
              <div className="space-y-1.5 p-4 bg-darkbg-950/30 border border-gray-900 rounded-2xl">
                <span className="text-[10px] uppercase font-bold text-brand-400 tracking-wider block border-b border-gray-900 pb-1 mb-2">Architecture Review</span>
                <p>{assessment.narrative.architecture_review}</p>
              </div>
              <div className="space-y-1.5 p-4 bg-darkbg-950/30 border border-gray-900 rounded-2xl">
                <span className="text-[10px] uppercase font-bold text-brand-400 tracking-wider block border-b border-gray-900 pb-1 mb-2">Maintainability Review</span>
                <p>{assessment.narrative.maintainability_review}</p>
              </div>
              <div className="space-y-1.5 p-4 bg-darkbg-950/30 border border-gray-900 rounded-2xl">
                <span className="text-[10px] uppercase font-bold text-brand-400 tracking-wider block border-b border-gray-900 pb-1 mb-2">Security Review</span>
                <p>{assessment.narrative.security_review}</p>
              </div>
              <div className="space-y-1.5 p-4 bg-darkbg-950/30 border border-gray-900 rounded-2xl">
                <span className="text-[10px] uppercase font-bold text-brand-400 tracking-wider block border-b border-gray-900 pb-1 mb-2">Engineering Strengths</span>
                <p>{assessment.narrative.engineering_strengths}</p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5 p-4 bg-darkbg-950/30 border border-gray-900 rounded-2xl">
                <span className="text-[10px] uppercase font-bold text-brand-400 tracking-wider block border-b border-gray-900 pb-1 mb-2">Documentation Review</span>
                <p>{assessment.narrative.documentation_review}</p>
              </div>
              <div className="space-y-1.5 p-4 bg-darkbg-950/30 border border-gray-900 rounded-2xl">
                <span className="text-[10px] uppercase font-bold text-brand-400 tracking-wider block border-b border-gray-900 pb-1 mb-2">Testing Review</span>
                <p>{assessment.narrative.testing_review}</p>
              </div>
              <div className="space-y-1.5 p-4 bg-darkbg-950/30 border border-gray-900 rounded-2xl">
                <span className="text-[10px] uppercase font-bold text-brand-400 tracking-wider block border-b border-gray-900 pb-1 mb-2">Risk Assessment</span>
                <p>{assessment.narrative.risk_assessment}</p>
              </div>
              <div className="space-y-1.5 p-4 bg-darkbg-950/30 border border-gray-900 rounded-2xl">
                <span className="text-[10px] uppercase font-bold text-brand-400 tracking-wider block border-b border-gray-900 pb-1 mb-2">Engineering Weaknesses</span>
                <p>{assessment.narrative.engineering_weaknesses}</p>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 col-span-1 md:col-span-2">
              <div className="p-4 bg-darkbg-950/40 border border-gray-900 rounded-2xl space-y-1">
                <span className="text-[9px] uppercase font-bold text-gray-500 tracking-wider">Production Readiness</span>
                <p className="text-gray-250 font-medium">{assessment.narrative.production_readiness}</p>
              </div>
              <div className="p-4 bg-darkbg-950/40 border border-gray-900 rounded-2xl space-y-1">
                <span className="text-[9px] uppercase font-bold text-gray-500 tracking-wider">Engineering Maturity</span>
                <p className="text-gray-250 font-medium">{assessment.narrative.engineering_maturity}</p>
              </div>
            </div>
            
            <div className="col-span-1 md:col-span-2 space-y-1.5 p-5 bg-brand-500/5 border border-brand-500/10 rounded-2xl">
              <span className="text-[10px] uppercase font-bold text-brand-400 tracking-wider">Final Verdict</span>
              <p className="text-gray-200 font-medium">{assessment.narrative.final_verdict}</p>
            </div>
          </div>
        </div>

        {/* EVIDENCE INSPECTOR DRAWER */}
        {selectedEvidence && (
          <div className="fixed bottom-6 right-6 max-w-sm w-full bg-darkbg-900 border border-gray-800 rounded-2xl shadow-2xl p-5 space-y-4 z-50 animate-slide-in">
            <div className="flex justify-between items-center border-b border-gray-800 pb-2">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Info className="w-4 h-4 text-brand-400" /> Evidence Inspector
              </span>
              <button onClick={() => setSelectedEvidence(null)} className="text-xs text-gray-500 hover:text-white">Close</button>
            </div>
            
            <div className="space-y-2 text-xs">
              <div className="flex justify-between text-[10px] text-gray-500 font-mono">
                <span>Type: {selectedEvidence.type}</span>
                {selectedEvidence.line > 0 && <span>Line: {selectedEvidence.line}</span>}
              </div>
              <div className="p-3 bg-darkbg-950 border border-gray-950 rounded-xl font-mono text-[10px] text-gray-300 break-all select-all">
                {selectedEvidence.path || 'Root Project'}
              </div>
              <p className="text-gray-450 leading-normal text-[11px] pt-1">{selectedEvidence.detail}</p>
            </div>
            
            {selectedEvidence.path && (
              <button
                disabled={!resolvedFileId}
                onClick={() => {
                  if (resolvedFileId) {
                    router.push(`/repositories/${repoId}/files/${resolvedFileId}?line=${selectedEvidence.line}`);
                  }
                }}
                className="w-full py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-xl text-[10px] font-semibold transition-all flex items-center justify-center gap-1.5 disabled:opacity-45"
              >
                {resolvedFileId ? "Open in File Inspector" : "Resolving File..."}
              </button>
            )}
          </div>
        )}

        {/* INTERACTIVE LEARNING DRAWER (Component 11) */}
        {activeLearningConcept && LEARNING_DATA[activeLearningConcept] && (
          <div className="fixed top-0 right-0 h-screen max-w-lg w-full bg-darkbg-900 border-l border-gray-900 shadow-2xl p-6 overflow-y-auto space-y-6 z-50 animate-slide-in-right">
            <div className="flex justify-between items-center border-b border-gray-900 pb-3">
              <h2 className="text-md font-extrabold text-white flex items-center gap-1.5">
                <HelpIcon className="w-5 h-5 text-indigo-400" /> Learn: {LEARNING_DATA[activeLearningConcept].title}
              </h2>
              <button
                onClick={() => setActiveLearningConcept(null)}
                className="p-1 text-gray-500 hover:text-white rounded-lg border border-gray-800 hover:border-gray-700 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            <div className="space-y-5 text-xs leading-relaxed">
              <div className="space-y-1">
                <span className="text-[10px] uppercase font-bold text-gray-500">Definition</span>
                <p className="text-gray-300 text-[11px] leading-relaxed">{LEARNING_DATA[activeLearningConcept].definition}</p>
              </div>
              
              <div className="space-y-2">
                <span className="text-[10px] uppercase font-bold text-gray-500">Code Comparison</span>
                <div className="grid grid-cols-1 gap-3">
                  <div className="p-3 bg-red-950/10 border border-red-500/10 rounded-xl">
                    <span className="text-[9px] uppercase font-bold text-rose-400 block mb-1">Bad Pattern</span>
                    <pre className="font-mono text-[9px] text-rose-350 overflow-x-auto">{LEARNING_DATA[activeLearningConcept].badExample}</pre>
                  </div>
                  <div className="p-3 bg-emerald-950/10 border border-emerald-500/10 rounded-xl">
                    <span className="text-[9px] uppercase font-bold text-emerald-400 block mb-1">Good Refactored Pattern</span>
                    <pre className="font-mono text-[9px] text-emerald-350 overflow-x-auto">{LEARNING_DATA[activeLearningConcept].goodExample}</pre>
                  </div>
                </div>
              </div>

              <div className="space-y-1.5 p-3.5 bg-darkbg-950/60 border border-gray-900 rounded-xl">
                <span className="text-[10px] uppercase font-bold text-indigo-400 block">Why Industry Uses It</span>
                <p className="text-gray-400 text-[10px] leading-normal">{LEARNING_DATA[activeLearningConcept].whyIndustryUsesIt}</p>
              </div>

              <div className="space-y-2 border-t border-gray-900 pt-4">
                <span className="text-[10px] uppercase font-bold text-gray-500 block">Recommended Readings</span>
                <ul className="list-disc pl-4 space-y-1 text-gray-450 text-[10px]">
                  {LEARNING_DATA[activeLearningConcept].recommendedReading.map((book, j) => (
                    <li key={j}>{book}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

      </main>

      <footer className="w-full text-center py-6 text-xs text-slate-500 dark:text-zinc-500 border-t border-slate-200 dark:border-zinc-900/40 mt-8 font-mono">
        Repository Mentor AI &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
}
