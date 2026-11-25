'use client';

import React from 'react';
import ReactFlow, {
  Background,
  Node,
  Edge,
  OnNodesChange,
  OnEdgesChange,
  ReactFlowInstance,
} from 'reactflow';
import 'reactflow/dist/style.css';

interface GraphCanvasProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onInit: (instance: ReactFlowInstance) => void;
  onNodeClick: (_: any, node: Node) => void;
  onNodeMouseEnter?: (_: any, node: Node) => void;
  onNodeMouseLeave?: (_: any, node: Node) => void;
  theme: string;
}

export default function GraphCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onInit,
  onNodeClick,
  onNodeMouseEnter,
  onNodeMouseLeave,
  theme,
}: GraphCanvasProps) {
  const isDark = theme === 'dark';
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onInit={onInit}
      onNodeClick={onNodeClick}
      onNodeMouseEnter={onNodeMouseEnter}
      onNodeMouseLeave={onNodeMouseLeave}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.15}
      maxZoom={2.5}
    >
      <Background 
        color={isDark ? '#2A2825' : '#E2DDD5'} 
        gap={20} 
        size={1} 
      />
    </ReactFlow>
  );
}
