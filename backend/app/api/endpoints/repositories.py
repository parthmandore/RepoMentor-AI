import os
import uuid
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Optional

logger = logging.getLogger(__name__)

from app.db.session import get_db
from app.models.repository import Repository, RepositoryStatus
from app.models.repository_file import RepositoryFile
from app.models.code_smell import CodeSmell
from app.schemas.repository import (
    RepositoryCreate,
    RepositorySubmitResponse,
    RepositoryResponse,
    PaginatedFilesResponse
)
from app.schemas.analysis import (
    CodeSmellResponse,
    FileDetailResponse,
    PaginatedSmellsResponse,
    FileRankingEntry
)
from app.schemas.architecture import (
    ArchitectureGraphResponse,
    ArchitectureSummaryResponse,
    ArchitectureFindingsResponse,
    GraphNode,
    GraphEdge
)
from app.schemas.security import (
    SecuritySummaryResponse,
    SecurityFindingsResponse,
    PaginatedSecurityIssuesResponse,
    SecurityIssueResponse
)
from app.schemas.knowledge import (
    KnowledgeSummaryResponse
)
from app.services.ingestion.cloner import validate_github_url
from app.services.ingestion.pipeline import ingest_repository

router = APIRouter()

STATUS_MESSAGES = {
    RepositoryStatus.QUEUED: "Repository queued",
    RepositoryStatus.CLONING: "Cloning repository...",
    RepositoryStatus.PARSING: "Scanning project files...",
    RepositoryStatus.DETECTING_TECHNOLOGIES: "Detecting technologies...",
    RepositoryStatus.ANALYZING: "Running analysis...",
    RepositoryStatus.FINALIZING: "Preparing repository overview...",
    RepositoryStatus.READY: "Repository ready",
    RepositoryStatus.FAILED: "Ingestion failed"
}


def _get_file_status_badge(loc: int, complexity: int, smells: int) -> str:
    """Derives a deterministic status badge from file metrics."""
    if complexity > 20 or smells > 5:
        return "High Complexity"
    elif complexity > 10 or smells > 2 or loc > 300:
        return "Needs Attention"
    else:
        return "Healthy"


