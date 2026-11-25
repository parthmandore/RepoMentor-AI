'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Sparkles, Send, Loader2, User, ChevronRight, X,
  FileCode, Terminal, HelpCircle, ArrowUpRight, Check,
  BookOpen, Shield, Flame, AlertCircle, RotateCw, Square, ShieldAlert
} from 'lucide-react';

import Header from '../../../Header';
import MarkdownRenderer from '../../../components/MarkdownRenderer';
import { PageLayoutSkeleton } from '../../../components/Skeletons';
import { trackMentorQuerySent } from '../../../lib/analytics';
import { useToast } from '../../../ToastProvider';

interface Citation {
  similarity_score: number;
  source_type: string;
  file_path: string;
  line_numbers: string;
  content: string;
  start_line: number;
  end_line: number;
}

interface Message {
  id: string;
  role: string;
  content: string;
  cited_chunks?: Citation[];
  confidence?: number;
  expert_mode?: string;
  created_at: string;
  is_error?: boolean;
  model_used?: string;
  code_index_incomplete?: boolean;
}

interface ActiveError {
  code?: number;
  message: string;
  retryable: boolean;
  retryAfter?: number;
  submittedText: string;
}

export default function RepositoryMentorPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const toast = useToast();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  const searchParams = useSearchParams();
  const queryQ = searchParams?.get('q') || '';

  const [repo, setRepo] = useState<any>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [streamStage, setStreamStage] = useState<'idle' | 'searching' | 'writing' | 'streaming' | 'error'>('idle');
  const [activeError, setActiveError] = useState<ActiveError | null>(null);
  const [streamingResponse, setStreamingResponse] = useState('');
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [starterQuestions, setStarterQuestions] = useState<string[]>([]);

  // Citation Modal Overlay State
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastSubmittedTextRef = useRef<string>('');

  useEffect(() => {
    if (queryQ) {
      setInputText(queryQ);
    }
  }, [queryQ]);

  // Handle Escape key to close citation modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedCitation) {
        setSelectedCitation(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedCitation]);

  // Initial load
  useEffect(() => {
    const initData = async () => {
      try {
        const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
        if (!repoRes.ok) throw new Error('Repository details not found.');
        const repoData = await repoRes.json();
        setRepo(repoData);

        // Fetch starter questions
        const startersRes = await fetch(`${apiUrl}/repositories/${repoId}/chat/starter-questions`);
        if (startersRes.ok) {
          const s = await startersRes.json();
          setStarterQuestions(s);
        }

        // Establish Chat Session
        const cachedSession = localStorage.getItem(`chat_session_${repoId}`);
        if (cachedSession) {
          setSessionId(cachedSession);
          fetchHistory(cachedSession);
        } else {
          await createNewSession();
        }
      } catch (err) {
        console.error('Failed to configure mentor chat:', err);
        setIsLoadingHistory(false);
      }
    };
    initData();
  }, [repoId, apiUrl]);

  // Scroll to chat bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingResponse]);

  // Poll repository status while background indexing is in progress
  useEffect(() => {
    const isIndexing = repo?.knowledge_status === 'indexing' || 
      (repo?.knowledge_summary?.chat_index_progress !== undefined && repo.knowledge_summary.chat_index_progress < 100);
      
    if (isIndexing) {
      const interval = setInterval(async () => {
        try {
          const res = await fetch(`${apiUrl}/repositories/${repoId}`);
          if (res.ok) {
            const data = await res.json();
            setRepo(data);
            if (data?.knowledge_summary?.chat_index_progress >= 100 || data?.knowledge_status === 'completed') {
              clearInterval(interval);
            }
          }
        } catch (e) {
          // ignore transient poll error
        }
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [repo?.knowledge_status, repo?.knowledge_summary?.chat_index_progress, repoId, apiUrl]);

  const createNewSession = async () => {
    setIsLoadingHistory(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/chat/sessions`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSessionId(data.session_id);
        localStorage.setItem(`chat_session_${repoId}`, data.session_id);
        setMessages([]);
      }
      setIsLoadingHistory(false);
    } catch (err) {
      console.error(err);
      setIsLoadingHistory(false);
    }
  };

  const fetchHistory = async (sessId: string) => {
    setIsLoadingHistory(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/chat/sessions/${sessId}`);
      if (res.ok) {
        setMessages(await res.json());
      }
      setIsLoadingHistory(false);
    } catch (err) {
      console.error(err);
      setIsLoadingHistory(false);
    }
  };

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsSending(false);
    setStreamStage('idle');
  };

  const handleReindexCode = async () => {
    setIsReindexing(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/knowledge/retry`, {
        method: 'POST'
      });
      if (res.ok) {
        toast.success('Knowledge Base indexing triggered. Polling progress...');
        const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
        if (repoRes.ok) {
          const updated = await repoRes.json();
          setRepo(updated);
        }
      } else {
        const errData = await res.json().catch(() => ({}));
        toast.error(errData.detail || 'Failed to trigger Knowledge Base indexing.');
      }
    } catch (e: any) {
      toast.error(e.message || 'Error communicating with server.');
    } finally {
      setIsReindexing(false);
    }
  };

  const handleSendMessage = async (textToSend?: string, isAutoRetry: boolean = false) => {
    if (isSending && !isAutoRetry) return; // Guard duplicate submissions

    const text = (textToSend || inputText).trim();
    if (!text || !sessionId) return;

    lastSubmittedTextRef.current = text;
    setInputText('');
    setActiveError(null);
    setIsSending(true);
    setStreamStage('searching');
    setStreamingResponse('');
    setStreamingCitations([]);

    // Add user message locally only if not an automatic retry
    if (!isAutoRetry) {
      const userMsg: Message = {
        id: Math.random().toString(36).substring(2, 9),
        role: 'user',
        content: text,
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, userMsg]);
      trackMentorQuerySent(repoId, false);
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const response = await fetch(`${apiUrl}/repositories/${repoId}/chat/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: text,
          expert_mode: 'General',
          explain_mode: 'Senior Engineer'
        }),
        signal: abortController.signal
      });

      if (!response.ok) {
        let errMsg = `Mentor request failed with status ${response.status}.`;
        let retryable = true;
        try {
          const errJson = await response.json();
          if (errJson.detail) errMsg = errJson.detail;
        } catch (_) {}

        if (response.status === 429) {
          const retryHeader = response.headers.get('Retry-After');
          const waitSec = retryHeader ? Math.min(6, parseInt(retryHeader, 10)) : 2;
          if (!isAutoRetry) {
            // Automatic retry once on 429 after waiting Retry-After
            setActiveError({
              code: 429,
              message: `Rate limit reached (HTTP 429). Waiting for Retry-After and retrying automatically in ${waitSec}s...`,
              retryable: false,
              submittedText: text
            });
            setTimeout(() => {
              handleSendMessage(text, true);
            }, waitSec * 1000);
            return;
          }
          errMsg = "LLM rate limit reached (HTTP 429). Please wait a moment and click Retry.";
        } else if (response.status === 500) {
          errMsg = "Internal Server Error (HTTP 500): The server encountered an error processing repository analysis facts. Please click Retry.";
        } else if (response.status === 503 || response.status === 504) {
          errMsg = "Request Timed Out (HTTP 504): The LLM or database connection took too long to respond. Please click Retry.";
        }

        setActiveError({
          code: response.status,
          message: errMsg,
          retryable: retryable,
          submittedText: text
        });
        setInputText(text); // Preserve submitted question in input box
        setStreamStage('error');
        setIsSending(false);
        return;
      }

      if (!response.body) throw new Error('ReadableStream not supported.');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let tokensReceived = 0;
      let lastModelUsed = '';
      let isIncomplete = false;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            try {
              const payload = JSON.parse(dataStr);
              if (payload.type === 'status') {
                if (payload.stage === 'synthesizing') {
                  setStreamStage('writing');
                } else if (payload.stage === 'retrieving') {
                  setStreamStage('searching');
                } else {
                  setStreamStage(payload.stage || 'streaming');
                }
              } else if (payload.type === 'token') {
                tokensReceived++;
                setStreamStage('streaming');
                setStreamingResponse(prev => prev + payload.token);
              } else if (payload.type === 'metadata') {
                setStreamingCitations(payload.citations || []);
                if (payload.model_used) lastModelUsed = payload.model_used;
                if (payload.code_index_incomplete) isIncomplete = true;
              } else if (payload.type === 'error') {
                if (payload.code === 429 && !isAutoRetry) {
                  const waitSec = payload.retry_after ? Math.min(6, Math.ceil(payload.retry_after)) : 2;
                  setActiveError({
                    code: 429,
                    message: `Rate limit reached (429). Retrying automatically in ${waitSec}s...`,
                    retryable: false,
                    submittedText: text
                  });
                  setTimeout(() => {
                    handleSendMessage(text, true);
                  }, waitSec * 1000);
                  return;
                }
                setActiveError({
                  code: payload.code,
                  message: payload.message || 'Stream was interrupted by provider.',
                  retryable: payload.retryable ?? true,
                  retryAfter: payload.retry_after,
                  submittedText: text
                });
                setStreamStage('error');
                if (tokensReceived === 0) {
                  setInputText(text); // Preserve question
                }
                break;
              }
            } catch (jsonErr) {
              // ignore incomplete JSON chunk
            }
          }
        }
      }

      fetchHistory(sessionId);
      setIsSending(false);
      setStreamStage('idle');
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // User voluntarily cancelled stream
        setStreamStage('idle');
        setIsSending(false);
        return;
      }
      console.error('Mentor request failure:', err);
      const isTimeout = err.name === 'TimeoutError' || err.message?.includes('timed out');
      setActiveError({
        code: isTimeout ? 504 : 0,
        message: isTimeout
          ? 'Request timed out: The mentor did not answer within the allowed time. Please click Retry.'
          : 'Network Connection Lost: Unable to connect to RepoMentor backend. Please check your network and click Retry.',
        retryable: true,
        submittedText: text
      });
      setInputText(text); // Preserve submitted question
      setStreamStage('error');
      setIsSending(false);
    } finally {
      abortControllerRef.current = null;
    }
  };

  const defaultChips = [
    'Explain the overall project architecture',
    'Where is authentication handled?',
    'What should I refactor first?',
    'Identify potential security risks',
  ];

  const displayChips = starterQuestions.length > 0 ? starterQuestions.slice(0, 4) : defaultChips;

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans transition-colors duration-200">
      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="mentor" 
      />

      <div className="flex-grow flex flex-col max-w-5xl w-full mx-auto px-4 sm:px-6 pt-[76px] pb-6 h-[calc(100vh-20px)]">
        
        {/* Editorial Subheader */}
        <div className="py-3 border-b border-borderPrimary flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="section-header">CONSULTATION // CODEBASE MENTOR</span>
            <span className="text-textMuted">•</span>
            <span className="text-textSecondary">Evidence-Grounded RAG</span>
            {repo?.knowledge_status === 'failed' ? (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono border border-bad/40 bg-bad/10 text-bad font-bold">
                <ShieldAlert className="w-2.5 h-2.5" />
                Index Failed: {repo?.knowledge_summary?.failure_stage || 'Error'}
              </span>
            ) : repo?.knowledge_summary?.chat_index_progress !== undefined && repo.knowledge_summary.chat_index_progress < 100 ? (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-mono border border-signal/40 bg-signal/10 text-signal">
                <Loader2 className="w-2.5 h-2.5 animate-spin" />
                Chat index: {repo.knowledge_summary.chat_index_progress}%
              </span>
            ) : null}
          </div>
          <button
            onClick={createNewSession}
            className="text-textSecondary hover:text-signal text-[11px] underline underline-offset-2 transition-colors"
          >
            Clear conversation
          </button>
        </div>

        {repo?.knowledge_status === 'failed' && (
          <div className="p-3 my-3 bg-bad/10 border border-bad/30 rounded text-bad text-xs font-mono flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5 text-bad" />
            <div>
              <strong className="font-bold">Knowledge Build Failed:</strong> Stage: {repo?.knowledge_summary?.failure_stage || 'Unknown'}, Reason: {repo?.knowledge_summary?.failure_reason || repo?.error_message || 'Unexpected failure'}
            </div>
          </div>
        )}

        {/* Message Thread Viewport */}
        <div className="flex-grow overflow-y-auto py-6 space-y-6">
          {isLoadingHistory ? (
            <div className="space-y-4 max-w-xl mx-auto py-8">
              <div className="h-10 bg-bgSecondary border border-borderPrimary rounded animate-pulse" />
              <div className="h-24 bg-bgSecondary border border-borderPrimary rounded animate-pulse" />
            </div>
          ) : messages.length === 0 && !streamingResponse ? (
            /* Empty State: Starter Question Chips */
            <div className="max-w-2xl mx-auto py-12 text-center space-y-6">
              <div className="space-y-2">
                <div className="w-10 h-10 rounded-full border border-signal/30 bg-signal/10 flex items-center justify-center mx-auto text-signal">
                  <Sparkles className="w-5 h-5" />
                </div>
                <h2 className="font-serif text-2xl font-bold text-textPrimary">
                  Ask Your Repository Mentor
                </h2>
                <p className="text-xs text-textSecondary font-sans max-w-md mx-auto leading-relaxed">
                  Every answer is strictly grounded in the parsed AST, dependency imports, and code smell analysis of this repository.
                </p>
              </div>

              {/* Suggested Question Chips */}
              <div className="space-y-2 max-w-xl mx-auto text-left">
                <span className="section-header block text-center">RECOMMENDED INQUIRIES</span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                  {displayChips.map((chip, i) => (
                    <button
                      key={i}
                      onClick={() => handleSendMessage(chip)}
                      className="p-3 rounded border border-borderPrimary bg-bgSecondary hover:border-signal text-textSecondary hover:text-textPrimary transition-all text-left flex items-start justify-between gap-2 shadow-sm group"
                    >
                      <span className="line-clamp-2">{chip}</span>
                      <ArrowUpRight className="w-3.5 h-3.5 text-textMuted group-hover:text-signal shrink-0 mt-0.5" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Render Existing Messages */}
              {messages.map((m) => {
                const isUser = m.role === 'user';
                return (
                  <div key={m.id} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
                    {!isUser && (
                      <div className="w-7 h-7 rounded border border-borderPrimary bg-bgSecondary flex items-center justify-center text-signal shrink-0 mt-0.5 shadow-sm">
                        <Terminal className="w-3.5 h-3.5" />
                      </div>
                    )}

                    <div className={`space-y-2 max-w-[85%] sm:max-w-[78%] ${isUser ? 'items-end' : 'items-start'}`}>
                      <div className={`p-4 sm:p-5 rounded-lg border text-xs sm:text-sm leading-relaxed ${
                        isUser
                          ? 'bg-signal/5 border-signal/20 text-textPrimary'
                          : 'bg-bgSecondary border-borderPrimary text-textPrimary shadow-report'
                      }`}>
                        {isUser ? (
                          <p className="whitespace-pre-wrap font-sans">{m.content}</p>
                        ) : (
                          <>
                            <MarkdownRenderer content={m.content} />
                            {m.model_used && (
                              <div className="pt-2 mt-2 border-t border-borderPrimary/40 flex items-center justify-between text-[10px] font-mono text-textMuted">
                                <span>Answered by {m.model_used}</span>
                                <span>Deterministic (temp: 0, seed: 42)</span>
                              </div>
                            )}
                          </>
                        )}
                      </div>

                      {/* Evidence Citations Chips */}
                      {m.cited_chunks && m.cited_chunks.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 pt-1 pl-1">
                          <span className="text-[10px] font-mono text-textMuted uppercase font-bold">Evidence:</span>
                          {m.cited_chunks.map((ch, cIdx) => {
                            const isSummary = (ch as any).chunk_type?.toLowerCase() === 'evidence' || ch.file_path.startsWith('Repo summary:') || ch.file_path === 'Repository Summary';
                            const displayName = isSummary ? ch.file_path : ch.file_path.split('/').pop();
                            const hasLines = !isSummary && ch.line_numbers && ch.line_numbers !== '1-1';
                            return (
                              <button
                                key={cIdx}
                                onClick={() => setSelectedCitation(ch)}
                                className="px-2 py-0.5 rounded border border-borderPrimary bg-bgSecondary hover:border-signal text-[10px] font-mono text-textSecondary hover:text-textPrimary transition-colors flex items-center gap-1"
                                title={`Inspect source snippet in ${ch.file_path}`}
                              >
                                <FileCode className="w-3 h-3 text-signal" />
                                <span>{displayName}</span>
                                {hasLines && <span className="text-textMuted">L{ch.line_numbers}</span>}
                              </button>
                            );
                          })}
                        </div>
                      )}

                      {/* Incomplete Index Alert with Re-index Button */}
                      {(m.content.includes("Code index is incomplete") || m.content.includes("Index incomplete") || m.content.includes("Index model mismatch") || m.code_index_incomplete) && (
                        <div className="pt-2">
                          <button
                            type="button"
                            onClick={handleReindexCode}
                            disabled={isReindexing || repo?.knowledge_status === 'indexing'}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-signal/10 hover:bg-signal/20 text-signal border border-signal/30 rounded text-xs font-mono font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <RotateCw className={`w-3.5 h-3.5 ${isReindexing || repo?.knowledge_status === 'indexing' ? 'animate-spin' : ''}`} />
                            <span>{isReindexing || repo?.knowledge_status === 'indexing' ? 'Indexing Code Chunks...' : 'Re-index Repository Code'}</span>
                          </button>
                        </div>
                      )}
                    </div>

                    {isUser && (
                      <div className="w-7 h-7 rounded border border-borderPrimary bg-bgSecondary flex items-center justify-center text-textSecondary shrink-0 mt-0.5 shadow-sm">
                        <User className="w-3.5 h-3.5" />
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Live Streaming Response */}
              {isSending && (
                <div className="flex gap-3 justify-start animate-fade-in">
                  <div className="w-7 h-7 rounded border border-borderPrimary bg-bgSecondary flex items-center justify-center text-signal shrink-0 mt-0.5 shadow-sm">
                    <Terminal className="w-3.5 h-3.5" />
                  </div>
                  <div className="space-y-2 max-w-[85%] sm:max-w-[78%]">
                    <div className="p-4 sm:p-5 rounded-lg border border-borderPrimary bg-bgSecondary text-textPrimary shadow-report">
                      {streamingResponse ? (
                        <MarkdownRenderer content={streamingResponse} />
                      ) : (
                        <div className="flex items-center gap-2 text-xs font-mono text-textSecondary">
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-signal" />
                          <span>
                            {streamStage === 'searching' ? 'Searching the repository...' :
                             streamStage === 'writing' ? 'Writing answer...' :
                             'Searching the repository...'}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Citations arriving while streaming */}
                    {streamingCitations.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 pt-1 pl-1">
                        <span className="text-[10px] font-mono text-textMuted uppercase font-bold">Evidence:</span>
                        {streamingCitations.map((ch, cIdx) => {
                          const isSummary = (ch as any).chunk_type?.toLowerCase() === 'evidence' || ch.file_path.startsWith('Repo summary:') || ch.file_path === 'Repository Summary';
                          const displayName = isSummary ? ch.file_path : ch.file_path.split('/').pop();
                          return (
                            <button
                              key={cIdx}
                              onClick={() => setSelectedCitation(ch)}
                              className="px-2 py-0.5 rounded border border-borderPrimary bg-bgSecondary text-[10px] font-mono text-textSecondary flex items-center gap-1"
                            >
                              <FileCode className="w-3 h-3 text-signal" />
                              <span>{displayName}</span>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Suggested Chips Bar (Always visible above input when thread exists) */}
        {messages.length > 0 && !isSending && (
          <div className="py-2 flex items-center gap-2 overflow-x-auto text-[11px] font-mono">
            <span className="text-textMuted shrink-0">Quick prompts:</span>
            {defaultChips.map((chip, i) => (
              <button
                key={i}
                onClick={() => handleSendMessage(chip)}
                className="px-2.5 py-1 rounded border border-borderPrimary bg-bgSecondary hover:border-signal text-textSecondary hover:text-textPrimary whitespace-nowrap transition-colors"
              >
                {chip}
              </button>
            ))}
          </div>
        )}

        {/* Active Error / Retry Banner */}
        {activeError && (
          <div className="p-3 my-2 bg-bad/10 border border-bad/30 rounded-lg text-bad text-xs font-mono flex items-center justify-between gap-3 animate-fade-in shadow-sm">
            <div className="flex items-center gap-2 overflow-hidden">
              <AlertCircle className="w-4 h-4 shrink-0 text-bad" />
              <span className="truncate">{activeError.message}</span>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {activeError.retryable && (
                <button
                  type="button"
                  onClick={() => handleSendMessage(activeError.submittedText)}
                  className="px-2.5 py-1 bg-bad/20 hover:bg-bad/30 text-bad border border-bad/40 rounded flex items-center gap-1 transition-colors text-[11px] font-bold"
                  title="Retry previous query"
                >
                  <RotateCw className="w-3 h-3" />
                  <span>Retry</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => setActiveError(null)}
                className="text-textMuted hover:text-textPrimary p-1 rounded transition-colors"
                title="Dismiss error"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* Input Form Bar */}
        <div className="pt-2 border-t border-borderPrimary">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2 bg-bgSecondary border border-borderPrimary rounded-lg p-2 shadow-sm focus-within:border-signal transition-colors"
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask about design patterns, classes, smells, or security..."
              disabled={isSending}
              className="flex-grow bg-transparent px-3 py-1.5 text-xs sm:text-sm font-sans text-textPrimary placeholder:text-textMuted focus:outline-none"
            />
            {isSending ? (
              <button
                type="button"
                onClick={handleCancel}
                className="px-4 py-2 bg-bad/15 hover:bg-bad/25 text-bad border border-bad/30 rounded text-xs font-mono font-bold flex items-center gap-1.5 transition-colors shadow-sm"
                aria-label="Stop generation"
                title="Stop generation"
              >
                <Square className="w-3 h-3 fill-current" />
                <span>Stop</span>
              </button>
            ) : (
              <button
                type="submit"
                disabled={isSending || !inputText.trim()}
                className="px-4 py-2 bg-signal hover:bg-signal-hover disabled:opacity-30 disabled:cursor-not-allowed rounded text-white text-xs font-mono font-bold flex items-center gap-1.5 transition-colors shadow-sm"
                aria-label="Send query"
              >
                <Send className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Send</span>
              </button>
            )}
          </form>
        </div>

      </div>

      {/* Citation Snippet Modal Overlay */}
      {selectedCitation && (
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in"
          onClick={() => setSelectedCitation(null)}
        >
          <div 
            className="bg-bgSecondary border border-borderPrimary rounded-lg max-w-2xl w-full max-h-[85vh] flex flex-col p-6 shadow-report-lg space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-borderPrimary pb-3 shrink-0">
              <div className="space-y-0.5">
                <span className="section-header">GROUNDED EVIDENCE SNIPPET</span>
                <h3 className="font-mono text-sm font-bold text-textPrimary">
                  {selectedCitation.file_path} (Lines {selectedCitation.line_numbers})
                </h3>
              </div>
              <button
                onClick={() => setSelectedCitation(null)}
                className="p-1 hover:bg-bgTertiary text-textSecondary rounded transition-colors"
                aria-label="Close modal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <pre className="p-4 bg-bgTertiary rounded border border-borderPrimary font-mono text-xs overflow-auto max-h-[55vh] text-textPrimary leading-relaxed">
              <code>{selectedCitation.content}</code>
            </pre>

            <div className="flex justify-between items-center text-xs font-mono text-textMuted pt-2 shrink-0 border-t border-borderPrimary/40">
              <span>Similarity Score: {(selectedCitation.similarity_score * 100).toFixed(0)}%</span>
              <button
                onClick={() => setSelectedCitation(null)}
                className="px-3 py-1 bg-bgTertiary border border-borderPrimary rounded hover:border-borderStrong text-textPrimary transition-colors"
              >
                Close (Esc)
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
