'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import {
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  MarkerType
} from 'reactflow';

import {
  ArrowLeft, Loader2, ShieldAlert, Layers, Shield, AlertTriangle,
  Search, ZoomIn, ZoomOut, Maximize2, RefreshCw, X, ChevronRight,
  Code, Bug, FileText, Check, AlertCircle, Sparkles, Filter,
  ArrowRight, Compass, HelpCircle
} from 'lucide-react';

import Header from '../../../Header';
import { useTheme } from '../../../ThemeProvider';
import { PageLayoutSkeleton } from '../../../components/Skeletons';
import { trackArchitectureExplored } from '../../../lib/analytics';

const GraphCanvas = dynamic(() => import('./GraphCanvas'), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 flex items-center justify-center bg-bgPrimary">
      <Loader2 className="w-8 h-8 animate-spin text-signal" />
    </div>
  ),
});

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

// Architectural Swim-Lanes Definition
const SWIM_LANES = [
  { key: 'controllers', label: '01 // CONTROLLERS & API', types: ['Controller', 'API', 'Router', 'Endpoint'], col: 0 },
  { key: 'services', label: '02 // SERVICES & DOMAIN', types: ['Service', 'Handler', 'Manager', 'Core'], col: 1 },
  { key: 'repositories', label: '03 // REPOSITORIES & DATA', types: ['Repository', 'DAO', 'Store', 'Persistence'], col: 2 },
  { key: 'models', label: '04 // MODELS & ENTITIES', types: ['Model', 'Entity', 'Schema', 'DTO'], col: 3 },
  { key: 'utilities', label: '05 // UTILITIES & HELPERS', types: ['Utility', 'Helper', 'Component', 'Hook'], col: 4 },
  { key: 'config', label: '06 // CONFIG & SECURITY', types: ['Configuration', 'Config', 'Security', 'Middleware'], col: 5 },
];

const NON_CODE_EXTS = ['.gitignore', '.properties', '.xml', '.yml', '.yaml', '.json', '.md', '.txt', '.cmd', '.sh'];