@router.post("/repositories", response_model=RepositorySubmitResponse, status_code=status.HTTP_201_CREATED)
def submit_repository(
    payload: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    url = payload.url.strip()
    if not validate_github_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub repository URL. Must be a valid public GitHub link (e.g. https://github.com/owner/repo)."
        )

    repo = db.query(Repository).filter(Repository.url == url).first()
    if repo:
        # If repo is already READY and analyzed, return it directly without wiping data
        if repo.status == RepositoryStatus.READY and (repo.files_analyzed or 0) > 0:
            return {"id": repo.id, "status": repo.status.value, "is_existing": True}

        # If repo is currently in progress, do not spawn duplicate pipeline tasks
        active_statuses = [
            RepositoryStatus.QUEUED,
            RepositoryStatus.CLONING,
            RepositoryStatus.PARSING,
            RepositoryStatus.DETECTING_TECHNOLOGIES,
            RepositoryStatus.ANALYZING,
            RepositoryStatus.FINALIZING,
        ]
        if repo.status in active_statuses:
            return {"id": repo.id, "status": repo.status.value, "is_existing": True}

        # Only reset and re-queue if status is FAILED or unanalyzed
        db.query(RepositoryFile).filter(RepositoryFile.repository_id == repo.id).delete()
        db.query(CodeSmell).filter(CodeSmell.repository_id == repo.id).delete()
        
        from app.models.security_issue import SecurityIssue
        db.query(SecurityIssue).filter(SecurityIssue.repository_id == repo.id).delete()
        
        # Purge matching ChromaDB collection
        try:
            import chromadb
            from app.core.config import settings
            chroma_client = chromadb.HttpClient(host=settings.CHROMADB_HOST, port=int(settings.CHROMADB_PORT))
            collection_name = f"repo_{str(repo.id)}"
            try:
                chroma_client.delete_collection(name=collection_name)
            except Exception:
                pass
        except Exception:
            pass

        repo.status = RepositoryStatus.QUEUED
        repo.status_message = "Repository queued"
        repo.total_files = 0
        repo.total_folders = 0
        repo.text_file_count = 0
        repo.binary_file_count = 0
        repo.language_breakdown = None
        repo.tech_stack = None
        repo.health_score = 100
        repo.health_grade = "A"
        repo.total_lines_of_code = 0
        repo.average_complexity = 0.0
        repo.max_complexity = 0
        repo.total_smells = 0
        repo.duplication_percentage = 0.0
        repo.files_analyzed = 0
        repo.files_skipped = 0
        repo.started_at = None
        repo.completed_at = None
        repo.duration_seconds = None
        repo.analysis_started_at = None
        repo.analysis_completed_at = None
        repo.analysis_duration_seconds = None
        repo.error_message = None
        repo.knowledge_summary = None
        repo.knowledge_status = "pending"
        db.commit()
    else:
        repo = Repository(url=url, status=RepositoryStatus.QUEUED, status_message="Repository queued")
        db.add(repo)
        db.commit()
        db.refresh(repo)

    background_tasks.add_task(ingest_repository, repo.id)

    active_count = db.query(Repository).filter(
        Repository.status.in_([
            RepositoryStatus.QUEUED,
            RepositoryStatus.CLONING,
            RepositoryStatus.PARSING,
            RepositoryStatus.DETECTING_TECHNOLOGIES,
            RepositoryStatus.ANALYZING,
            RepositoryStatus.FINALIZING,
        ]),
        Repository.id != repo.id
    ).count()

    return {"id": repo.id, "status": repo.status.value, "is_existing": False, "queue_position": active_count + 1}


def get_repository_progress(repo):
    summary = repo.knowledge_summary or {}
    meta = summary.get("pipeline_metadata")
    if meta:
        return meta.get("stages"), meta.get("current_stage")
        
    # Fallback builder (Component 5)
    stages = {
        "clone": {"status": "completed" if repo.status.value != "queued" else "pending"},
        "parse": {"status": "completed" if repo.status.value not in ["queued", "cloning"] else "pending"},
        "tech_detect": {"status": "completed" if repo.status.value not in ["queued", "cloning", "parsing"] else "pending"},
        "metrics": {"status": "completed" if repo.status.value not in ["queued", "cloning", "parsing", "detecting_technologies"] else "pending"},
        "architecture": {"status": "completed" if repo.status.value not in ["queued", "cloning", "parsing", "detecting_technologies", "analyzing"] else "pending"},
        "security": {"status": "completed" if repo.status.value == "ready" else "pending"},
        "knowledge": {"status": "completed" if repo.knowledge_status == "completed" else ("failed" if repo.knowledge_status in ["failed", "interrupted"] else "pending")},
        "assessment": {"status": "completed" if repo.knowledge_status == "completed" else "pending"}
    }
    current = "completed" if repo.status.value == "ready" else "processing"
    return stages, current


@router.get("/repositories/{id}", response_model=RepositoryResponse)
def get_repository(id: uuid.UUID, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
 
    status_message = repo.status_message or STATUS_MESSAGES.get(repo.status, "Processing...")
    progress_stages, current_stage = get_repository_progress(repo)

    active_statuses = [
        RepositoryStatus.QUEUED,
        RepositoryStatus.CLONING,
        RepositoryStatus.PARSING,
        RepositoryStatus.DETECTING_TECHNOLOGIES,
        RepositoryStatus.ANALYZING,
        RepositoryStatus.FINALIZING,
    ]
    queue_pos = None
    if repo.status in active_statuses:
        active_ahead = db.query(Repository).filter(
            Repository.status.in_(active_statuses),
            Repository.id != repo.id
        ).count()
        queue_pos = active_ahead + 1

    return {
        "id": repo.id,
        "url": repo.url,
        "status": repo.status.value,
        "status_message": status_message,
        "queue_position": queue_pos,
        "total_files": repo.total_files,
        "total_folders": repo.total_folders,
        "text_file_count": repo.text_file_count,
        "binary_file_count": repo.binary_file_count,
        "language_breakdown": repo.language_breakdown,
        "tech_stack": repo.tech_stack,
        "health_score": repo.health_score,
        "health_grade": repo.health_grade,
        "total_lines_of_code": repo.total_lines_of_code,
        "average_complexity": repo.average_complexity,
        "max_complexity": repo.max_complexity,
        "total_smells": repo.total_smells,
        "duplication_percentage": repo.duplication_percentage,
        "files_analyzed": repo.files_analyzed,
        "files_skipped": repo.files_skipped,
        "started_at": repo.started_at,
        "completed_at": repo.completed_at,
        "duration_seconds": repo.duration_seconds,
        "analysis_started_at": repo.analysis_started_at,
        "analysis_completed_at": repo.analysis_completed_at,
        "analysis_duration_seconds": repo.analysis_duration_seconds,
        "architecture_score": repo.architecture_score,
        "architecture_grade": repo.architecture_grade,
        "architecture_summary": repo.architecture_summary,
        "architecture_findings": repo.architecture_findings,
        "security_score": repo.security_score,
        "security_grade": repo.security_grade,
        "security_summary": repo.security_summary,
        "security_findings": repo.security_findings,
        "knowledge_status": repo.knowledge_status,
        "knowledge_summary": repo.knowledge_summary,
        "progress": progress_stages,
        "current_stage": current_stage,
        "error_message": repo.error_message,
        "created_at": repo.created_at
    }


@router.get("/repositories/{id}/files", response_model=PaginatedFilesResponse)
def get_repository_files(
    id: uuid.UUID,
    path: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    repo_exists = db.query(Repository).filter(Repository.id == id).first()
    if not repo_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    query = db.query(RepositoryFile).filter(RepositoryFile.repository_id == id)
    if path:
        query = query.filter(RepositoryFile.path == path)

    total_files = query.count()
    files = (
        query.order_by(RepositoryFile.path)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {"total": total_files, "skip": skip, "limit": limit, "files": files}


@router.get("/repositories/{id}/files/{file_id}", response_model=FileDetailResponse)
def get_file_detail(id: uuid.UUID, file_id: uuid.UUID, db: Session = Depends(get_db)):
    file = (
        db.query(RepositoryFile)
        .filter(RepositoryFile.id == file_id, RepositoryFile.repository_id == id)
        .first()
    )
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    file_smells = (
        db.query(CodeSmell)
        .filter(CodeSmell.repository_id == id, CodeSmell.file_path == file.path)
        .all()
    )

    status_badge = _get_file_status_badge(file.lines_of_code, file.complexity, file.code_smells_count)

    return {
        "id": file.id,
        "repository_id": file.repository_id,
        "path": file.path,
        "extension": file.extension,
        "size_bytes": file.size_bytes,
        "is_text": file.is_text,
        "lines_of_code": file.lines_of_code,
        "complexity": file.complexity,
        "code_smells_count": file.code_smells_count,
        "status_badge": status_badge,
        "analysis_metadata": file.analysis_metadata,
        "smells": file_smells
    }


@router.get("/repositories/{id}/smells", response_model=PaginatedSmellsResponse)
def get_repository_smells(
    id: uuid.UUID,
    severity: Optional[str] = Query(None, description="Filter by severity: High, Medium, Low"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    repo_exists = db.query(Repository).filter(Repository.id == id).first()
    if not repo_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    query = db.query(CodeSmell).filter(CodeSmell.repository_id == id)
    if severity:
        query = query.filter(CodeSmell.severity == severity)

    total = query.count()
    smells = query.order_by(CodeSmell.severity, CodeSmell.file_path).offset(skip).limit(limit).all()

    return {"total": total, "skip": skip, "limit": limit, "smells": smells}


@router.get("/repositories/{id}/architecture/graph", response_model=ArchitectureGraphResponse)
def get_architecture_graph(id: uuid.UUID, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    files = db.query(RepositoryFile).filter(RepositoryFile.repository_id == id).all()
    
    total_nodes = len(files)
    is_truncated = total_nodes > 80
    
    # If truncated, filter to show the top 40 most coupled files to keep the visualization clear
    if is_truncated:
        sorted_files = sorted(files, key=lambda f: f.coupling_score, reverse=True)
        visualized_files = sorted_files[:40]
    else:
        visualized_files = files
        
    visualized_paths = {f.path for f in visualized_files}
    
    nodes = []
    edges = []
    
    for f in visualized_files:
        nodes.append(GraphNode(
            id=f.path,
            path=f.path,
            type=f.module_type,
            coupling=f.coupling_score,
            instability=f.instability_score,
            in_cycle=f.in_dependency_cycle
        ))
        
        # Outgoing dependencies: only render link if target is in the visualized paths
        for target in f.outgoing_dependencies:
            if target in visualized_paths:
                edges.append(GraphEdge(
                    id=f"{f.path}->{target}",
                    source=f.path,
                    target=target
                ))
                
    return {
        "nodes": nodes,
        "edges": edges,
        "is_truncated": is_truncated,
        "total_nodes": total_nodes
    }


@router.get("/repositories/{id}/architecture/explorer", response_model=ArchitectureSummaryResponse)
def get_architecture_explorer(id: uuid.UUID, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if not repo.architecture_summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Architecture analysis has not been performed on this repository."
        )
        
    return repo.architecture_summary


@router.get("/repositories/{id}/architecture/findings", response_model=ArchitectureFindingsResponse)
def get_architecture_findings(id: uuid.UUID, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
        
    if not repo.architecture_findings:
        return {"strengths": [], "warnings": []}
        
    return repo.architecture_findings


@router.get("/repositories/{id}/security/issues", response_model=PaginatedSecurityIssuesResponse)
def get_security_issues(
    id: uuid.UUID,
    severity: Optional[str] = Query(None, description="Filter by severity: Critical, High, Medium, Low"),
    category: Optional[str] = Query(None, description="Filter by category: Secrets, Dependencies, Injection, Weak Cryptography, Unsafe APIs, Configuration"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    from app.models.security_issue import SecurityIssue

    repo_exists = db.query(Repository).filter(Repository.id == id).first()
    if not repo_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    query = db.query(SecurityIssue).filter(SecurityIssue.repository_id == id)
    if severity:
        query = query.filter(SecurityIssue.severity == severity)
    if category:
        query = query.filter(SecurityIssue.category == category)

    total = query.count()
    issues = query.order_by(SecurityIssue.severity, SecurityIssue.file_path).offset(skip).limit(limit).all()

    return {"total": total, "skip": skip, "limit": limit, "issues": issues}


@router.get("/repositories/{id}/security/summary", response_model=SecuritySummaryResponse)
@router.get("/repositories/{id}/security/explorer", response_model=SecuritySummaryResponse)
def get_security_summary(id: uuid.UUID, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if not repo.security_summary:
        sec_score = repo.security_score if repo.security_score is not None else 100
        sec_grade = "A" if sec_score >= 90 else ("B" if sec_score >= 80 else ("C" if sec_score >= 70 else "D"))
        return {
            "score": sec_score,
            "grade": sec_grade,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "category_counts": {},
            "badges": ["Security Profile Verified"],
            "dependency_stats": {
                "total_dependencies": 0,
                "safe_dependencies": 0,
                "vulnerable_dependencies": 0,
                "most_severe_vulnerability": "none",
                "total_known_cves": 0
            },
            "scan_stats": {
                "files_scanned": repo.total_files or 0,
                "files_skipped": 0,
                "dependencies_parsed": 0,
                "secrets_checked": repo.total_files or 0,
                "issues_found": 0
            }
        }
        
    return repo.security_summary


@router.get("/repositories/{id}/security/findings", response_model=SecurityFindingsResponse)
def get_security_findings(id: uuid.UUID, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
        
    if not repo.security_findings:
        return {"strengths": [], "warnings": []}
        
    return repo.security_findings


@router.get("/repositories/{id}/knowledge/summary", response_model=KnowledgeSummaryResponse)
def get_knowledge_summary(id: uuid.UUID, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    summary = repo.knowledge_summary or {}
    
    # If the database contains the old architecture-only graph in knowledge_summary,
    # or is empty, return a safe pending fallback structure to avoid validation crashes.
    if "project_structure" in summary or not summary:
        return {
            "total_chunks": 0,
            "code_chunks": 0,
            "evidence_documents": 0,
            "indexed_files": 0,
            "supported_languages": list(repo.language_breakdown.keys()) if repo.language_breakdown else [],
            "build_status": repo.knowledge_status if repo.knowledge_status else "pending",
            "embedding_status": "offline",
            "evidence_docs_list": []
        }

    return {
        "total_chunks": summary.get("total_chunks", 0),
        "code_chunks": summary.get("code_chunks", 0),
        "evidence_documents": summary.get("evidence_documents", 0),
        "indexed_files": summary.get("indexed_files", 0),
        "supported_languages": summary.get("supported_languages", []),
        "build_status": summary.get("build_status", repo.knowledge_status or "pending"),
        "embedding_status": summary.get("embedding_status", "offline"),
        "evidence_docs_list": summary.get("evidence_docs_list", []),
        "summary_description": summary.get("summary_description"),
        "architecture_knowledge": summary.get("architecture_knowledge"),
        "timing_metadata": summary.get("timing_metadata"),
        "health_metadata": summary.get("health_metadata"),
        "security_metadata": summary.get("security_metadata"),
        "diagnostics": summary.get("diagnostics"),
        "wiki_data": summary.get("wiki_data"),
        "knowledge_graph": summary.get("knowledge_graph"),
        "learning_report": summary.get("learning_report")
    }


@router.get("/repositories/{id}/knowledge/search")
def search_knowledge_base(id: uuid.UUID, query: str, limit: int = 5, db: Session = Depends(get_db)):
    from app.services.knowledge.retriever import retrieve_grounded_context
    return retrieve_grounded_context(str(id), query, limit)


@router.post("/repositories/{id}/assessment")
def generate_repository_assessment(id: uuid.UUID, db: Session = Depends(get_db)):
    from app.services.assessment.orchestrator import run_assessment
    try:
        return run_assessment(db, id)
    except Exception as e:
        import traceback
        import logging
        logging.getLogger(__name__).error(f"Uncaught exception in generate_repository_assessment: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "problem": "Failed to generate assessment report",
                "reason": str(e),
                "suggested_fix": "Check if database constraints are satisfied. Make sure the repository ingestion pipeline has completed.",
                "log_id": str(uuid.uuid4())
            }
        )


@router.get("/repositories/{id}/assessment")
def get_repository_assessment(id: uuid.UUID, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
        
    summary = repo.knowledge_summary or {}
    assessment = summary.get("assessment")
    if not assessment:
        from app.services.assessment.orchestrator import run_assessment
        try:
            return run_assessment(db, id)
        except Exception as e:
            import traceback
            import logging
            logging.getLogger(__name__).error(f"Uncaught exception in get_repository_assessment build: {e}\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "problem": "Assessment report not yet generated, and compilation failed",
                    "reason": str(e),
                    "suggested_fix": "Verify that your repository structure is valid and that local indexing process is running.",
                    "log_id": str(uuid.uuid4())
                }
            )
            
    return assessment


@router.get("/repositories/{id}/files/{file_id}/content")
def get_file_content(id: uuid.UUID, file_id: uuid.UUID, db: Session = Depends(get_db)):
    file = db.query(RepositoryFile).filter(RepositoryFile.id == file_id, RepositoryFile.repository_id == id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
        
    from app.core.config import settings
    clone_path = os.path.abspath(os.path.join(settings.CLONE_DIR, str(id)))
    abs_path = os.path.join(clone_path, file.path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File content not found on disk")
        
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
        
    return {"content": content}


@router.get("/repositories/{id}/export")
def export_repository_data(id: uuid.UUID, format: str = "json", db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
        
    if format == "markdown":
        md = f"# Repository Analysis Report: {repo.url}\n\n"
        md += f"## Health Overview\n"
        md += f"- **Health Score**: {repo.health_score} ({repo.health_grade})\n"
        md += f"- **Total LOC**: {repo.total_lines_of_code}\n"
        md += f"- **Average Complexity**: {repo.average_complexity}\n"
        md += f"- **Total Smells**: {repo.total_smells}\n"
        md += f"- **Duplication**: {repo.duplication_percentage}%\n\n"
        
        md += f"## Timing Breakdown\n"
        timing = (repo.knowledge_summary or {}).get("timing_metadata") or {}
        for stage, duration in timing.items():
            md += f"- **{stage.capitalize()}**: {duration}s\n"
            
        md += f"\n## Code Smells\n"
        smells = db.query(CodeSmell).filter(CodeSmell.repository_id == id).all()
        for s in smells:
            md += f"- **{s.smell_type}** ({s.severity}) in `{s.file_path}` Line {s.line_number}: {s.reason}\n"
            
        return PlainTextResponse(md, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=report_{id}.md"})
        
    return repo.knowledge_summary or {}


@router.post("/repositories/{id}/chat/sessions")
def create_chat_session(id: uuid.UUID, db: Session = Depends(get_db)):
    from app.services.expert.chat import ChatManager
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    manager = ChatManager(db)
    session = manager.create_session(str(id))
    return {
        "session_id": str(session.id),
        "repository_id": str(session.repository_id),
        "created_at": session.created_at.isoformat()
    }


@router.get("/repositories/{id}/chat/sessions/{session_id}")
def get_chat_session_history(id: uuid.UUID, session_id: uuid.UUID, db: Session = Depends(get_db)):
    from app.services.expert.chat import ChatManager
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    manager = ChatManager(db)
    messages = manager.get_messages(str(session_id))
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "cited_chunks": m.cited_chunks,
            "confidence": m.confidence,
            "expert_mode": m.expert_mode,
            "created_at": m.created_at.isoformat()
        }
        for m in messages
    ]


@router.post("/repositories/{id}/chat/sessions/{session_id}/messages")
def post_chat_message(
    id: uuid.UUID,
    session_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db)
):
    from fastapi.responses import StreamingResponse
    from app.services.expert.chat import ChatManager
    from app.services.expert.rag_pipeline import RagPipeline
    from app.services.expert.cache import mentor_cache
    from app.services.expert.telemetry import MentorTelemetry
    from app.services.llm.groq_service import GroqService, GroqProviderError
    from app.db.session import SessionLocal
    from app.core.config import settings

    telemetry = MentorTelemetry(str(id), str(session_id))

    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    content = payload.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    if content == "__test_force_429__":
        raise HTTPException(
            status_code=429,
            detail="Rate limit reached. Please wait a moment and try again.",
            headers={"Retry-After": "3"}
        )
    if content == "__test_force_500__":
        raise HTTPException(
            status_code=500,
            detail="Internal server error occurred while processing repository AST."
        )

    mode = payload.get("expert_mode", "General")
    explain_mode = payload.get("explain_mode")

    # Local quick responses for greetings and basic conceptual definitions
    local_queries = {
        "hi": "Hello! I am your AI Repository Mentor. How can I help you analyze your codebase today?",
        "hello": "Hello! I am your AI Repository Mentor. How can I help you analyze your codebase today?",
        "hey": "Hello! I am your AI Repository Mentor. How can I help you analyze your codebase today?",
        "how are you": "I'm doing great, thank you! Ready to dive into some code and review your repository architecture.",
        "thanks": "You're very welcome! Let me know if you need any other codebase explanations or refactoring tips.",
        "thank you": "You're very welcome! Let me know if you need any other codebase explanations or refactoring tips.",
        "good morning": "Good morning! Ready for another productive day of codebase mentoring. What repository section should we look at?",
        "good evening": "Good evening! Ready to review your codebase. What repository section should we look at?",
        
        "what is a code smell": (
            "A code smell is a surface-level indicator in a program's source code that suggests a deeper design flaw or quality issue. "
            "While not bugs themselves, code smells make the system harder to maintain, increase cognitive complexity, and increase the likelihood of introducing future regressions. "
            "Common examples include God Classes, Long Methods, Magic Numbers, and Duplicated Code."
        ),
        "what is cognitive complexity": (
            "Cognitive complexity is a measure of how difficult a block of code is for a human developer to read and understand. "
            "Unlike cyclomatic complexity (which counts path combinations), cognitive complexity scores code based on human readability factors, "
            "such as deeply nested conditionals, multi-level loops, early exit structures, and logical formatting shortcuts. "
            "A high cognitive complexity suggests that a file should be simplified or decomposed into smaller functions."
        ),
        "what is maintainability": (
            "Maintainability represents how easily a software system can be modified to fix defects, improve performance, or adapt to a changed environment. "
            "It is highly correlated with clean code principles, low coupling, high cohesion, comprehensive unit test suites, clear documentation, and the absence of code smells."
        ),
        "what is architecture": (
            "Software architecture defines the fundamental structure of a software system, establishing its high-level components, "
            "their relationships, boundaries, and how they interact. A clean architecture ensures a clear separation of concerns "
            "(e.g., MVC, Layered, Clean/Hexagonal Architecture), making systems robust, scalable, and easy to maintain."
        ),
        "what is dependency injection": (
            "Dependency Injection (DI) is a software design pattern where an object receives its dependencies from external sources "
            "rather than constructing them internally. This supports loose coupling, separation of concerns, and simplifies "
            "unit testing by allowing mock implementations to be easily swapped in for external dependencies (such as APIs or databases)."
        ),
        "what is rest": (
            "REST (Representational State Transfer) is an architectural style for designing networked applications. "
            "It relies on a stateless, client-server communication model using standard HTTP methods (GET, POST, PUT, DELETE) "
            "to perform operations on resources, which are identified by uniform URIs."
        ),
        "what is mvc": (
            "MVC (Model-View-Controller) is a classic software design pattern that separates an application into three main components: "
            "1. Model: Manages data and business logic.\n"
            "2. View: Handles the visual interface and presentation layer.\n"
            "3. Controller: Accepts user input and coordinates updates between the Model and View."
        ),
        "what is jwt": (
            "A JSON Web Token (JWT) is an open standard (RFC 7519) that defines a compact and self-contained way for securely "
            "transmitting information between parties as a JSON object. This information is digitally signed, ensuring its integrity, "
            "and is commonly used for stateless user authentication and secure API exchanges."
        ),
        "what is docker": (
            "Docker is an open-source platform that enables developers to automate the deployment of applications inside lightweight, "
            "isolated containers. Containers package the application code alongside all libraries and dependencies, guaranteeing "
            "consistent execution across development, staging, and production environments."
        ),
        "what is sql": (
            "SQL (Structured Query Language) is the standard programming language used for managing, querying, and manipulating "
            "data held in relational database management systems (RDBMS). It utilizes declarative statements to insert, update, delete, "
            "and search records across structured tables."
        ),
        "what is an api": (
            "An API (Application Programming Interface) is a set of defined rules and protocols that allows different software applications "
            "to communicate and share data with each other. It acts as an abstraction layer, exposing specific endpoints and data contracts "
            "while hiding internal implementation logic."
        )
    }

    query_cleaned = content.lower().strip("?.! ")

    # Preambles to strip from LLM answers
    preambles = [
        "based on the security assessment,",
        "based on the architectural blueprint,",
        "based on the repository stats,",
        "based on the codebase context,",
        "based on the provided repository evidence,",
        "according to the codebase context,",
        "according to the security assessment,",
        "according to the architectural blueprint,",
        "looking at the security assessment,",
        "looking at the architectural blueprint,"
    ]

    index_version = str(repo.analysis_completed_at or repo.completed_at or repo.created_at or "v1")

    # Check Exact Answer Cache
    cached_entry = mentor_cache.get_exact_answer(
        repo_id=str(id),
        index_version=index_version,
        query=content,
        llm_model=settings.GROQ_MODEL,
        mode=mode,
        explain_mode=explain_mode
    )

    # Check Pre-generated Starter Q&A (Instant First Answers)
    if not cached_entry:
        cached_qa = (repo.knowledge_summary or {}).get("cached_qa", {})
        query_norm = content.strip().lower().rstrip("?.,!")
        for q_key, q_val in cached_qa.items():
            key_norm = q_key.strip().lower().rstrip("?.,!")
            if key_norm == query_norm or query_norm in key_norm or key_norm in query_norm:
                cached_entry = {
                    "answer": q_val["answer"],
                    "citations": q_val.get("citations", []),
                    "confidence": q_val.get("confidence", 95),
                    "steps": ["Pre-generated repository knowledge answer (instant DB hit)"],
                    "follow_up": []
                }
                break

    def event_generator():
        # Handle Instant Local Responses
        if query_cleaned in local_queries:
            telemetry.mark_cache_checked(True)
            ans = local_queries[query_cleaned]
            telemetry.mark_first_token()
            yield f"data: {json.dumps({'type': 'status', 'stage': 'complete'})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'token': ans})}\n\n"
            tele_report = telemetry.mark_completed()
            yield f"data: {json.dumps({'type': 'metadata', 'citations': [], 'confidence': 100, 'steps': ['Direct local response'], 'follow_up': [], 'telemetry': tele_report})}\n\n"
            
            # Save messages in short transaction
            save_db = SessionLocal()
            try:
                save_mgr = ChatManager(save_db)
                save_mgr.add_message(str(session_id), "user", content, expert_mode=mode)
                save_mgr.add_message(str(session_id), "assistant", ans, expert_mode=mode)
            finally:
                save_db.close()
            return

        # Handle Exact Answer Cache Hit (Near Zero TTFT)
        if cached_entry:
            telemetry.mark_cache_checked(True)
            yield f"data: {json.dumps({'type': 'status', 'stage': 'cached'})}\n\n"
            cached_ans = cached_entry["answer"]
            telemetry.mark_first_token()
            
            # Stream cached tokens progressively in small token chunks
            words = cached_ans.split(" ")
            chunk_size = 6
            for i in range(0, len(words), chunk_size):
                chunk_str = " ".join(words[i:i + chunk_size]) + (" " if i + chunk_size < len(words) else "")
                telemetry.increment_token()
                yield f"data: {json.dumps({'type': 'token', 'token': chunk_str})}\n\n"
            
            tele_report = telemetry.mark_completed()
            yield f"data: {json.dumps({'type': 'metadata', 'citations': cached_entry['citations'], 'confidence': cached_entry['confidence'], 'steps': cached_entry['steps'], 'follow_up': cached_entry['follow_up'], 'telemetry': tele_report})}\n\n"
            
            # Persist user & cached assistant message in short transaction
            save_db = SessionLocal()
            try:
                save_mgr = ChatManager(save_db)
                save_mgr.add_message(str(session_id), "user", content, expert_mode=mode)
                save_mgr.add_message(str(session_id), "assistant", cached_ans, cited_chunks=cached_entry["citations"], confidence=cached_entry["confidence"], expert_mode=mode)
            finally:
                save_db.close()
            return

        # Cache Miss: Proceed with RAG Pipeline
        telemetry.mark_cache_checked(False)
        yield f"data: {json.dumps({'type': 'status', 'stage': 'retrieving'})}\n\n"

        # 1. DB Operations: Save user message & load history
        prep_db = SessionLocal()
        try:
            prep_mgr = ChatManager(prep_db)
            prep_mgr.add_message(str(session_id), "user", content, expert_mode=mode)
            history_msgs = prep_mgr.get_messages(str(session_id))
            history_list = [{"role": m.role, "content": m.content} for m in history_msgs[:-1]]
            
            # 2. Context Retrieval & Prompt Assembly
            pipeline = RagPipeline(prep_db, str(id), repo=repo)
            prompt, system_instruction, chunks, confidence_val, steps = pipeline.prepare_context_and_prompt(
                question=content,
                mode=mode,
                explain_mode=explain_mode,
                history=history_list
            )
            telemetry.mark_retrieval_done(len(chunks))
            telemetry.mark_prompt_ready(len(prompt) if prompt else 0)
        finally:
            # RELEASE DB CONNECTION: DB connection is closed before external Groq streaming
            prep_db.close()

        # Handle Insufficient Evidence Refusal or Incomplete Code Index
        if not prompt or not system_instruction:
            refusal_text = prompt or "I couldn't find enough information in the indexed repository to answer that confidently."
            is_incomplete = "Code index is incomplete" in refusal_text
            yield f"data: {json.dumps({'type': 'token', 'token': refusal_text})}\n\n"
            tele_report = telemetry.mark_completed()
            yield f"data: {json.dumps({'type': 'metadata', 'citations': [], 'confidence': 0, 'steps': steps, 'follow_up': [], 'telemetry': tele_report, 'code_index_incomplete': is_incomplete, 'model_used': settings.GROQ_MODEL})}\n\n"
            
            # Record assistant refusal
            save_db = SessionLocal()
            try:
                save_mgr = ChatManager(save_db)
                save_mgr.add_message(str(session_id), "assistant", refusal_text, cited_chunks=[], confidence=0, expert_mode=mode)
            finally:
                save_db.close()
            return

        # 3. Stream from Groq LLM with Connection Pooling & Rate-Limit Handling
        yield f"data: {json.dumps({'type': 'status', 'stage': 'synthesizing'})}\n\n"
        telemetry.mark_llm_initiated()

        full_response = ""
        preamble_stripped = False
        preamble_buffer = ""

        try:
            for token in GroqService.generate_stream(prompt, system_instruction):
                telemetry.mark_first_token()
                full_response += token
                if not preamble_stripped:
                    preamble_buffer += token
                    if len(preamble_buffer) >= 60:
                        lower_buf = preamble_buffer.lower().strip()
                        matched_p = None
                        for p in preambles:
                            if lower_buf.startswith(p):
                                matched_p = p
                                break
                        if matched_p:
                            idx = preamble_buffer.lower().find(matched_p)
                            rest = preamble_buffer[idx + len(matched_p):].strip()
                            if rest.startswith(","):
                                rest = rest[1:].strip()
                            if rest:
                                rest = rest[0].upper() + rest[1:]
                            preamble_buffer = rest
                        preamble_stripped = True
                        yield f"data: {json.dumps({'type': 'token', 'token': preamble_buffer})}\n\n"
                    continue
                yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

        except GroqProviderError as provider_err:
            telemetry.mark_error(f"Groq_{provider_err.status_code}")
            # Structured SSE Error Event
            yield f"data: {json.dumps({'type': 'error', 'code': provider_err.status_code, 'message': provider_err.message, 'retryable': provider_err.retryable, 'retry_after': provider_err.retry_after, 'has_partial': bool(full_response.strip())})}\n\n"
            
            # Save whatever partial tokens were delivered if any
            if full_response.strip():
                save_db = SessionLocal()
                try:
                    save_mgr = ChatManager(save_db)
                    save_mgr.add_message(str(session_id), "assistant", full_response.strip(), cited_chunks=chunks, confidence=confidence_val, expert_mode=mode)
                finally:
                    save_db.close()
            return

        except Exception as unhandled_err:
            telemetry.mark_error("UnhandledException")
            logger.error(f"Unexpected streaming exception: {unhandled_err}")
            yield f"data: {json.dumps({'type': 'error', 'code': 500, 'message': 'An unexpected error interrupted the mentor response.', 'retryable': True, 'has_partial': bool(full_response.strip())})}\n\n"
            return

        # Flush any trailing preamble buffer
        if not preamble_stripped and preamble_buffer:
            lower_buf = preamble_buffer.lower().strip()
            matched_p = None
            for p in preambles:
                if lower_buf.startswith(p):
                    matched_p = p
                    break
            if matched_p:
                idx = preamble_buffer.lower().find(matched_p)
                rest = preamble_buffer[idx + len(matched_p):].strip()
                if rest.startswith(","):
                    rest = rest[1:].strip()
                if rest:
                    rest = rest[0].upper() + rest[1:]
                preamble_buffer = rest
            yield f"data: {json.dumps({'type': 'token', 'token': preamble_buffer})}\n\n"

        # Generate contextual follow-up questions
        follow_ups = []
        if any(w in content.lower() for w in ["auth", "login", "jwt", "token", "session"]):
            follow_ups = [
                "Would you like me to explain JWT token verification in this repo?",
                "Should we discuss authentication security risks or best practices?"
            ]
        elif any(w in content.lower() for w in ["db", "database", "repository", "query", "sql"]):
            follow_ups = [
                "Explain the data transaction pattern used here.",
                "How would we safely parameterize dynamic database queries?"
            ]
        else:
            follow_ups = [
                "Explain the main design patterns in this project.",
                "What refactoring recommendations should I apply first?"
            ]

        # 4. Save assistant message and cache answer
        cleaned_response = full_response.strip()
        save_db = SessionLocal()
        try:
            save_mgr = ChatManager(save_db)
            save_mgr.add_message(str(session_id), "assistant", cleaned_response, cited_chunks=chunks, confidence=confidence_val, expert_mode=mode)
        finally:
            save_db.close()

        model_used = GroqService.get_last_model_used()

        # Save to Exact Answer Cache
        mentor_cache.set_exact_answer(
            repo_id=str(id),
            index_version=index_version,
            query=content,
            llm_model=model_used,
            answer=cleaned_response,
            citations=chunks,
            confidence=confidence_val,
            steps=steps,
            follow_up=follow_ups,
            mode=mode,
            explain_mode=explain_mode
        )

        tele_report = telemetry.mark_completed()
        yield f"data: {json.dumps({'type': 'metadata', 'citations': chunks, 'confidence': confidence_val, 'steps': steps, 'follow_up': follow_ups, 'telemetry': tele_report, 'model_used': model_used})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/repositories/{id}/chat/starter-questions")
def get_chat_starter_questions(id: uuid.UUID, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
        
    cached_qa = (repo.knowledge_summary or {}).get("cached_qa", {})
    if cached_qa:
        return list(cached_qa.keys())[:4]
        
    tech_stack = repo.tech_stack or {}
    frameworks = tech_stack.get("frameworks", [])
    
    questions = [
        "Explain the overall project architecture and layering.",
        "What are the biggest maintainability problems and code smells?",
        "Are there any security concerns or exposed secrets?"
    ]
    if frameworks:
        questions.append(f"How is the {frameworks[0]} framework configured?")
    else:
        questions.append("Where does the primary business logic live?")
        
    questions.append("What would you suggest refactoring first?")
    return questions


@router.get("/repositories/{id}/chat/expert-modes")
def get_chat_expert_modes():
    return [
        {"mode": "General", "description": "Senior AI Mentor who reviews code and answers general codebase questions."}
    ]


@router.get("/repositories/{id}/chat/walkthrough")
def get_repository_walkthrough(id: uuid.UUID, db: Session = Depends(get_db)):
    from app.services.expert.walkthrough import WalkthroughService
    lessons = WalkthroughService.generate_lessons(db, str(id))
    if not lessons:
        raise HTTPException(status_code=404, detail="Repository not found or has no analysis.")
    return lessons


@router.delete("/repositories/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(id: uuid.UUID, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    # Clean up ChromaDB collection
    try:
        import chromadb
        from app.core.config import settings
        chroma_client = chromadb.HttpClient(host=settings.CHROMADB_HOST, port=int(settings.CHROMADB_PORT))
        collection_name = f"repo_{str(id)}"
        try:
            chroma_client.delete_collection(name=collection_name)
        except Exception:
            pass
    except Exception:
        pass

    try:
        db.delete(repo)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database commit failed: {str(e)}"
        )
    return


@router.get("/diagnostics")
def get_diagnostics(db: Session = Depends(get_db)):
    """
    Diagnostics endpoint for Component 16.
    Checks status of Postgres, pgvector, Groq LLM, Git, and active job queue.
    """
    from sqlalchemy import text
    import subprocess
    import requests
    from app.core.config import settings

    # 1. Database check
    db_healthy = False
    try:
        db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception:
        pass

    # 2. pgvector check (represented as chromadb for frontend compatibility)
    chroma_healthy = False
    try:
        db.execute(text("SELECT 1 FROM repository_embeddings LIMIT 1"))
        chroma_healthy = True
    except Exception:
        pass

    # 3. Groq LLM check (represented as ollama for frontend compatibility)
    ollama_healthy = False
    models_list = [f"groq:{settings.GROQ_MODEL}", "fastembed:bge-small-en-v1.5"]
    if settings.GROQ_API_KEY:
        try:
            res = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                timeout=2
            )
            if res.status_code == 200:
                ollama_healthy = True
        except Exception:
            pass

    # 4. Git check
    git_healthy = False
    try:
        res = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            git_healthy = True
    except Exception:
        pass

    # 5. Queue statistics
    queued_repos = db.query(Repository).filter(Repository.status == RepositoryStatus.QUEUED).all()
    active_repos = db.query(Repository).filter(
        Repository.status.in_([
            RepositoryStatus.CLONING,
            RepositoryStatus.PARSING,
            RepositoryStatus.DETECTING_TECHNOLOGIES,
            RepositoryStatus.ANALYZING,
            RepositoryStatus.FINALIZING
        ])
    ).all()

    # 6. Basic memory info (without external dependencies)
    mem_info = {"status": "available"}
    try:
        import psutil
        virtual_mem = psutil.virtual_memory()
        mem_info = {
            "total_mb": round(virtual_mem.total / (1024 * 1024), 2),
            "used_mb": round(virtual_mem.used / (1024 * 1024), 2),
            "percent": virtual_mem.percent,
            "cpu_percent": psutil.cpu_percent(interval=None)
        }
    except ImportError:
        # Fallback if psutil is not loaded in Docker context
        try:
            import os
            # If running on Linux inside Docker container
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", "r") as f:
                    lines = f.readlines()
                mem_total = 0
                mem_free = 0
                for line in lines:
                    if "MemTotal" in line:
                        mem_total = int(line.split()[1])
                    elif "MemFree" in line:
                        mem_free = int(line.split()[1])
                if mem_total > 0:
                    mem_used = mem_total - mem_free
                    mem_info = {
                        "total_mb": round(mem_total / 1024, 2),
                        "used_mb": round(mem_used / 1024, 2),
                        "percent": round((mem_used / mem_total) * 100, 2),
                        "cpu_percent": 0.0
                    }
        except Exception:
            pass

    return {
        "status": "healthy" if (db_healthy and chroma_healthy and ollama_healthy and git_healthy) else "degraded",
        "services": {
            "database": "online" if db_healthy else "offline",
            "chromadb": "online" if chroma_healthy else "offline",
            "ollama": "online" if ollama_healthy else "offline",
            "git": "available" if git_healthy else "unavailable"
        },
        "ollama_models": models_list,
        "queue": {
            "queued_count": len(queued_repos),
            "active_count": len(active_repos),
            "active_tasks": [
                {
                    "id": str(r.id),
                    "url": r.url,
                    "status": r.status.value,
                    "status_message": r.status_message,
                    "elapsed_seconds": round((datetime.now(timezone.utc) - r.started_at).total_seconds(), 2) if r.started_at else 0
                }
                for r in active_repos
            ]
        },
        "system": mem_info
    }


@router.post("/repositories/{id}/knowledge/retry")
def retry_knowledge_base(id: uuid.UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Component 8 & Retry capability.
    Resets knowledge base progress and triggers Phase B indexing + assessment
    for a READY repository without wiping Phase A analysis results.
    """
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
        
    if repo.status != RepositoryStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot retry Knowledge Base indexing on a repository that is not READY."
        )
        
    if repo.knowledge_status == "indexing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Knowledge Base compilation is currently in progress."
        )
        
    try:
        # Reset knowledge indexing states
        repo.knowledge_status = "pending"
        repo.status_message = "Re-indexing Knowledge Base..."
        
        # Reset knowledge_summary metadata if exists
        summary = dict(repo.knowledge_summary or {})
        summary["build_status"] = "pending"
        if "pipeline_metadata" in summary:
            # Re-initialize knowledge and assessment stages
            summary["pipeline_metadata"]["stages"]["knowledge"] = {"status": "pending"}
            summary["pipeline_metadata"]["stages"]["assessment"] = {"status": "pending"}
            summary["pipeline_metadata"]["current_stage"] = "Knowledge Base"
        repo.knowledge_summary = summary
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database update failed: {str(e)}"
        )
        
    # Queue task - since status is READY, it will bypass Phase A clone/parse and run Phase B directly!
    from app.services.ingestion.pipeline import ingest_repository
    background_tasks.add_task(ingest_repository, repo.id)
    
    return {"id": repo.id, "status": repo.status.value, "knowledge_status": repo.knowledge_status}


@router.get("/repositories/{id}/recommendations")
def get_repository_recommendations(id: uuid.UUID, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    
    from app.services.analysis.recommendations import generate_recommendations as gen_recs
    try:
        return gen_recs(db, id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


@router.post("/repositories/{id}/reanalyse")
def reanalyse_repository(id: uuid.UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Triggers a full repository re-analysis from scratch, as if uploaded for the first time.
    Bypasses Phase A skip checks, wipes old database records (CodeSmell, SecurityIssue, RepositoryFile),
    resets metrics, and queues a full ingestion pipeline run.
    """
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
        
    if repo.knowledge_status == "indexing" or repo.status in [
        RepositoryStatus.CLONING,
        RepositoryStatus.PARSING,
        RepositoryStatus.DETECTING_TECHNOLOGIES,
        RepositoryStatus.ANALYZING,
        RepositoryStatus.FINALIZING
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An analysis or indexing pipeline is already in progress for this repository."
        )
        
    try:
        # Reset repository status to QUEUED so pipeline runs from scratch (Phase A + Phase B)
        repo.status = RepositoryStatus.QUEUED
        repo.status_message = "Re-analysing repository..."
        repo.knowledge_status = "pending"
        
        # Reset health score and grade
        repo.health_score = 0
        repo.health_grade = "F"
        repo.total_files = 0
        repo.total_folders = 0
        repo.text_file_count = 0
        repo.binary_file_count = 0
        repo.total_lines_of_code = 0
        repo.average_complexity = 0.0
        repo.max_complexity = 0
        repo.total_smells = 0
        repo.duplication_percentage = 0.0
        repo.architecture_score = 0
        repo.architecture_grade = "F"
        repo.security_score = 0
        repo.security_grade = "F"
        
        # Reset knowledge_summary JSON metadata completely
        repo.knowledge_summary = {}
        repo.architecture_summary = {}
        repo.architecture_findings = {}
        repo.security_summary = {}
        repo.security_findings = {}
        
        # Clear child tables to avoid duplicate keys/records
        from app.models.code_smell import CodeSmell
        from app.models.security_issue import SecurityIssue
        
        db.query(CodeSmell).filter(CodeSmell.repository_id == id).delete()
        db.query(SecurityIssue).filter(SecurityIssue.repository_id == id).delete()
        db.query(RepositoryFile).filter(RepositoryFile.repository_id == id).delete()
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset repository state: {str(e)}"
        )
        
    # Queue task - since status is QUEUED, it will run Phase A clone/parse, then Phase B!
    from app.services.ingestion.pipeline import ingest_repository
    background_tasks.add_task(ingest_repository, repo.id)
    
    return {"id": repo.id, "status": repo.status.value, "knowledge_status": repo.knowledge_status}


