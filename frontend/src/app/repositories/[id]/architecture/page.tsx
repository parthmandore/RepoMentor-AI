'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import ReactFlow, {
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';

import {
  ArrowLeft, Loader2, ShieldAlert, Layers, Shield, AlertTriangle,
  CheckCircle2, Search, Activity, GitBranch, Cpu, HelpCircle,
  Maximize2, Minimize2, ZoomIn, ZoomOut, RefreshCw, X, ChevronRight,
  Code, BarChart3, Bug, FileText, Check, AlertCircle, Sparkles, Gauge
} from 'lucide-react';

import Header from '../../../Header';
import { useTheme } from '../../../ThemeProvider';

interface DependencyStats {
  total_edges: number;
  average_imports: number;
  highest_fan_in: string;
  highest_fan_out: string;
  largest_chain: number;
  highest_coupling_score: number;
}

interface ArchitectureSummary {
  pattern: string;
  confidence: number;
  evidence: string[];
  total_modules: number;
  entry_points: number;
  cycles_count: number;
  most_coupled_module: string;
  stats: DependencyStats;
  cycles_list: string[][];
}

interface FindingEntry {
  title: string;
  description: string;
  evidence?: string;
}

interface ArchitectureFindings {
  strengths: FindingEntry[];
  warnings: FindingEntry[];
}

interface GraphNodeData {
  id: string;
  path: string;
  type: string;
  coupling: number;
  instability: number;
  in_cycle: boolean;
}

interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
}

interface GraphResponse {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
  is_truncated: boolean;
  total_nodes: number;
}

// Side pane file detail model
interface SelectedFileDetail {
  id: string;
  lines_of_code: number;
  complexity: number;
  code_smells_count: number;
  analysis_metadata: {
    metrics?: {
      function_count?: number;
      class_count?: number;
      interface_count?: number;
      enum_count?: number;
    };
    declarations?: Array<{
      name: string;
      type: string;
      line: number;
    }>;
  } | null;
}

const GRADE_COLORS: Record<string, string> = {
  A: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
  B: 'text-sky-400 border-sky-500/30 bg-sky-500/10',
  C: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
  D: 'text-orange-400 border-orange-500/30 bg-orange-500/10',
  F: 'text-rose-400 border-rose-500/30 bg-rose-500/10',
};

