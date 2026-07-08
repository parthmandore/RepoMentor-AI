import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class RepositoryCreate(BaseModel):
    url: str


class RepositorySubmitResponse(BaseModel):
    id: uuid.UUID
    status: str


class RepositoryResponse(BaseModel):
    id: uuid.UUID
    url: str
    status: str
    status_message: Optional[str] = None

    # Discovery Statistics (Phase 2)
    total_files: int
    total_folders: int
    text_file_count: int
    binary_file_count: int
    language_breakdown: Optional[Dict[str, int]] = None
    tech_stack: Optional[Dict[str, Any]] = None

    # Analysis Summary (Phase 3)
    health_score: int
    health_grade: str
    total_lines_of_code: int
    average_complexity: float
    max_complexity: int
    total_smells: int
    duplication_percentage: float
    files_analyzed: int
    files_skipped: int

    # Ingestion timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Analysis timing
    analysis_started_at: Optional[datetime] = None
    analysis_completed_at: Optional[datetime] = None
    analysis_duration_seconds: Optional[float] = None

    # Architecture Explorer Summary (Phase 4)
    architecture_score: int
    architecture_grade: str
    architecture_summary: Optional[Dict[str, Any]] = None
    architecture_findings: Optional[Dict[str, Any]] = None

    # Security Summary (Phase 5)
    security_score: int
    security_grade: str
    security_summary: Optional[Dict[str, Any]] = None
    security_findings: Optional[Dict[str, Any]] = None

    # Knowledge Summary (Phase 6)
    knowledge_status: str = "pending"
    knowledge_summary: Optional[Dict[str, Any]] = None

    error_message: Optional[str] = None
    created_at: datetime

    # Progress stages metadata (Component 5)
    progress: Optional[Dict[str, Any]] = None
    current_stage: Optional[str] = None

    class Config:
        from_attributes = True


class RepositoryFileResponse(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    path: str
    extension: Optional[str] = None
    size_bytes: int
    content_hash: str
    is_text: bool
    lines_of_code: int = 0
    complexity: int = 0
    code_smells_count: int = 0
    module_type: str = "Unknown"
    coupling_score: int = 0
    instability_score: float = 0.0
    in_dependency_cycle: bool = False

    class Config:
        from_attributes = True


class PaginatedFilesResponse(BaseModel):
    total: int
    skip: int
    limit: int
    files: List[RepositoryFileResponse]
