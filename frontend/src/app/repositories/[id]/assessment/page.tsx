'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, Loader2, Sparkles, CheckCircle2, AlertCircle,
  Shield, Cpu, FileText, ChevronDown, ChevronUp, Activity,
  RefreshCw, Layers, Bug, Zap, Check, X, FileCode, ShieldAlert,
  ArrowRight, Compass
} from 'lucide-react';

import Header from '../../../Header';
import { PageLayoutSkeleton } from '../../../components/Skeletons';
import EmptyState from '../../../components/EmptyState';

interface EvidenceRef {
  type: string;
  path: string;
  line: number;
  detail: string;
}

interface DeductionEntry {
  name: string;
  score: number;
  reason: string;
  rule_triggered: string;
  affected_files: string[];
}

interface DimensionDetails {
  score: number;
  grade: string;
  bonuses: Array<{ name: string; score: number; reason: string }>;
  deductions: DeductionEntry[];
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
  scores: {
    overall: number;
    grade: string;
    dimensions: Record<string, any>;
  };
  explanations: {
    overall_score: number;
    explanations: Record<string, DimensionDetails>;
  };
  principles?: SOLIDPrinciple[];
  narrative?: {
    executive_summary?: string;
    architecture_review?: string;
    maintainability_review?: string;
    security_review?: string;
    final_verdict?: string;
  };
}

