'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ArrowLeft, Sparkles, Send, Loader2, Cpu, AlertTriangle, CheckCircle,
  FileText, Shield, Compass, BookOpen, Clock, BarChart3, ChevronRight,
  User, Play, Sliders, Layers, RefreshCw, X, ChevronLeft, ArrowRightLeft,
  Bug, Zap, HelpCircle, Code, Info, Gauge
} from 'lucide-react';

import Header from '../../../Header';

interface ChatSessionResponse {
  session_id: string;
  repository_id: string;
  created_at: string;
}

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
}

interface Lesson {
  slide_index: number;
  title: string;
  content: string;
}

interface FileOption {
  id: string;
  path: string;
}

// Lightweight syntax highlighting engine
function highlightCode(code: string = '') {
  if (!code) return '';
  let escaped = code
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  const keywords = /\b(class|struct|interface|enum|def|func|function|fn|return|if|else|for|while|import|package|public|private|protected|static|final|abstract|const|let|var|try|catch|throw|raise|use|namespace)\b/g;
  const strings = /(["'`])(.*?)\1/g;
  const comments = /(\/\/.*$|#.*$|\/\*[\s\S]*?\*\/)/gm;

  escaped = escaped.replace(comments, '<span class="text-gray-500 italic">$1</span>');
  escaped = escaped.replace(strings, '<span class="text-emerald-300">$&</span>');
  escaped = escaped.replace(keywords, '<span class="text-pink-400 font-bold">$1</span>');
  
  return escaped;
}

export default function RepositoryExpert({ params }: { params: { id: string } }) {
  const router = useRouter();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';

  // Persistence State
  const searchParams = useSearchParams();
  const queryQ = searchParams?.get('q') || '';

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [expertMode, setExpertMode] = useState('General');
  const [explainMode, setExplainMode] = useState('Senior Engineer');
  const [flashLine, setFlashLine] = useState<number | null>(null);
  const [expertModes, setExpertModes] = useState<Array<{ mode: string; description: string }>>([]);
  const [starterQuestions, setStarterQuestions] = useState<string[]>([]);

  useEffect(() => {
    if (queryQ) {
      setInputText(queryQ);
    }
  }, [queryQ]);
  
  // Status States
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [streamingResponse, setStreamingResponse] = useState('');
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [streamingConfidence, setStreamingConfidence] = useState<number | null>(null);
  const [streamingSteps, setStreamingSteps] = useState<string[]>([]);
  const [streamingFollowUp, setStreamingFollowUp] = useState<string[]>([]);
  
  // Walkthrough Lesson States
  const [isWalkthroughOpen, setIsWalkthroughOpen] = useState(false);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [activeLessonIdx, setActiveLessonIdx] = useState(0);

  // Citation Modal Overlay State
  const [citationModal, setCitationModal] = useState<{
    isOpen: boolean;
    filePath: string;
    lineNumbers: string;
    content: string;
  }>({ isOpen: false, filePath: '', lineNumbers: '', content: '' });

  // File Inspector States
  const [filesList, setFilesList] = useState<FileOption[]>([]);
  const [selectedFileId, setSelectedFileId] = useState<string>('');
  const [selectedFilePath, setSelectedFilePath] = useState<string>('');
  const [selectedFileCode, setSelectedFileCode] = useState<string>('');
  const [isLoadingCode, setIsLoadingCode] = useState(false);
  
  // Code Range Selection States
  const [startLineSelect, setStartLineSelect] = useState<number | null>(null);
  const [endLineSelect, setEndLineSelect] = useState<number | null>(null);
  const [selectedCodeSnippet, setSelectedCodeSnippet] = useState<string>('');

  const chatEndRef = useRef<HTMLDivElement>(null);
  const codeContainerRef = useRef<HTMLDivElement>(null);

  const [repo, setRepo] = useState<any>(null);
  const [isRetryingKb, setIsRetryingKb] = useState(false);

  const handleRetryKb = async () => {
    setIsRetryingKb(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/knowledge/retry`, {
        method: 'POST'
      });
      if (res.ok) {
        const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
        if (repoRes.ok) setRepo(await repoRes.json());
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

  // 1. Initial Load: Expert Modes, Starters, Files List, and Session setup
  useEffect(() => {
    const initData = async () => {
      try {
        // Fetch repository details first
        const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
        if (!repoRes.ok) throw new Error('Repository details not found.');
        const repoData = await repoRes.json();
        setRepo(repoData);

        const isUnlocked = repoData.status === 'ready' && repoData.knowledge_status === 'completed';

        if (!isUnlocked) {
          setIsLoadingHistory(false);
          return;
        }

        // Load modes
        const modesRes = await fetch(`${apiUrl}/repositories/${repoId}/chat/expert-modes`);
        if (modesRes.ok) setExpertModes(await modesRes.json());

        // Load starters
        const startersRes = await fetch(`${apiUrl}/repositories/${repoId}/chat/starter-questions`);
        if (startersRes.ok) setStarterQuestions(await startersRes.json());

        // Load lessons
        const lessonsRes = await fetch(`${apiUrl}/repositories/${repoId}/chat/walkthrough`);
        if (lessonsRes.ok) setLessons(await lessonsRes.json());

        // Load files list for selection
        const filesRes = await fetch(`${apiUrl}/repositories/${repoId}/files?limit=200`);
        if (filesRes.ok) {
          const filesData = await filesRes.json();
          setFilesList(filesData.files.map((f: any) => ({ id: f.id, path: f.path })));
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
        console.error('Failed to configure chatbot presets:', err);
        setIsLoadingHistory(false);
      }
    };
    initData();
  }, [repoId, apiUrl]);

  // Polling setup for active indexing
  useEffect(() => {
    if (repo && (repo.knowledge_status !== 'completed' || repo.status !== 'ready')) {
      const interval = setInterval(async () => {
        const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
        if (repoRes.ok) {
          const repoData = await repoRes.json();
          setRepo(repoData);
          if (repoData.status === 'ready' && repoData.knowledge_status === 'completed') {
            clearInterval(interval);
            // Re-run setup
            const reloadSetup = async () => {
              try {
                const modesRes = await fetch(`${apiUrl}/repositories/${repoId}/chat/expert-modes`);
                if (modesRes.ok) setExpertModes(await modesRes.json());
                const startersRes = await fetch(`${apiUrl}/repositories/${repoId}/chat/starter-questions`);
                if (startersRes.ok) setStarterQuestions(await startersRes.json());
                const lessonsRes = await fetch(`${apiUrl}/repositories/${repoId}/chat/walkthrough`);
                if (lessonsRes.ok) setLessons(await lessonsRes.json());
                const filesRes = await fetch(`${apiUrl}/repositories/${repoId}/files?limit=200`);
                if (filesRes.ok) {
                  const filesData = await filesRes.json();
                  setFilesList(filesData.files.map((f: any) => ({ id: f.id, path: f.path })));
                }
                const cachedSession = localStorage.getItem(`chat_session_${repoId}`);
                if (cachedSession) {
                  setSessionId(cachedSession);
                  fetchHistory(cachedSession);
                } else {
                  await createNewSession();
                }
              } catch (e) {
                console.error(e);
              }
            };
            reloadSetup();
          }
        }
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [repo, repoId, apiUrl]);

  // Scroll to chat bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingResponse]);

  const createNewSession = async () => {
    setIsLoadingHistory(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/chat/sessions`, { method: 'POST' });
      if (res.ok) {
        const data: ChatSessionResponse = await res.json();
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

  // 2. Fetch File Source Code Content
  const fetchFileContent = async (fileId: string, filePath: string) => {
    setIsLoadingCode(true);
    setSelectedFileId(fileId);
    setSelectedFilePath(filePath);
    setStartLineSelect(null);
    setEndLineSelect(null);
    setSelectedCodeSnippet('');
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/files/${fileId}/content`);
      if (res.ok) {
        const data = await res.json();
        setSelectedFileCode(data.content);
      }
      setIsLoadingCode(false);
    } catch (err) {
      console.error(err);
      setIsLoadingCode(false);
    }
  };

  // Click on a line in code preview sets start/end range
  const handleLineClick = (lineNum: number) => {
    if (startLineSelect === null) {
      setStartLineSelect(lineNum);
      setEndLineSelect(lineNum);
    } else if (lineNum < startLineSelect) {
      setStartLineSelect(lineNum);
    } else {
      setEndLineSelect(lineNum);
    }
  };

  // Update selected code snippet based on selected line bounds
  useEffect(() => {
    if (startLineSelect === null || endLineSelect === null || !selectedFileCode) {
      setSelectedCodeSnippet('');
      return;
    }
    const lines = selectedFileCode.split('\n');
    const slice = lines.slice(startLineSelect - 1, endLineSelect);
    setSelectedCodeSnippet(slice.join('\n'));
  }, [startLineSelect, endLineSelect, selectedFileCode]);

  // Inject selected code range into the chat input
  const handleInjectSelection = (action: string) => {
    if (!selectedCodeSnippet) return;
    const prompt = (
      `${action} in file \`${selectedFilePath}\` (lines ${startLineSelect}-${endLineSelect}):\n` +
      `\`\`\`\n${selectedCodeSnippet}\n\`\`\``
    );
    setInputText(prompt);
  };

  // Clear selections
  const clearSelection = () => {
    setStartLineSelect(null);
    setEndLineSelect(null);
    setSelectedCodeSnippet('');
  };

  // 3. Send Message via Server-Sent Events (SSE) Streaming
  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim();
    if (!text || !sessionId) return;

    setInputText('');
    setIsSending(true);
    setStreamingResponse('');
    setStreamingCitations([]);
    setStreamingConfidence(null);
    setStreamingSteps([]);
    setStreamingFollowUp([]);

    // Add user message locally
    const userMsg: Message = {
      id: Math.random().toString(36).substring(2, 9),
      role: 'user',
      content: text,
      expert_mode: expertMode,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      // Initiate HTTP request
      const response = await fetch(`${apiUrl}/repositories/${repoId}/chat/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: text,
          expert_mode: expertMode,
          explain_mode: explainMode
        })
      });

      if (!response.body) throw new Error('ReadableStream not supported.');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Save the incomplete line back to buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            try {
              const payload = JSON.parse(dataStr);
              if (payload.type === 'token') {
                setStreamingResponse(prev => prev + payload.token);
              } else if (payload.type === 'metadata') {
                setStreamingCitations(payload.citations || []);
                setStreamingConfidence(payload.confidence);
                setStreamingSteps(payload.steps || []);
                setStreamingFollowUp(payload.follow_up || []);
              }
            } catch (jsonErr) {
              // ignore parse errors on incomplete chunk lines
            }
          }
        }
      }

      // Re-fetch message history to keep sync with DB
      fetchHistory(sessionId);
      setIsSending(false);
    } catch (err) {
      console.error(err);
      setIsSending(false);
    }
  };

  const activeExpertPrompt = expertModes.find(m => m.mode === expertMode)?.description || 'General mode';

  // 1. Ingestion Pipeline Active
  if (repo && repo.status !== 'ready') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary text-textPrimary font-sans">
        <div className="max-w-md w-full p-6 bg-bgSecondary border border-borderPrimary rounded-2xl space-y-6 shadow-md">
          <div className="text-center space-y-2">
            <Loader2 className="w-8 h-8 animate-spin text-brand-500 mx-auto" />
            <h2 className="text-sm font-bold text-textPrimary uppercase tracking-wider">Repository Ingestion Active</h2>
            <p className="text-xs text-textSecondary">Deterministic scanning and analysis are running...</p>
          </div>
          
          <div className="bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-950 p-4 rounded-xl space-y-3 text-xs">
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
                      <CheckCircle className="w-4 h-4 text-emerald-500" />
                    ) : isRunning ? (
                      <Loader2 className="w-4 h-4 animate-spin text-brand-500" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-slate-300 dark:border-gray-800" />
                    )}
                    <span className={isCompleted ? 'text-textSecondary' : isRunning ? 'text-textPrimary font-semibold' : 'text-slate-400 dark:text-gray-600'}>
                      {stg.label}
                    </span>
                  </div>
                );
              });
            })()}
          </div>
          <button
            onClick={() => router.push(`/repositories/${repoId}`)}
            className="w-full py-2.5 px-4 bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-800 text-textPrimary rounded-xl text-xs font-semibold transition-all"
          >
            Back to Overview
          </button>
        </div>
      </div>
    );
  }

  // 2. Knowledge Indexing in Progress (Component 4)
  // 2. Indexing / Processing State
  const pct = (() => {
    if (!repo?.status_message) return 0;
    const match = repo.status_message.match(/(\d+)%\s+complete/);
    return match ? parseInt(match[1]) : 0;
  })();

  if (repo && (repo.knowledge_status === 'pending' || repo.knowledge_status === 'indexing')) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4 font-sans text-center text-textPrimary">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-8 rounded-2xl shadow-sm space-y-6">
          <Loader2 className="w-10 h-10 animate-spin text-brand-500 mx-auto" />
          <div className="space-y-2">
            <h2 className="text-lg font-bold text-textPrimary tracking-tight">AI Indexing Active</h2>
            <p className="text-xs text-textSecondary">
              The vector knowledge index is currently compiling. The AI Mentor chat interface will unlock immediately after vector indexing completes.
            </p>
          </div>
          <div className="bg-slate-50 dark:bg-zinc-950/40 border border-slate-200 dark:border-zinc-900/60 p-4 rounded-xl text-xs space-y-2 text-left">
            <div className="flex justify-between items-center text-textSecondary">
              <span>Knowledge Base Indexing</span>
              <span className="text-[10px] text-brand-600 dark:text-brand-400 font-bold uppercase tracking-wider animate-pulse">Running</span>
            </div>
            <div className="flex justify-between items-center text-slate-400 dark:text-gray-500">
              <span>AI Chat Initialization</span>
              <span>Pending</span>
            </div>
          </div>
          <p className="text-[10px] text-textSecondary font-mono">Current Stage: {repo.status_message || 'Indexing'}</p>
          <div className="flex gap-2">
            <button
              onClick={() => router.push(`/repositories/${repoId}`)}
              className="w-full py-2.5 px-4 bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-800 text-textPrimary rounded-xl text-xs font-semibold transition-all"
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
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4 font-sans text-center text-textPrimary">
        <div className="max-w-md w-full bg-bgSecondary border border-rose-500/20 p-8 rounded-2xl shadow-md space-y-6">
          <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto" />
          <div className="space-y-2">
            <h2 className="text-lg font-bold text-textPrimary tracking-tight">AI Indexing Failed</h2>
            <p className="text-xs text-textSecondary text-left">
              The AI Knowledge Base indexing could not be completed. Vector query is unavailable. Please click below to retry indexing.
            </p>
          </div>
          <div className="bg-slate-50 dark:bg-zinc-950 border border-rose-500/10 p-4 rounded-xl text-left">
            <span className="text-textSecondary font-bold block mb-1 text-[10px]">Error Details:</span>
            <p className="text-rose-500 dark:text-rose-400 font-mono text-[10px] leading-relaxed break-all">
              {repo.error_message || 'Timeout exceeded during embedding generation.'}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => router.push(`/repositories/${repoId}`)}
              className="flex-1 py-2.5 px-4 bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-800 text-textPrimary rounded-xl text-xs font-semibold transition-all"
            >
              Back to Overview
            </button>
            <button
              disabled={isRetryingKb}
              onClick={handleRetryKb}
              className="flex-1 py-2.5 px-4 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-xl transition-all flex items-center justify-center gap-1.5"
            >
              {isRetryingKb && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Retry Indexing
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bgPrimary text-textPrimary flex flex-col font-sans selection:bg-brand-500/20 relative overflow-hidden transition-colors duration-300">
      {/* Background radial/linear glow elements */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-brand-500/5 rounded-full blur-[120px] pointer-events-none -z-10 animate-slow-blob-1" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-500/5 rounded-full blur-[100px] pointer-events-none -z-10 animate-slow-blob-2" />
      
      {/* Grid Overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(99,102,241,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(99,102,241,0.02)_1px,transparent_1px)] bg-[size:3.5rem_3.5rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] -z-10" />

      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="mentor" 
      />

      {/* Main split dashboard layout */}
      <div className="flex-grow flex flex-col lg:flex-row h-[calc(100vh-68px)] mt-[68px] overflow-hidden">
        
        {/* ==========================================
            LEFT PANEL: CHAT INTERFACE & INPUT
           ========================================== */}
        <div className="w-full flex flex-col h-full bg-slate-50/5 dark:bg-zinc-950/20">
          
          {/* Header toolbar */}
          <div className="px-6 py-4 border-b border-borderPrimary flex items-center justify-between gap-4">
            <div>
              <h2 className="text-sm font-bold text-textPrimary flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-brand-600 dark:text-violet-400 animate-spin-slow" /> AI Repository Mentor
              </h2>
              <span className="text-[10px] text-textSecondary font-medium">Fully Grounded Evidence chatbot</span>
            </div>
          </div>

          {/* Messages stream viewport */}
          <div className="flex-grow overflow-y-auto px-6 py-6 space-y-6 animate-fade-in">

            {isLoadingHistory ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center space-y-4">
                  <Loader2 className="w-6 h-6 animate-spin text-brand-500 mx-auto" />
                  <p className="text-xs text-textSecondary">Loading conversation session...</p>
                </div>
              </div>
            ) : (
              <>
                {messages.length === 0 && !streamingResponse && (
                  <div className="max-w-xl mx-auto space-y-6 py-6">
                    <div className="p-5 bg-bgSecondary border border-borderPrimary rounded-2xl space-y-2 shadow-sm">
                      <h3 className="text-xs font-bold text-textSecondary uppercase tracking-wider flex items-center gap-1.5">
                        <Cpu className="w-4 h-4 text-brand-500 dark:text-violet-400" /> AI Repository Mentor
                      </h3>
                      <p className="text-xs text-textSecondary leading-relaxed font-medium">
                        Ask any questions about the files, classes, architecture, security, or algorithms in this repository. All answers are grounded in codebase evidence.
                      </p>
                    </div>

                    <div className="space-y-3">
                      <span className="text-[10px] text-gray-500 uppercase font-bold tracking-wider block">Starter Prompts:</span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        {starterQuestions.map((q, i) => (
                          <button
                            key={i}
                            onClick={() => handleSendMessage(q)}
                            className="p-3 bg-slate-50 dark:bg-zinc-950/60 border border-slate-200 dark:border-zinc-900 hover:border-slate-300 dark:hover:border-zinc-800 text-left rounded-xl text-textSecondary hover:text-textPrimary transition-all leading-relaxed"
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Messages list */}
                {messages.map((m) => {
                  const isUser = m.role === 'user';
                  const isSummary = m.role === 'summary';
                  
                  if (isSummary) {
                    return (
                      <div key={m.id} className="max-w-md mx-auto p-3 bg-brand-500/5 border border-brand-500/10 rounded-xl text-center text-[10px] text-brand-600 dark:text-violet-300 font-medium">
                        Conversation Summarized: "{m.content}"
                      </div>
                    );
                  }

                  return (
                    <div key={m.id} className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
                      <div className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center border ${
                        isUser ? 'bg-brand-500/10 border-brand-500/20 text-brand-600 dark:text-brand-300' : 'bg-violet-500/10 border-violet-500/20 text-violet-600 dark:text-violet-300'
                      }`}>
                        {isUser ? <User className="w-4 h-4" /> : <Cpu className="w-4 h-4" />}
                      </div>

                      <div className="space-y-3 max-w-[80%]">
                        <div className={`p-4 rounded-2xl text-xs leading-relaxed border ${
                          isUser
                            ? 'bg-brand-500/5 border-brand-500/15 text-textPrimary rounded-tr-none'
                            : 'bg-bgSecondary border-borderPrimary text-textPrimary rounded-tl-none'
                        }`}>
                          <pre className="whitespace-pre-wrap font-sans">{m.content}</pre>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* Streaming Assistant bubble */}
                {isSending && streamingResponse && (
                  <div className="flex gap-4 justify-start">
                    <div className="w-8 h-8 rounded-xl shrink-0 flex items-center justify-center border bg-violet-500/10 border-violet-500/20 text-violet-650 dark:text-brand-300">
                      <Cpu className="w-4 h-4" />
                    </div>
                    <div className="space-y-3 max-w-[80%]">
                      <div className="p-4 rounded-2xl text-xs leading-relaxed border bg-bgSecondary border-borderPrimary text-textPrimary rounded-tl-none">
                        <pre className="whitespace-pre-wrap font-sans">{streamingResponse}</pre>
                      </div>

                      {/* Follow-up Questions */}
                      {streamingFollowUp.length > 0 && (
                        <div className="space-y-1.5 pt-1 pl-2">
                          <span className="text-[10px] text-textSecondary font-bold uppercase tracking-wider block">Suggested Questions:</span>
                          <div className="flex flex-wrap gap-2">
                            {streamingFollowUp.map((q, fIdx) => (
                              <button
                                key={fIdx}
                                onClick={() => handleSendMessage(q)}
                                className="px-2.5 py-1 border border-slate-200 dark:border-zinc-900 hover:border-brand-500/20 bg-slate-50 dark:bg-zinc-900/25 hover:bg-slate-100 dark:hover:bg-zinc-900/65 text-textSecondary hover:text-textPrimary text-[9px] rounded-lg transition-all"
                              >
                                {q}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {isSending && !streamingResponse && (
                  <div className="flex gap-4 justify-start">
                    <div className="w-8 h-8 rounded-xl shrink-0 flex items-center justify-center border bg-violet-500/10 border-violet-500/20 text-violet-500 animate-pulse">
                      <Loader2 className="w-4 h-4 animate-spin" />
                    </div>
                    <span className="text-xs text-textSecondary mt-2 italic">Mentor is searching repository evidence...</span>
                  </div>
                )}
              </>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Chat input form */}
          <div className="p-4 border-t border-borderPrimary bg-slate-100/50 dark:bg-zinc-950/40">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Ask about classes, interfaces, patterns, or architecture..."
                className="flex-grow bg-bgPrimary border border-slate-200 dark:border-zinc-900 focus:border-brand-500 rounded-xl px-4 py-2.5 text-xs text-textPrimary placeholder-slate-400 dark:placeholder-gray-600 focus:ring-0 outline-none"
                value={inputText}
                onChange={e => setInputText(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') handleSendMessage();
                }}
              />
              <button
                disabled={isSending || !inputText.trim()}
                onClick={() => handleSendMessage()}
                className="px-4 py-2.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl text-white text-xs font-semibold flex items-center gap-1.5 transition-all shadow-lg"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

      </div>

      {/* ==========================================
          MODAL: TEACH ME WALKTHROUGH MODAL
         ========================================== */}
      {isWalkthroughOpen && lessons.length > 0 && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-bgSecondary border border-borderPrimary rounded-3xl max-w-lg w-full overflow-hidden shadow-md animate-scale-up">
            
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-borderPrimary flex justify-between items-center bg-slate-50/50 dark:bg-zinc-950/40">
              <span className="text-xs font-bold text-textPrimary uppercase tracking-wider flex items-center gap-1.5 font-mono">
                <BookOpen className="w-4 h-4 text-brand-500 dark:text-brand-400" /> Teach Me: Onboarding Walkthrough
              </span>
              <button
                onClick={() => setIsWalkthroughOpen(false)}
                className="text-slate-500 hover:text-slate-900 dark:text-gray-500 dark:hover:text-white p-1 hover:bg-slate-100 dark:hover:bg-gray-900 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Slide content body */}
            <div className="p-6 space-y-4">
              <div className="space-y-2">
                <span className="text-[10px] text-brand-600 dark:text-brand-400 uppercase font-bold tracking-wider font-mono">
                  Lesson {lessons[activeLessonIdx].slide_index} of {lessons.length}
                </span>
                <h4 className="text-base font-bold text-textPrimary">
                  {lessons[activeLessonIdx].title}
                </h4>
              </div>
              
              <div className="p-5 bg-slate-50 dark:bg-zinc-950/80 border border-slate-200 dark:border-gray-950 rounded-2xl text-xs text-textSecondary leading-relaxed font-medium min-h-[140px]">
                {lessons[activeLessonIdx].content}
              </div>
            </div>

            {/* Modal Footer Controls */}
            <div className="px-6 py-4 border-t border-borderPrimary bg-slate-50/50 dark:bg-zinc-950/40 flex justify-between items-center">
              <button
                disabled={activeLessonIdx === 0}
                onClick={() => setActiveLessonIdx(idx => idx - 1)}
                className="px-3.5 py-2 border border-slate-200 dark:border-zinc-900 hover:border-slate-300 dark:hover:border-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-semibold rounded-xl text-textSecondary hover:text-textPrimary transition-all flex items-center gap-1"
              >
                <ChevronLeft className="w-4 h-4" /> Previous
              </button>
              
              {activeLessonIdx === lessons.length - 1 ? (
                <button
                  onClick={() => setIsWalkthroughOpen(false)}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition-all shadow-md"
                >
                  Finish Walkthrough
                </button>
              ) : (
                <button
                  onClick={() => setActiveLessonIdx(idx => idx + 1)}
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-bold rounded-xl transition-all flex items-center gap-1 shadow-md"
                >
                  Next Lesson <ChevronRight className="w-4 h-4" />
                </button>
              )}
            </div>

          </div>
        </div>
      )}

      {/* ==========================================
          MODAL: INLINE CITATION SNIPPET OVERLAY
         ========================================== */}
      {citationModal.isOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-bgSecondary border border-borderPrimary rounded-2xl max-w-2xl w-full flex flex-col overflow-hidden shadow-md animate-scale-up">
            
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-borderPrimary flex justify-between items-center bg-slate-50/50 dark:bg-[#0e111a]">
              <div>
                <h3 className="text-xs font-bold text-textPrimary font-mono truncate">{citationModal.filePath}</h3>
                <span className="text-[9px] text-textSecondary font-mono">Lines {citationModal.lineNumbers}</span>
              </div>
              <button
                onClick={() => setCitationModal(prev => ({ ...prev, isOpen: false }))}
                className="text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-white p-1 hover:bg-slate-100 dark:hover:bg-zinc-900 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto max-h-[60vh] bg-slate-50/20 dark:bg-[#07090e]">
              <pre className="text-[11px] font-mono text-textPrimary whitespace-pre-wrap leading-relaxed bg-slate-100 dark:bg-[#0b0e16]/80 p-4 rounded-xl border border-borderPrimary overflow-x-auto">
                {citationModal.content}
              </pre>
            </div>
            
            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-borderPrimary bg-slate-50/50 dark:bg-[#0e111a] flex justify-end">
              <button
                onClick={() => setCitationModal(prev => ({ ...prev, isOpen: false }))}
                className="px-4 py-1.5 bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 text-textSecondary hover:text-textPrimary text-xs font-bold rounded-lg transition-colors"
              >
                Close
              </button>
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