const MODULE_TYPE_COLORS: Record<string, { bg: string; border: string; text: string; hex: string }> = {
  Controller: { bg: 'bg-rose-500/10', border: 'border-rose-500/30', text: 'text-rose-400', hex: '#f43f5e' },
  API: { bg: 'bg-rose-500/10', border: 'border-rose-500/30', text: 'text-rose-400', hex: '#f43f5e' },
  Service: { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400', hex: '#f59e0b' },
  Repository: { bg: 'bg-violet-500/10', border: 'border-violet-500/30', text: 'text-violet-400', hex: '#8b5cf6' },
  Model: { bg: 'bg-indigo-500/10', border: 'border-indigo-500/30', text: 'text-indigo-400', hex: '#6366f1' },
  Component: { bg: 'bg-sky-500/10', border: 'border-sky-500/30', text: 'text-sky-400', hex: '#0ea5e9' },
  Hook: { bg: 'bg-teal-500/10', border: 'border-teal-500/30', text: 'text-teal-400', hex: '#14b8a6' },
  Utility: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400', hex: '#10b981' },
  Configuration: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', hex: '#3b82f6' },
  Middleware: { bg: 'bg-orange-500/10', border: 'border-orange-500/30', text: 'text-orange-400', hex: '#f97316' },
  Unknown: { bg: 'bg-gray-500/10', border: 'border-gray-500/30', text: 'text-gray-400', hex: '#6b7280' },
};

export default function ArchitectureExplorerPage({ params }: { params: { id: string } }) {
  const { theme } = useTheme();
  const router = useRouter();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api/v1';

  // API states
  const [repo, setRepo] = useState<any>(null);
  const [repoScore, setRepoScore] = useState<{ score: number; grade: string } | null>(null);
  const [summary, setSummary] = useState<ArchitectureSummary | null>(null);
  const [findings, setFindings] = useState<ArchitectureFindings | null>(null);
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Interaction states
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModule, setSelectedModule] = useState<GraphNodeData | null>(null);
  const [selectedFile, setSelectedFile] = useState<SelectedFileDetail | null>(null);
  const [isSidebarLoading, setIsSidebarLoading] = useState(false);
  const [rfInstance, setRfInstance] = useState<any>(null);

  // React Flow hooks
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const fetchData = useCallback(async () => {
    try {
      const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
      if (!repoRes.ok) throw new Error('Repository detail not found.');
      const repoData = await repoRes.json();
      setRepo(repoData);
      setRepoScore({ score: repoData.architecture_score, grade: repoData.architecture_grade });

      const summaryRes = await fetch(`${apiUrl}/repositories/${repoId}/architecture/explorer`);
      if (!summaryRes.ok) throw new Error('Architecture details not found.');
      setSummary(await summaryRes.json());

      const findingsRes = await fetch(`${apiUrl}/repositories/${repoId}/architecture/findings`);
      if (findingsRes.ok) setFindings(await findingsRes.json());

      const graphRes = await fetch(`${apiUrl}/repositories/${repoId}/architecture/graph`);
      if (graphRes.ok) {
        const gd: GraphResponse = await graphRes.json();
        setGraphData(gd);

        const numNodes = gd.nodes.length;
        const radius = Math.max(250, numNodes * 12);
        
        const flowNodes: Node[] = gd.nodes.map((n, index) => {
          const angle = (index / numNodes) * 2 * Math.PI;
          const x = Math.round(400 + radius * Math.cos(angle));
          const y = Math.round(300 + radius * Math.sin(angle));
          const colorObj = MODULE_TYPE_COLORS[n.type] || MODULE_TYPE_COLORS.Unknown;

          return {
            id: n.path,
            type: 'default',
            data: {
              label: (
                <div className="text-center font-mono">
                  <div className="text-[10px] font-bold truncate max-w-[180px]">{n.path.split('/').pop()}</div>
                  <div className={`text-[8px] mt-0.5 font-sans px-1 rounded border inline-block ${colorObj.bg} ${colorObj.border} ${colorObj.text}`}>
                    {n.type}
                  </div>
                </div>
              )
            },
            position: { x, y },
            style: {
              background: 'var(--bg-secondary)',
              border: `1.5px solid ${n.in_cycle ? '#f43f5e' : colorObj.hex}`,
              borderRadius: '12px',
              padding: '6px 10px',
              color: 'var(--text-primary)',
              boxShadow: n.in_cycle ? '0 0 10px rgba(244, 63, 94, 0.2)' : 'none',
              width: 180,
            }
          };
        });

        const flowEdges: Edge[] = gd.edges.map(e => ({
          id: e.id,
          source: e.source,
          target: e.target,
          type: 'smoothstep',
          animated: gd.nodes.find(n => n.path === e.source)?.in_cycle && gd.nodes.find(n => n.path === e.target)?.in_cycle,
          style: {
            stroke: gd.nodes.find(n => n.path === e.source)?.in_cycle && gd.nodes.find(n => n.path === e.target)?.in_cycle ? '#f43f5e' : 'var(--border-primary)',
            strokeWidth: 1.5
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 12,
            height: 12,
            color: gd.nodes.find(n => n.path === e.source)?.in_cycle && gd.nodes.find(n => n.path === e.target)?.in_cycle ? '#f43f5e' : 'var(--border-primary)',
          }
        }));

        setNodes(flowNodes);
        setEdges(flowEdges);
      }
      setIsLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch architecture data.');
      setIsLoading(false);
    }
  }, [apiUrl, repoId, setNodes, setEdges]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Selected imports / imported by helpers
  const selectedImports = useMemo(() => {
    if (!selectedModule || !graphData) return [];
    return graphData.edges.filter(e => e.source === selectedModule.path).map(e => e.target);
  }, [selectedModule, graphData]);

  const selectedImportedBy = useMemo(() => {
    if (!selectedModule || !graphData) return [];
    return graphData.edges.filter(e => e.target === selectedModule.path).map(e => e.source);
  }, [selectedModule, graphData]);

  // Task 3 Node Highlighting: Selected (blue), Incoming (green), Outgoing (red), others dimmed
  useEffect(() => {
    if (!graphData) return;

    setNodes(prevNodes =>
      prevNodes.map(node => {
        let isMatched = searchQuery ? node.id.toLowerCase().includes(searchQuery.toLowerCase()) : true;
        const colorObj = MODULE_TYPE_COLORS[graphData.nodes.find(n => n.path === node.id)?.type || 'Unknown'] || MODULE_TYPE_COLORS.Unknown;
        const inCycle = graphData.nodes.find(n => n.path === node.id)?.in_cycle;

        let borderStyle = `1.5px solid ${inCycle ? '#f43f5e' : colorObj.hex}`;
        let opacity = isMatched ? 1.0 : 0.15;
        let shadow = inCycle ? '0 0 10px rgba(244, 63, 94, 0.2)' : 'none';

        if (selectedModule) {
          if (node.id === selectedModule.path) {
            borderStyle = '2.5px solid #3b82f6'; // Blue for selected
            opacity = 1.0;
            shadow = '0 0 14px rgba(59, 130, 246, 0.5)';
          } else if (selectedImportedBy.includes(node.id)) {
            borderStyle = '2px solid #10b981'; // Green for incoming
            opacity = 1.0;
            shadow = '0 0 10px rgba(16, 185, 129, 0.3)';
          } else if (selectedImports.includes(node.id)) {
            borderStyle = '2px solid #ef4444'; // Red for outgoing
            opacity = 1.0;
            shadow = '0 0 10px rgba(239, 68, 68, 0.3)';
          } else {
            opacity = 0.15; // Dim others
          }
        }

        return {
          ...node,
          style: {
            ...node.style,
            opacity,
            border: borderStyle,
            boxShadow: shadow
          }
        };
      })
    );

    setEdges(prevEdges =>
      prevEdges.map(edge => {
        let stroke = '#3f3f46';
        let animated = false;
        let opacity = 1.0;

        if (selectedModule) {
          if (edge.source === selectedModule.path) {
            stroke = '#ef4444'; // Red edge for outgoing imports
            animated = true;
          } else if (edge.target === selectedModule.path) {
            stroke = '#10b981'; // Green edge for incoming imports
            animated = true;
          } else {
            opacity = 0.1; // Hide/dim unrelated links
          }
        }

        const currentMarker = typeof edge.markerEnd === 'object' && edge.markerEnd !== null ? edge.markerEnd : { type: MarkerType.ArrowClosed };

        return {
          ...edge,
          animated,
          style: {
            ...edge.style,
            stroke,
            opacity,
            strokeWidth: selectedModule && (edge.source === selectedModule.path || edge.target === selectedModule.path) ? 2.5 : 1.5
          },
          markerEnd: {
            ...currentMarker,
            color: stroke
          }
        };
      })
    );
  }, [selectedModule, selectedImports, selectedImportedBy, searchQuery, graphData, setNodes, setEdges]);

  // Sidebar detailed file info fetcher
  const fetchModuleFileDetails = async (path: string) => {
    setIsSidebarLoading(true);
    try {
      const res = await fetch(`${apiUrl}/repositories/${repoId}/files?path=${path}`);
      if (res.ok) {
        const paginated = await res.json();
        if (paginated.files && paginated.files.length > 0) {
          const fid = paginated.files[0].id;
          const detailRes = await fetch(`${apiUrl}/repositories/${repoId}/files/${fid}`);
          if (detailRes.ok) {
            setSelectedFile(await detailRes.json());
          }
        }
      }
    } catch (e) {
      console.error(e);
    }
    setIsSidebarLoading(false);
  };

  const onNodeClick = (_: any, node: Node) => {
    const matchedModule = graphData?.nodes.find(n => n.path === node.id);
    if (matchedModule) {
      setSelectedModule(matchedModule);
      setSelectedFile(null);
      fetchModuleFileDetails(matchedModule.path);
    }
  };

  const handleZoomToFit = () => { if (rfInstance) rfInstance.fitView({ padding: 0.15 }); };
  const handleResetView = () => { if (rfInstance) rfInstance.setViewport({ x: 50, y: 50, zoom: 0.85 }); };

  const selectedCycles = useMemo(() => {
    if (!selectedModule || !summary?.cycles_list) return [];
    return summary.cycles_list.filter(cycle => cycle.includes(selectedModule.path));
  }, [selectedModule, summary]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary text-textPrimary">
        <div className="text-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500 mx-auto" />
          <p className="text-sm text-textSecondary">Analyzing software architecture...</p>
        </div>
      </div>
    );
  }

  if (error || !summary || !repoScore) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-6 rounded-2xl shadow-md text-center space-y-6">
          <ShieldAlert className="w-8 h-8 text-rose-500 mx-auto" />
          <h2 className="text-xl font-bold text-textPrimary animate-pulse">Analysis Missing</h2>
          <p className="text-sm text-textSecondary">{error || 'Please run a repository codebase scan first.'}</p>
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
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-brand-500/5 rounded-full blur-[120px] pointer-events-none -z-10 animate-slow-blob-1" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-500/5 rounded-full blur-[100px] pointer-events-none -z-10 animate-slow-blob-2" />
      
      {/* Grid Overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(99,102,241,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(99,102,241,0.02)_1px,transparent_1px)] bg-[size:3.5rem_3.5rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] -z-10" />

      <Header 
        repoId={repoId} 
        repoUrl={repo?.url || ''} 
        repoStatus={repo?.status || ''} 
        activeTab="architecture" 
      />

      {/* Main Workspace */}
      <main className="w-full max-w-[1700px] mx-auto px-4 sm:px-6 lg:px-12 pt-[92px] pb-6 space-y-6 flex-grow">

        {/* Executive summary details cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-fade-in">
          <div className="premium-glass-card border border-cardBorder rounded-2xl p-6 flex items-center justify-between gap-6 bg-bgSecondary shadow-sm">
            <div className="space-y-2">
              <span className="text-xs text-textSecondary uppercase font-semibold tracking-wider">Architecture Health</span>
              <h2 className="text-4xl font-black text-textPrimary">{repoScore.score}<span className="text-lg text-textSecondary">/100</span></h2>
              <div className={`px-2.5 py-0.5 rounded-lg border text-xs font-bold inline-block ${GRADE_COLORS[repoScore.grade] || GRADE_COLORS.F}`}>
                Grade {repoScore.grade}
              </div>
            </div>
            <div className="relative w-20 h-20 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path className="text-slate-200 dark:text-zinc-800" strokeWidth="3" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path className={repoScore.score >= 80 ? 'text-emerald-500' : repoScore.score >= 60 ? 'text-amber-500' : 'text-rose-500'} strokeDasharray={`${repoScore.score}, 100`} strokeWidth="3" strokeLinecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <span className="absolute text-sm font-bold text-textPrimary">{repoScore.score}%</span>
            </div>
          </div>

          <div className="premium-glass-card border border-cardBorder rounded-2xl p-6 grid grid-cols-2 gap-4 bg-bgSecondary shadow-sm">
            <div>
              <span className="text-[10px] text-textSecondary uppercase tracking-wider font-semibold">Detected Pattern</span>
              <p className="text-sm font-bold text-textPrimary mt-0.5">{summary.pattern}</p>
              <span className="text-[10px] text-emerald-500 dark:text-emerald-400 font-bold uppercase tracking-wider">{summary.confidence >= 80 ? 'Validated' : 'Verified'}</span>
            </div>
            <div>
              <span className="text-[10px] text-textSecondary uppercase tracking-wider font-semibold">Entry Points</span>
              <p className="text-lg font-bold text-emerald-500 dark:text-emerald-400 mt-0.5">{summary.entry_points}</p>
            </div>
            <div>
              <span className="text-[10px] text-textSecondary uppercase tracking-wider font-semibold">Total Modules</span>
              <p className="text-lg font-bold text-textPrimary mt-0.5">{summary.total_modules}</p>
            </div>
            <div>
              <span className="text-[10px] text-textSecondary uppercase tracking-wider font-semibold">Cycles Found</span>
              <p className={`text-lg font-bold mt-0.5 ${summary.cycles_count > 0 ? 'text-rose-500' : 'text-textSecondary'}`}>{summary.cycles_count}</p>
            </div>
          </div>

          <div className="premium-glass-card border border-cardBorder rounded-2xl p-6 space-y-3 bg-bgSecondary shadow-sm">
            <span className="text-xs text-textSecondary uppercase font-semibold tracking-wider block">Dependency Statistics</span>
            <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-xs">
              <div className="flex justify-between border-b border-borderPrimary pb-1">
                <span className="text-textSecondary">Edges (Imports)</span>
                <span className="font-mono text-textPrimary font-semibold">{summary.stats.total_edges}</span>
              </div>
              <div className="flex justify-between border-b border-borderPrimary pb-1">
                <span className="text-textSecondary">Avg Imports</span>
                <span className="font-mono text-textPrimary font-semibold">{summary.stats.average_imports}</span>
              </div>
              <div className="flex justify-between border-b border-borderPrimary pb-1">
                <span className="text-textSecondary">Max Chain Depth</span>
                <span className="font-mono text-textPrimary font-semibold">{summary.stats.largest_chain}</span>
              </div>
              <div className="flex justify-between border-b border-borderPrimary pb-1">
                <span className="text-textSecondary">Max Coupling</span>
                <span className="font-mono text-textPrimary font-semibold">{summary.stats.highest_coupling_score}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Visualizer network & Module explorer sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          
          {/* Main Visualizer Network */}
          <div className="lg:col-span-3 bg-bgSecondary border border-borderPrimary rounded-2xl p-6 flex flex-col h-[520px] relative overflow-hidden shadow-sm">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 border-b border-borderPrimary pb-4 mb-4">
              <div>
                <h3 className="text-md font-bold text-textPrimary flex items-center gap-2"><GitBranch className="w-4 h-4 text-brand-500 dark:text-brand-400" /> Dependency Network</h3>
                {graphData?.is_truncated && (
                  <p className="text-[10px] text-amber-600 dark:text-amber-500 font-medium mt-0.5 font-sans">Showing top 40 coupled modules for rendering performance.</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <div className="relative w-full sm:w-48">
                  <input
                    type="text"
                    placeholder="Search module..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800 rounded-xl py-1.5 pl-8 pr-3 text-xs text-textPrimary placeholder-slate-400 dark:placeholder-zinc-500 focus:outline-none focus:border-brand-500 transition-all font-mono"
                  />
                  <Search className="w-3.5 h-3.5 text-slate-400 dark:text-zinc-500 absolute left-2.5 top-2.5" />
                </div>
                <button onClick={handleZoomToFit} className="p-1.5 bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-lg text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white transition-all hover:bg-slate-200 dark:hover:bg-zinc-800" title="Zoom to Fit">
                  <Maximize2 className="w-3.5 h-3.5" />
                </button>
                <button onClick={handleResetView} className="p-1.5 bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-lg text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white transition-all hover:bg-slate-200 dark:hover:bg-zinc-800" title="Reset View">
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="flex-grow bg-slate-50 dark:bg-zinc-950/60 rounded-xl border border-slate-200 dark:border-zinc-900/50 overflow-hidden relative">
              {graphData && graphData.nodes.length > 0 ? (
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onInit={setRfInstance}
                  onNodeClick={onNodeClick}
                  fitView
                  fitViewOptions={{ padding: 0.15 }}
                  minZoom={0.2}
                  maxZoom={2}
                >
                  <Background color={theme === 'dark' ? '#18181b' : '#cbd5e1'} gap={12} size={1} />
                </ReactFlow>
              ) : (
                <div className="absolute inset-0 flex items-center justify-center text-xs text-textSecondary">No analyzable modules found.</div>
              )}
            </div>

            <div className="flex flex-wrap gap-2.5 pt-4 text-[10px] text-textSecondary border-t border-borderPrimary mt-4 select-none">
              <span className="font-semibold mr-1">Legend:</span>
              {Object.entries(MODULE_TYPE_COLORS).filter(([k]) => k !== 'Unknown').map(([type, colors]) => (
                <div key={type} className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: colors.hex }} />
                  <span>{type}</span>
                </div>
              ))}
              <div className="flex items-center gap-1 ml-auto font-bold uppercase tracking-wider">
                <div className="w-2.5 h-2.5 border border-dashed border-[#10b981]" />
                <span>Incoming</span>
                <div className="w-2.5 h-2.5 border border-dashed border-[#ef4444] ml-2" />
                <span>Outgoing</span>
              </div>
            </div>
          </div>

          {/* Module Explorer Sidebar Panel */}
          <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-5 flex flex-col h-[520px] lg:col-span-1 shadow-sm">
            <h3 className="text-xs font-bold text-textPrimary uppercase tracking-wider pb-3 border-b border-borderPrimary flex items-center gap-1.5"><Cpu className="w-4 h-4 text-brand-500 dark:text-brand-400" /> Module Explorer</h3>
            
            {selectedModule ? (
              <div className="flex-grow flex flex-col justify-between pt-4 overflow-y-auto space-y-4 text-xs">
                
                <div className="space-y-4 flex-grow overflow-y-auto pr-1">
                  <div className="flex justify-between items-start gap-4">
                    <div className="space-y-1">
                      <h4 className="text-xs font-bold text-textPrimary font-mono break-all leading-normal">{selectedModule.path}</h4>
                      <span className={`px-2.5 py-0.5 rounded-lg border text-[9px] font-bold inline-block ${
                        MODULE_TYPE_COLORS[selectedModule.type]?.bg || MODULE_TYPE_COLORS.Unknown.bg
                      } ${MODULE_TYPE_COLORS[selectedModule.type]?.border || MODULE_TYPE_COLORS.Unknown.border} ${
                        MODULE_TYPE_COLORS[selectedModule.type]?.text || MODULE_TYPE_COLORS.Unknown.text
                      }`}>
                        {selectedModule.type}
                      </span>
                    </div>
                    <button onClick={() => { setSelectedModule(null); setSelectedFile(null); }} className="p-1 bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 text-slate-500 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-white rounded-lg transition-all" title="Clear selection">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {isSidebarLoading ? (
                    <div className="py-20 text-center">
                      <Loader2 className="w-6 h-6 animate-spin text-brand-500 mx-auto" />
                    </div>
                  ) : selectedFile ? (
                    <div className="space-y-4">
                      {/* Metric cards */}
                      <div className="grid grid-cols-2 gap-2 bg-slate-50 dark:bg-zinc-950/60 border border-slate-200 dark:border-zinc-900/60 p-2.5 rounded-xl text-center shadow-inner">
                        <div className="border-r border-slate-200 dark:border-zinc-900/50">
                          <span className="text-[9px] text-textSecondary block uppercase">LOC</span>
                          <span className="font-bold text-textPrimary font-mono">{selectedFile.lines_of_code}</span>
                        </div>
                        <div>
                          <span className="text-[9px] text-textSecondary block uppercase">Complexity</span>
                          <span className="font-bold text-textPrimary font-mono">{selectedFile.complexity}</span>
                        </div>
                      </div>

                      {/* Outline summary */}
                      <div className="bg-slate-50 dark:bg-zinc-950/30 border border-slate-200 dark:border-zinc-900/40 p-3 rounded-xl space-y-1.5">
                        <span className="text-[10px] text-textSecondary uppercase font-bold">Local Elements</span>
                        <div className="grid grid-cols-2 gap-2 text-[10px] text-textSecondary">
                          <div>Functions: <span className="font-bold text-textPrimary">{selectedFile.analysis_metadata?.metrics?.function_count || 0}</span></div>
                          <div>Classes: <span className="font-bold text-textPrimary">{selectedFile.analysis_metadata?.metrics?.class_count || 0}</span></div>
                          <div>Smells: <span className="font-bold text-rose-500">{selectedFile.code_smells_count}</span></div>
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {/* Coupling details */}
                  <div className="bg-slate-50 dark:bg-zinc-950/60 border border-slate-200 dark:border-zinc-900 rounded-xl p-3 space-y-1 shadow-inner">
                    <div className="flex justify-between">
                      <span className="text-textSecondary">Coupling Score</span>
                      <span className="font-bold text-textPrimary font-mono">{selectedModule.coupling}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-textSecondary">Instability</span>
                      <span className="font-bold text-textPrimary font-mono">{selectedModule.instability.toFixed(2)}</span>
                    </div>
                  </div>

                  {/* Dependency Lists */}
                  <div className="space-y-3">
                    <div className="space-y-1.5">
                      <span className="text-[9px] text-textSecondary uppercase font-bold block">Imports / Uses ({selectedImports.length})</span>
                      <div className="max-h-20 overflow-y-auto border border-slate-200 dark:border-zinc-900/50 rounded-xl p-2 bg-slate-50 dark:bg-zinc-950/30 text-[9px] font-mono space-y-1">
                        {selectedImports.map(p => (
                          <div key={p} className="text-textPrimary truncate" title={p}>{p.split('/').pop()}</div>
                        ))}
                        {selectedImports.length === 0 && <div className="text-textSecondary italic">None</div>}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <span className="text-[9px] text-textSecondary uppercase font-bold block">Imported By ({selectedImportedBy.length})</span>
                      <div className="max-h-20 overflow-y-auto border border-slate-200 dark:border-zinc-900/50 rounded-xl p-2 bg-slate-50 dark:bg-zinc-950/30 text-[9px] font-mono space-y-1">
                        {selectedImportedBy.map(p => (
                          <div key={p} className="text-textPrimary truncate" title={p}>{p.split('/').pop()}</div>
                        ))}
                        {selectedImportedBy.length === 0 && <div className="text-textSecondary italic">None</div>}
                      </div>
                    </div>
                  </div>
                </div>

                {selectedFile && (
                  <button
                    onClick={() => router.push(`/repositories/${repoId}`)}
                    className="w-full py-2 px-4 bg-slate-100 dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 hover:bg-slate-200 dark:hover:bg-zinc-800 text-textPrimary rounded-xl text-xs font-semibold transition-all text-center block mt-2 shadow-sm font-bold uppercase tracking-wider"
                  >
                    View File Detail
                  </button>
                )}
              </div>
            ) : (
              <div className="flex-grow flex items-center justify-center text-center p-6 text-textSecondary select-none">
                <div className="space-y-2">
                  <GitBranch className="w-8 h-8 text-slate-300 dark:text-zinc-700 mx-auto" />
                  <p className="text-xs font-medium">Click a node on the graph or search for a module to inspect its dependency structure.</p>
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Architecture Findings & Cycles Inspector Panel (Component 5 & 14) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Strengths & Warnings (Findings) */}
          <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-4 shadow-sm">
            <h3 className="text-xs text-textPrimary uppercase font-bold tracking-wider flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-brand-500 dark:text-brand-400" /> Architecture Findings
            </h3>
            <div className="space-y-4 text-xs leading-normal">
              {/* Strengths */}
              <div className="space-y-2">
                <span className="text-[10px] text-emerald-600 dark:text-emerald-400 uppercase font-bold block">Key Strengths</span>
                <div className="space-y-1.5">
                  {findings?.strengths.map((str, idx) => (
                    <div key={idx} className="flex gap-2 items-start p-2.5 bg-emerald-500/10 dark:bg-emerald-500/5 border border-emerald-500/10 rounded-xl text-textSecondary">
                      <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                      <div className="space-y-0.5">
                        <span className="font-bold text-textPrimary block">{str.title}</span>
                        <span>{str.description}</span>
                        {str.evidence && <span className="text-[10px] text-textSecondary block font-mono">Evidence: {str.evidence}</span>}
                      </div>
                    </div>
                  ))}
                  {(!findings || findings.strengths.length === 0) && (
                    <p className="text-textSecondary italic">No significant architectural strengths flagged.</p>
                  )}
                </div>
              </div>
              
              {/* Warnings */}
              <div className="space-y-2">
                <span className="text-[10px] text-rose-600 dark:text-rose-400 uppercase font-bold block">Design Warnings</span>
                <div className="space-y-1.5">
                  {findings?.warnings.map((warn, idx) => (
                    <div key={idx} className="flex gap-2 items-start p-2.5 bg-rose-500/10 dark:bg-rose-500/5 border border-rose-500/10 rounded-xl text-textSecondary">
                      <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
                      <div className="space-y-0.5">
                        <span className="font-bold text-textPrimary block">{warn.title}</span>
                        <span>{warn.description}</span>
                        {warn.evidence && <span className="text-[10px] text-textSecondary block font-mono">Evidence: {warn.evidence}</span>}
                      </div>
                    </div>
                  ))}
                  {(!findings || findings.warnings.length === 0) && (
                    <p className="text-textSecondary italic">Outstanding structure with no warnings flagged!</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Dependency Cycles List */}
          <div className="bg-bgSecondary border border-borderPrimary rounded-2xl p-6 space-y-4 shadow-sm">
            <h3 className="text-xs text-textPrimary uppercase font-bold tracking-wider flex items-center gap-1.5">
              <RefreshCw className="w-4 h-4 text-rose-500" /> Dependency Cycle Inspector
            </h3>
            
            <div className="space-y-3 text-xs leading-normal">
              <p className="text-textSecondary text-[11px] leading-relaxed">
                Circular dependencies form import loops that make it difficult to split modules or deploy code independently.
              </p>
              
              <div className="space-y-3 max-h-[220px] overflow-y-auto pr-1 font-mono text-[10px]">
                {summary?.cycles_list && summary.cycles_list.map((cycle, idx) => (
                  <div key={idx} className="p-3 bg-rose-500/5 border border-rose-500/10 rounded-xl space-y-2">
                    <span className="text-[9px] uppercase font-bold text-rose-600 dark:text-rose-400 font-sans">Cycle #{idx + 1} ({cycle.length} steps)</span>
                    <div className="space-y-1 pl-1">
                      {cycle.map((node, nIdx) => (
                        <div key={nIdx} className="flex items-center gap-1.5 truncate text-textSecondary">
                          <span className="text-textSecondary">{nIdx + 1}.</span>
                          <span className="truncate hover:text-brand-500 dark:hover:text-brand-450 cursor-pointer" onClick={() => setSelectedModule(graphData?.nodes.find(n => n.path === node) || null)}>{node.split('/').pop()}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                {(!summary?.cycles_list || summary.cycles_list.length === 0) && (
                  <div className="p-4 bg-emerald-500/10 dark:bg-emerald-500/5 border border-emerald-500/15 rounded-xl text-center font-sans text-emerald-600 dark:text-emerald-400 font-semibold">
                    ✓ Clean dependency tree! Zero cycles detected.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

      </main>

      <footer className="w-full text-center py-6 text-xs text-slate-500 dark:text-zinc-500 border-t border-slate-200 dark:border-zinc-900/40 mt-8 font-mono">
        Repository Mentor AI &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
}