export default function ArchitectureExplorerPage({ params }: { params: { id: string } }) {
  const { theme } = useTheme();
  const router = useRouter();
  const repoId = params.id;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  // API states
  const [repo, setRepo] = useState<any>(null);
  const [summary, setSummary] = useState<ArchitectureSummary | null>(null);
  const [findings, setFindings] = useState<ArchitectureFindings | null>(null);
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Interaction states
  const [searchQuery, setSearchQuery] = useState('');
  const [showAllFiles, setShowAllFiles] = useState(false);
  const [selectedModule, setSelectedModule] = useState<GraphNodeData | null>(null);
  const [hoveredModulePath, setHoveredModulePath] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<SelectedFileDetail | null>(null);
  const [isSidebarLoading, setIsSidebarLoading] = useState(false);
  const [rfInstance, setRfInstance] = useState<any>(null);

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const isDark = theme === 'dark';

  // Determine lane for a node
  const getLaneIndex = (type: string, path: string): number => {
    const normType = type || '';
    const normPath = path.toLowerCase();

    for (let i = 0; i < SWIM_LANES.length; i++) {
      if (SWIM_LANES[i].types.some(t => t.toLowerCase() === normType.toLowerCase())) {
        return i;
      }
    }

    if (normPath.includes('controller') || normPath.includes('/api/')) return 0;
    if (normPath.includes('service')) return 1;
    if (normPath.includes('repository') || normPath.includes('repo')) return 2;
    if (normPath.includes('model') || normPath.includes('entity') || normPath.includes('schema')) return 3;
    if (normPath.includes('util') || normPath.includes('helper')) return 4;
    if (normPath.includes('config') || normPath.includes('security')) return 5;

    return 6; // Unclassified / Other
  };

  const isNonCodeFile = (path: string): boolean => {
    const filename = path.split('/').pop() || '';
    if (filename.startsWith('.') || filename === 'mvnw' || filename === 'mvnw.cmd') return true;
    return NON_CODE_EXTS.some(ext => filename.endsWith(ext));
  };

  const fetchData = useCallback(async () => {
    try {
      const repoRes = await fetch(`${apiUrl}/repositories/${repoId}`);
      if (!repoRes.ok) throw new Error('Repository detail not found.');
      const repoData = await repoRes.json();
      setRepo(repoData);

      const summaryRes = await fetch(`${apiUrl}/repositories/${repoId}/architecture/explorer`);
      if (!summaryRes.ok) throw new Error('Architecture details not found.');
      setSummary(await summaryRes.json());

      const findingsRes = await fetch(`${apiUrl}/repositories/${repoId}/architecture/findings`);
      if (findingsRes.ok) setFindings(await findingsRes.json());

      const graphRes = await fetch(`${apiUrl}/repositories/${repoId}/architecture/graph`);
      if (graphRes.ok) {
        const gd: GraphResponse = await graphRes.json();
        setGraphData(gd);
        trackArchitectureExplored(repoId);
      }
      setIsLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch architecture data.');
      setIsLoading(false);
    }
  }, [apiUrl, repoId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Compute Layout when graphData or showAllFiles changes
  useEffect(() => {
    if (!graphData) return;

    // Filter nodes
    const visibleRawNodes = graphData.nodes.filter(n => {
      if (!showAllFiles && isNonCodeFile(n.path)) return false;
      return true;
    });

    const visiblePaths = new Set(visibleRawNodes.map(n => n.path));

    // Group into lanes
    const laneBuckets: Record<number, GraphNodeData[]> = {};
    for (let i = 0; i <= 6; i++) laneBuckets[i] = [];

    visibleRawNodes.forEach(node => {
      const laneIdx = getLaneIndex(node.type, node.path);
      laneBuckets[laneIdx].push(node);
    });

    const LANE_WIDTH = 290;
    const NODE_HEIGHT = 80;
    const VERTICAL_GAP = 28;

    const flowNodes: Node[] = [];

    // Construct lane nodes
    Object.entries(laneBuckets).forEach(([laneStr, bucket]) => {
      const laneIdx = parseInt(laneStr, 10);
      const isUnclassified = laneIdx === 6;
      const x = isUnclassified ? 3 * LANE_WIDTH : laneIdx * LANE_WIDTH + 40;
      const startY = isUnclassified ? 600 : 120;

      bucket.forEach((n, k) => {
        const y = startY + k * (NODE_HEIGHT + VERTICAL_GAP);
        const filename = n.path.split('/').pop() || n.path;
        const displayType = n.type === 'Unknown' ? 'Unclassified' : n.type;

        flowNodes.push({
          id: n.path,
          type: 'default',
          position: { x, y },
          data: {
            label: (
              <div className="text-left font-mono py-1 px-1.5 space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-bold text-textPrimary truncate max-w-[160px]" title={n.path}>
                    {filename}
                  </span>
                  <span className={`text-[9px] px-1.5 py-0.2 rounded border font-mono uppercase ${
                    n.in_cycle 
                      ? 'text-bad bg-bad-bg border-bad-border font-bold'
                      : 'text-textSecondary bg-bgTertiary border-borderPrimary'
                  }`}>
                    {displayType}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px] text-textMuted font-mono">
                  <span>Fan-In: {n.coupling || 0}</span>
                  {n.in_cycle && <span className="text-bad font-bold">CYCLE</span>}
                </div>
              </div>
            )
          },
          style: {
            background: isDark ? '#1A1917' : '#FCFBF9',
            border: n.in_cycle ? '1.5px solid #B91C1C' : '1px solid var(--border-primary)',
            borderRadius: '6px',
            padding: '8px 10px',
            color: 'var(--text-primary)',
            width: 240,
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
            transition: 'border-color 150ms ease, opacity 150ms ease, box-shadow 150ms ease',
          }
        });
      });
    });

    // Visible edges
    const flowEdges: Edge[] = graphData.edges
      .filter(e => visiblePaths.has(e.source) && visiblePaths.has(e.target))
      .map(e => {
        const srcNode = graphData.nodes.find(n => n.path === e.source);
        const tgtNode = graphData.nodes.find(n => n.path === e.target);
        const inCycle = srcNode?.in_cycle && tgtNode?.in_cycle;

        return {
          id: e.id,
          source: e.source,
          target: e.target,
          type: 'smoothstep',
          animated: Boolean(inCycle),
          style: {
            stroke: inCycle ? '#B91C1C' : (isDark ? '#403D37' : '#C7C2B8'),
            strokeWidth: inCycle ? 2 : 1.25,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 10,
            height: 10,
            color: inCycle ? '#B91C1C' : (isDark ? '#403D37' : '#C7C2B8'),
          }
        };
      });

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [graphData, showAllFiles, isDark, setNodes, setEdges]);

  // Selected imports / imported-by sets
  const selectedImports = useMemo(() => {
    if (!selectedModule || !graphData) return [];
    return graphData.edges.filter(e => e.source === selectedModule.path).map(e => e.target);
  }, [selectedModule, graphData]);

  const selectedImportedBy = useMemo(() => {
    if (!selectedModule || !graphData) return [];
    return graphData.edges.filter(e => e.target === selectedModule.path).map(e => e.source);
  }, [selectedModule, graphData]);

  // Dynamic Highlighting on Select / Hover
  useEffect(() => {
    const activeTarget = selectedModule?.path || hoveredModulePath;

    setNodes(prevNodes =>
      prevNodes.map(node => {
        let isMatched = searchQuery ? node.id.toLowerCase().includes(searchQuery.toLowerCase()) : true;
        let opacity = isMatched ? 1.0 : 0.15;
        let borderColor = 'var(--border-primary)';
        let borderWidth = '1px';
        let shadow = 'none';

        if (activeTarget) {
          if (node.id === activeTarget) {
            borderColor = '#FF4D1C';
            borderWidth = '2px';
            opacity = 1.0;
            shadow = '0 0 0 1px #FF4D1C';
          } else if (selectedImportedBy.includes(node.id)) {
            borderColor = '#2D6A4F';
            borderWidth = '1.5px';
            opacity = 1.0;
          } else if (selectedImports.includes(node.id)) {
            borderColor = '#B91C1C';
            borderWidth = '1.5px';
            opacity = 1.0;
          } else {
            opacity = 0.2;
          }
        }

        return {
          ...node,
          style: {
            ...node.style,
            opacity,
            border: `${borderWidth} solid ${borderColor}`,
            boxShadow: shadow,
          }
        };
      })
    );

    setEdges(prevEdges =>
      prevEdges.map(edge => {
        let stroke = isDark ? '#403D37' : '#C7C2B8';
        let opacity = 1.0;
        let strokeWidth = 1.25;

        if (activeTarget) {
          if (edge.source === activeTarget) {
            stroke = '#FF4D1C';
            strokeWidth = 2;
          } else if (edge.target === activeTarget) {
            stroke = '#2D6A4F';
            strokeWidth = 2;
          } else {
            opacity = 0.08;
          }
        }

        return {
          ...edge,
          style: {
            ...edge.style,
            stroke,
            strokeWidth,
            opacity,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 10,
            height: 10,
            color: stroke,
          }
        };
      })
    );
  }, [selectedModule, hoveredModulePath, selectedImports, selectedImportedBy, searchQuery, isDark, setNodes, setEdges]);

  // Click a node to load file details in sidebar
  const handleNodeClick = async (_: any, node: Node) => {
    const rawModule = graphData?.nodes.find(n => n.path === node.id);
    if (!rawModule) return;

    setSelectedModule(rawModule);
    setIsSidebarLoading(true);

    try {
      const filesRes = await fetch(`${apiUrl}/repositories/${repoId}/files?limit=200`);
      if (filesRes.ok) {
        const data = await filesRes.json();
        const matched = data.files.find((f: any) => f.path === rawModule.path);
        if (matched) {
          const detailRes = await fetch(`${apiUrl}/repositories/${repoId}/files/${matched.id}`);
          if (detailRes.ok) {
            setSelectedFile(await detailRes.json());
          }
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSidebarLoading(false);
    }
  };

  const handleZoomIn = () => rfInstance?.zoomIn();
  const handleZoomOut = () => rfInstance?.zoomOut();
  const handleFitView = () => rfInstance?.fitView({ padding: 0.2, duration: 300 });

  if (isLoading) {
    return <PageLayoutSkeleton title="Mapping Swim-Lane Architecture..." />;
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bgPrimary px-4">
        <div className="max-w-md w-full bg-bgSecondary border border-borderPrimary p-8 rounded-lg shadow-report text-center space-y-4">
          <ShieldAlert className="w-8 h-8 text-bad mx-auto" />
          <h2 className="font-serif text-xl font-bold text-textPrimary">Architecture Map Unavailable</h2>
          <p className="text-xs text-textSecondary font-mono">{error}</p>
          <button onClick={() => router.push('/')} className="py-2 px-4 rounded bg-bgTertiary text-xs font-mono font-bold">
            Return Home
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
        activeTab="architecture" 
      />

      <div className="flex-grow flex flex-col lg:flex-row h-[calc(100vh-62px)] mt-[62px] overflow-hidden">
        
        {/* ========================================================
            MAIN CANVAS AREA: Top Toolbar + Swim-Lane Graph Canvas
           ======================================================== */}
        <div className="flex-grow flex flex-col h-full relative overflow-hidden hairline-r">
          
          {/* Top Control Bar */}
          <div className="px-6 py-3 bg-bgSecondary border-b border-borderPrimary flex flex-wrap items-center justify-between gap-3 z-10">
            <div className="flex items-center gap-3">
              <span className="section-header">SWIM-LANE TOPOLOGY</span>
              <span className="text-xs font-mono text-textMuted">•</span>
              <span className="text-xs font-mono text-textSecondary">
                Pattern: <strong className="text-textPrimary">{summary?.pattern || 'Layered Architecture'}</strong>
              </span>
              <span className="text-xs font-mono text-textMuted">•</span>
              <span className="text-xs font-mono text-textSecondary">
                {graphData?.nodes.length || 0} Modules
              </span>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-2">
              {/* Search */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-textMuted" />
                <input
                  type="text"
                  placeholder="Filter nodes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 pr-3 py-1 bg-bgPrimary border border-borderPrimary rounded text-xs font-mono text-textPrimary focus:outline-none focus:border-signal w-36 sm:w-44"
                />
              </div>

              {/* Show All Files Toggle */}
              <label className="flex items-center gap-1.5 text-xs font-mono text-textSecondary cursor-pointer px-2 py-1 rounded bg-bgPrimary border border-borderPrimary hover:border-borderStrong transition-colors">
                <input
                  type="checkbox"
                  checked={showAllFiles}
                  onChange={(e) => setShowAllFiles(e.target.checked)}
                  className="rounded border-borderPrimary text-signal focus:ring-0"
                />
                <span>Include Config/Scripts</span>
              </label>

              {/* Zoom Controls */}
              <div className="flex items-center gap-1 border border-borderPrimary rounded bg-bgPrimary p-0.5">
                <button onClick={handleZoomIn} className="p-1 hover:bg-bgTertiary text-textSecondary hover:text-textPrimary rounded" title="Zoom In">
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
                <button onClick={handleZoomOut} className="p-1 hover:bg-bgTertiary text-textSecondary hover:text-textPrimary rounded" title="Zoom Out">
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <button onClick={handleFitView} className="p-1 hover:bg-bgTertiary text-textSecondary hover:text-textPrimary rounded" title="Fit to Screen">
                  <Maximize2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Swim-Lane Column Headers */}
          <div className="bg-bgTertiary/70 border-b border-borderPrimary px-6 py-2 flex items-center overflow-x-auto text-[10px] font-mono font-bold text-textSecondary">
            {SWIM_LANES.map(lane => (
              <div key={lane.key} className="w-[290px] shrink-0 text-left pl-2">
                {lane.label}
              </div>
            ))}
          </div>

          {/* ReactFlow Canvas Viewport */}
          <div className="flex-grow relative bg-bgPrimary">
            <GraphCanvas
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onInit={setRfInstance}
              onNodeClick={handleNodeClick}
              onNodeMouseEnter={(_, node) => setHoveredModulePath(node.id)}
              onNodeMouseLeave={() => setHoveredModulePath(null)}
              theme={theme || 'light'}
            />

            {/* Architecture Legend */}
            <div className="absolute bottom-4 left-4 bg-bgSecondary/95 backdrop-blur-sm border border-borderPrimary p-3 rounded shadow-report text-[10px] font-mono space-y-1.5 z-10">
              <span className="section-header block mb-1">GRAPH LEGEND</span>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded border border-signal bg-signal/20" />
                <span>Selected Module</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded border border-good bg-good-bg" />
                <span>Incoming Caller (Depended On)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded border border-bad bg-bad-bg" />
                <span>Outgoing Import (Dependency)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded border border-bad-border bg-bad-bg" />
                <span>Cyclic Dependency Risk</span>
              </div>
            </div>
          </div>
        </div>

        {/* ========================================================
            RIGHT SIDE PANEL: Active Node Details OR Architectural Summary
           ======================================================== */}
        <div className="w-full lg:w-[420px] shrink-0 bg-bgSecondary flex flex-col h-full overflow-y-auto">
          
          {selectedModule ? (
            /* ACTIVE NODE INSPECTION PANEL */
            <div className="p-6 space-y-6 animate-fade-in">
              {/* Header */}
              <div className="flex items-start justify-between gap-3 border-b border-borderPrimary pb-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="section-header">MODULE INSPECTOR</span>
                    <span className="px-1.5 py-0.2 bg-bgTertiary border border-borderPrimary text-[9px] font-mono rounded uppercase">
                      {selectedModule.type === 'Unknown' ? 'Unclassified' : selectedModule.type}
                    </span>
                  </div>
                  <h3 className="font-serif text-xl font-bold text-textPrimary break-all">
                    {selectedModule.path.split('/').pop()}
                  </h3>
                  <span className="text-[11px] font-mono text-textMuted block break-all">
                    {selectedModule.path}
                  </span>
                </div>
                <button
                  onClick={() => { setSelectedModule(null); setSelectedFile(null); }}
                  className="p-1 hover:bg-bgTertiary text-textSecondary rounded transition-colors"
                  title="Close inspector"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* What It Does Summary */}
              <div className="space-y-2">
                <span className="section-header">ROLE IN CODEBASE</span>
                <p className="text-xs text-textSecondary leading-relaxed bg-bgPrimary p-3 rounded border border-borderPrimary">
                  {selectedModule.type === 'Controller' && 'Acts as an HTTP request gateway, handling routing, parameter parsing, and delegating business execution to services.'}
                  {selectedModule.type === 'Service' && 'Encapsulates core domain business logic, coordinating state mutations and data persistence.'}
                  {selectedModule.type === 'Repository' && 'Provides data access abstractions, executing database transactions and querying storage.'}
                  {selectedModule.type === 'Model' && 'Represents domain entities, data transfer objects, and schema representations.'}
                  {selectedModule.type === 'Utility' && 'Provides stateless helper functions, encoding algorithms, and cross-cutting utilities.'}
                  {selectedModule.type === 'Configuration' && 'Configures framework context, security rules, and dependency injection lifecycles.'}
                  {(!['Controller', 'Service', 'Repository', 'Model', 'Utility', 'Configuration'].includes(selectedModule.type)) && 'Classified source file within the project structure.'}
                </p>
              </div>

              {/* Metrics Breakdown */}
              <div className="space-y-2">
                <span className="section-header">SOURCE METRICS</span>
                <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                  <div className="p-2.5 bg-bgPrimary border border-borderPrimary rounded">
                    <span className="text-textMuted text-[10px] block">LINES (LOC)</span>
                    <strong className="text-base text-textPrimary">{selectedFile?.lines_of_code || '—'}</strong>
                  </div>
                  <div className="p-2.5 bg-bgPrimary border border-borderPrimary rounded">
                    <span className="text-textMuted text-[10px] block">COMPLEXITY</span>
                    <strong className={`text-base ${(selectedFile?.complexity || 0) > 15 ? 'text-bad' : 'text-good'}`}>
                      {selectedFile?.complexity || '—'}
                    </strong>
                  </div>
                  <div className="p-2.5 bg-bgPrimary border border-borderPrimary rounded">
                    <span className="text-textMuted text-[10px] block">SMELLS</span>
                    <strong className={`text-base ${(selectedFile?.code_smells_count || 0) > 0 ? 'text-warn' : 'text-good'}`}>
                      {selectedFile?.code_smells_count || 0}
                    </strong>
                  </div>
                </div>
              </div>

              {/* Outgoing Imports */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="section-header">OUTGOING DEPENDENCIES ({selectedImports.length})</span>
                  <span className="text-[10px] font-mono text-bad">Imports</span>
                </div>
                {selectedImports.length > 0 ? (
                  <div className="space-y-1 max-h-36 overflow-y-auto text-xs font-mono">
                    {selectedImports.map((imp, idx) => (
                      <div key={idx} className="p-2 bg-bgPrimary border border-borderPrimary rounded flex items-center justify-between">
                        <span className="truncate text-textPrimary" title={imp}>{imp.split('/').pop()}</span>
                        <ArrowRight className="w-3 h-3 text-bad shrink-0" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-3 bg-bgPrimary border border-borderPrimary rounded text-xs font-mono text-textMuted">
                    No internal module imports detected.
                  </div>
                )}
              </div>

              {/* Incoming Callers */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="section-header">INCOMING CALLERS ({selectedImportedBy.length})</span>
                  <span className="text-[10px] font-mono text-good">Imported By</span>
                </div>
                {selectedImportedBy.length > 0 ? (
                  <div className="space-y-1 max-h-36 overflow-y-auto text-xs font-mono">
                    {selectedImportedBy.map((caller, idx) => (
                      <div key={idx} className="p-2 bg-bgPrimary border border-borderPrimary rounded flex items-center justify-between">
                        <span className="truncate text-textPrimary" title={caller}>{caller.split('/').pop()}</span>
                        <Check className="w-3 h-3 text-good shrink-0" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-3 bg-bgPrimary border border-borderPrimary rounded text-xs font-mono text-textMuted">
                    Not imported by other internal modules (entrypoint candidate).
                  </div>
                )}
              </div>

              {/* Ask Mentor CTA */}
              <button
                onClick={() => {
                  const prompt = `Review the architecture of \`${selectedModule.path}\`. Explain its coupling, role, and any recommended refactoring.`;
                  router.push(`/repositories/${repoId}/mentor?q=${encodeURIComponent(prompt)}`);
                }}
                className="w-full py-2.5 px-4 bg-signal text-white rounded font-mono font-bold text-xs flex items-center justify-center gap-1.5 transition-colors hover:bg-signal-hover shadow-sm"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Ask AI Mentor to Review Module</span>
              </button>
            </div>
          ) : (
            /* DEFAULT ARCHITECTURAL OVERVIEW SUMMARY (NEVER EMPTY) */
            <div className="p-6 space-y-6 animate-fade-in">
              <div className="border-b border-borderPrimary pb-4 space-y-1">
                <span className="section-header">TOPOLOGICAL SUMMARY</span>
                <h3 className="font-serif text-2xl font-bold text-textPrimary">
                  {summary?.pattern || 'Layered Architecture'}
                </h3>
                <p className="text-xs text-textSecondary font-sans">
                  Click any node on the left canvas to inspect its direct imports, incoming callers, and maintainability metrics.
                </p>
              </div>

              {/* Key Indicators */}
              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-3 bg-bgPrimary border border-borderPrimary rounded space-y-1">
                  <span className="text-[10px] text-textMuted uppercase block">TOTAL MODULES</span>
                  <span className="text-2xl font-black text-textPrimary">{summary?.total_modules || 0}</span>
                </div>
                <div className="p-3 bg-bgPrimary border border-borderPrimary rounded space-y-1">
                  <span className="text-[10px] text-textMuted uppercase block">CIRCULAR CYCLES</span>
                  <span className={`text-2xl font-black ${(summary?.cycles_count || 0) > 0 ? 'text-bad' : 'text-good'}`}>
                    {summary?.cycles_count || 0}
                  </span>
                </div>
              </div>

              {/* Strengths & Observations */}
              {findings?.strengths && findings.strengths.length > 0 && (
                <div className="space-y-2">
                  <span className="section-header">ARCHITECTURAL STRENGTHS</span>
                  <div className="space-y-2 text-xs">
                    {findings.strengths.map((st, i) => (
                      <div key={i} className="p-3 bg-good-bg border border-good-border rounded space-y-1">
                        <span className="font-bold text-good block">{st.title}</span>
                        <p className="text-textSecondary text-[11px] leading-relaxed">{st.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Warnings / Smells */}
              {findings?.warnings && findings.warnings.length > 0 && (
                <div className="space-y-2">
                  <span className="section-header">ARCHITECTURAL WARNINGS</span>
                  <div className="space-y-2 text-xs">
                    {findings.warnings.map((warn, i) => (
                      <div key={i} className="p-3 bg-warn-bg border border-warn-border rounded space-y-1">
                        <span className="font-bold text-warn block">{warn.title}</span>
                        <p className="text-textSecondary text-[11px] leading-relaxed">{warn.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tips */}
              <div className="p-3 bg-bgPrimary border border-borderPrimary rounded text-[11px] font-mono text-textMuted space-y-1">
                <span className="font-bold text-textPrimary block">💡 Navigation Tip:</span>
                <p>Use mouse wheel or trackpad to pan and zoom. Drag nodes to customize arrangement.</p>
              </div>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