export default function AssessmentPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  const [repo, setRepo] = useState<any>(null);
  const [assessment, setAssessment] = useState<AssessmentData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedIssueId, setExpandedIssueId] = useState<string | null>(null);
  const [expandedDimension, setExpandedDimension] = useState<string | null>(null);

  const fetchAssessment = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
      if (!repoRes.ok) throw new Error('Repository detail not found.');
      setRepo(await repoRes.json());

      const res = await fetch(`${apiUrl}/repositories/${repoId}/assessment`);
      if (res.ok) {
        setAssessment(await res.json());
      } else {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail?.reason || 'Failed to compile assessment');
      }
      setIsLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to compile assessment.');
      setIsLoading(false);
    }
  }, [apiUrl, repoId]);

  useEffect(() => {
    fetchAssessment();
  }, [fetchAssessment]);

  const getSeverityStyle = (status: string) => {
    if (status === 'passed') return 'text-good bg-good-bg border-good-border';
    if (status === 'warning') return 'text-warn bg-warn-bg border-warn-border';
    return 'text-bad bg-bad-bg border-bad-border';
  };

  if (isLoading) {
    return <PageLayoutSkeleton title="Compiling Architectural Assessment..." />;
  }

  if (error || !assessment) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4 font-sans">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-8 rounded-lg shadow-report text-center space-y-4">
          <ShieldAlert className="w-8 h-8 text-bad mx-auto" />
          <h2 className="font-serif text-xl font-bold text-textPrimary">Assessment Report Unavailable</h2>
          <p className="text-xs text-textSecondary font-mono">{error || 'Data could not be compiled.'}</p>
          <button onClick={() => router.push(`/repositories/${repoId}`)} className="py-2 px-4 rounded bg-bgTertiary text-xs font-mono font-bold">
            Return to Overview
          </button>
        </div>
      </div>
    );
  }

  const overall = assessment.scores?.overall || repo?.health_score || 0;
  const grade = assessment.scores?.grade || repo?.health_grade || 'B';
  const narrative = assessment.narrative || {};
  const principles = assessment.principles || [];
  const dimensions = assessment.explanations?.explanations || {};

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans transition-colors duration-200">
      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="assessment" 
      />

      <main className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 lg:px-10 pt-[76px] pb-16 space-y-8 flex-grow">
        
        {/* HERO / OVERVIEW */}
        <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="section-header px-2 py-0.5 rounded bg-bgTertiary border border-borderPrimary text-[10px]">
                  SECTION 02 // CODE QUALITY & SMELL AUDIT
                </span>
                <span className="text-xs font-mono text-textMuted">•</span>
                <span className="text-xs font-mono text-textSecondary">{repo?.total_smells || 0} code smells audited</span>
              </div>
              <h1 className="font-serif text-3xl sm:text-4xl font-bold text-textPrimary">
                Engineering Assessment & Principles Review
              </h1>
              <p className="text-xs sm:text-sm text-textSecondary max-w-2xl font-sans leading-relaxed">
                Evaluation of SOLID principles adherence, cognitive complexity distribution, and structural code smells.
              </p>
            </div>

            {/* Score Stamp */}
            <div className="shrink-0 p-4 sm:p-6 rounded border-2 border-borderStrong bg-bgPrimary text-center min-w-[160px] shadow-report">
              <span className="section-header text-[9px] block">ASSESSMENT SCORE</span>
              <div className="inspection-stamp text-5xl font-black text-textPrimary mt-1">
                {overall}
              </div>
              <span className="text-[10px] font-mono text-textSecondary block mt-0.5 font-bold">
                GRADE {grade}
              </span>
            </div>
          </div>

          {/* Executive Verdict Callout */}
          {narrative.executive_summary && (
            <div className="mt-6 pt-6 border-t border-borderPrimary border-l-2 border-l-signal pl-4 py-1">
              <span className="section-header block text-[9px]">EXECUTIVE SUMMARY VERDICT</span>
              <p className="text-xs sm:text-sm text-textPrimary leading-relaxed font-sans mt-1">
                {narrative.executive_summary}
              </p>
            </div>
          )}
        </section>

        {/* DIMENSIONS CARDS */}
        {Object.keys(dimensions).length > 0 && (
          <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report space-y-4">
            <span className="section-header">QUALITY DIMENSIONS</span>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
              {Object.entries(dimensions).map(([dim, data]) => (
                <div key={dim} className="p-3 bg-bgPrimary border border-borderPrimary rounded space-y-1">
                  <div className="flex justify-between items-center text-[10px] text-textMuted uppercase">
                    <span>{dim}</span>
                    <span className="font-bold text-textPrimary">Grade {data.grade}</span>
                  </div>
                  <div className="text-2xl font-black text-textPrimary">{data.score}</div>
                  <div className="flex justify-between text-[10px] text-textSecondary pt-1 border-t border-borderPrimary">
                    <span className="text-good">+{data.bonuses?.length || 0} bonuses</span>
                    <span className="text-bad">-{data.deductions?.length || 0} deductions</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ENGINEERING PRINCIPLES / SMELLS (ROW WITH SEVERITY, FILE, WHY IT MATTERS, HOW TO FIX) */}
        <section className="bg-bgSecondary border border-borderPrimary rounded-lg p-6 sm:p-8 shadow-report space-y-6">
          <div className="border-b border-borderPrimary pb-4">
            <span className="section-header">ENGINEERING DESIGN AUDIT</span>
            <h2 className="font-serif text-xl font-bold text-textPrimary mt-0.5">
              Principles & Smell Findings ({principles.length})
            </h2>
          </div>

          {principles.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="Clean Design Architecture"
              description="No architectural code smells or SOLID principle violations exceeded warning thresholds in the analyzed files."
              badge="CLEAN AUDIT"
              variant="success"
            />
          ) : (
            <div className="divide-y divide-borderPrimary">
              {principles.map((pr, idx) => {
                const isExpanded = expandedIssueId === pr.principle;
                const isPassed = pr.status === 'passed';
                return (
                  <div key={idx} className="py-4 first:pt-0 last:pb-0 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase border ${getSeverityStyle(pr.status)}`}>
                            {pr.status}
                          </span>
                          <span className="text-xs font-mono text-textPrimary font-bold">
                            {pr.principle}
                          </span>
                        </div>

                        <p className="text-xs text-textSecondary font-sans leading-relaxed pt-1">
                          {pr.explanation}
                        </p>

                        {!isPassed && pr.why_it_matters && (
                          <p className="text-xs text-textPrimary font-sans">
                            <strong>Why it matters:</strong> {pr.why_it_matters}
                          </p>
                        )}
                      </div>

                      {!isPassed && (
                        <button
                          onClick={() => setExpandedIssueId(isExpanded ? null : pr.principle)}
                          className="px-3 py-1.5 rounded bg-bgTertiary hover:bg-borderPrimary border border-borderPrimary text-textPrimary text-xs font-mono flex items-center gap-1.5 shrink-0 transition-colors"
                        >
                          <span>{isExpanded ? 'Hide Fix' : 'How to Fix'}</span>
                          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>
                      )}
                    </div>

                    {/* How to Fix Expander */}
                    {isExpanded && !isPassed && (
                      <div className="mt-3 p-4 bg-bgPrimary border border-borderPrimary rounded space-y-3 text-xs font-mono animate-fade-in">
                        <div className="space-y-1">
                          <span className="text-[10px] text-textMuted uppercase font-bold block">REMEDIATION GUIDANCE:</span>
                          <p className="text-textPrimary leading-relaxed font-sans">
                            {pr.how_to_fix || 'Refactor affected components into dedicated interfaces.'}
                          </p>
                        </div>

                        {pr.evidence && pr.evidence.length > 0 && (
                          <div>
                            <span className="text-[10px] text-textMuted uppercase font-bold block mb-1">AFFECTED FILES:</span>
                            <div className="flex flex-wrap gap-1.5">
                              {pr.evidence.map((f, fIdx) => (
                                <span key={fIdx} className="px-2 py-0.5 bg-bgTertiary border border-borderPrimary rounded text-[11px] text-textPrimary">
                                  {f.split('/').pop()}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="pt-2 flex justify-end">
                          <button
                            onClick={() => {
                              const prompt = `Explain how to refactor "${pr.principle}" in this repository. Give a concrete before/after code walkthrough.`;
                              router.push(`/repositories/${repoId}/mentor?q=${encodeURIComponent(prompt)}`);
                            }}
                            className="px-3 py-1.5 bg-signal text-white rounded text-[11px] font-bold flex items-center gap-1 hover:bg-signal-hover transition-colors"
                          >
                            <Sparkles className="w-3 h-3" />
                            <span>Ask Mentor for Architecture Advice</span>
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
