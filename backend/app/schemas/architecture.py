import uuid
from typing import List, Dict, Optional, Any
from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    path: str
    type: str
    coupling: int
    instability: float
    in_cycle: bool


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str


class ArchitectureGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    is_truncated: bool
    total_nodes: int


class FindingEntry(BaseModel):
    title: str
    description: str
    evidence: Optional[str] = None


class ArchitectureFindingsResponse(BaseModel):
    strengths: List[FindingEntry]
    warnings: List[FindingEntry]


class DependencyStats(BaseModel):
    total_edges: int
    average_imports: float
    highest_fan_in: str
    highest_fan_out: str
    largest_chain: int
    highest_coupling_score: int


class ArchitectureSummaryResponse(BaseModel):
    pattern: str
    confidence: int
    evidence: List[str]
    total_modules: int
    entry_points: int
    cycles_count: int
    most_coupled_module: str
    stats: DependencyStats
    cycles_list: List[List[str]]


class ModuleDetailResponse(BaseModel):
    path: str
    module_type: str
    incoming: List[str]
    outgoing: List[str]
    coupling_score: int
    instability_score: float
    in_dependency_cycle: bool
