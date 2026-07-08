import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel


class SecurityIssueResponse(BaseModel):
    id: uuid.UUID
    file_path: str
    line_number: Optional[int] = None
    severity: str
    category: str
    title: str
    evidence: str
    snippet: Optional[str] = None
    reason: str
    recommendation: str = "AI Recommendation available after repository assessment."
    created_at: datetime

    class Config:
        from_attributes = True


class DependencyStats(BaseModel):
    total_dependencies: int
    safe_dependencies: int
    vulnerable_dependencies: int
    most_severe_vulnerability: str
    total_known_cves: int


class ScanStats(BaseModel):
    files_scanned: int
    files_skipped: int
    dependencies_parsed: int
    secrets_checked: int
    issues_found: int


class SecuritySummaryResponse(BaseModel):
    score: int
    grade: str
    severity_counts: Dict[str, int]
    category_counts: Dict[str, int]
    badges: List[str]
    dependency_stats: DependencyStats
    scan_stats: ScanStats


class FindingEntry(BaseModel):
    title: str
    description: str
    evidence: Optional[str] = None


class SecurityFindingsResponse(BaseModel):
    strengths: List[FindingEntry]
    warnings: List[FindingEntry]


class PaginatedSecurityIssuesResponse(BaseModel):
    total: int
    skip: int
    limit: int
    issues: List[SecurityIssueResponse]
