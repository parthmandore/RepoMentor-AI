import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class CodeSmellResponse(BaseModel):
    id: uuid.UUID
    file_path: str
    smell_type: str
    category: str
    severity: str
    line_number: Optional[int] = None
    measured_value: float
    threshold: float
    reason: str

    class Config:
        from_attributes = True


class FileRankingEntry(BaseModel):
    file_id: uuid.UUID
    path: str
    value: float
    label: str


class FileDetailResponse(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    path: str
    extension: Optional[str] = None
    size_bytes: int
    is_text: bool
    lines_of_code: int
    complexity: int
    code_smells_count: int
    status_badge: str
    analysis_metadata: Optional[Dict[str, Any]] = None
    smells: List[CodeSmellResponse] = []

    class Config:
        from_attributes = True


class PaginatedSmellsResponse(BaseModel):
    total: int
    skip: int
    limit: int
    smells: List[CodeSmellResponse]
