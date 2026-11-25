import logging
import json
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.code_smell import CodeSmell
from app.models.security_issue import SecurityIssue

logger = logging.getLogger(__name__)

def build_repo_fact_sheet(repo: Repository, db: Session) -> str:
    """
    Builds a compact, high-density repository fact sheet from Phase A deterministic metrics.
    Budget: Strictly under 600 tokens (~2400 chars).
    """
    repo_id = repo.id
    repo_name = repo.url.rstrip("/").split("/")[-1] if repo.url else "Repository"

    # 1. Smells breakdown by type
    smell_counts = db.query(CodeSmell.smell_type, func.count(CodeSmell.id))\
        .filter(CodeSmell.repository_id == repo_id)\
        .group_by(CodeSmell.smell_type)\
        .order_by(func.count(CodeSmell.id).desc())\
        .limit(6).all()

    # 2. Top 10 files by smells
    top_smell_files = db.query(CodeSmell.file_path, func.count(CodeSmell.id))\
        .filter(CodeSmell.repository_id == repo_id)\
        .group_by(CodeSmell.file_path)\
        .order_by(func.count(CodeSmell.id).desc())\
        .limit(10).all()

    # 3. Most coupled files (bottlenecks)
    coupled_files = db.query(RepositoryFile.path, RepositoryFile.coupling_score)\
        .filter(RepositoryFile.repository_id == repo_id, RepositoryFile.coupling_score > 0)\
        .order_by(RepositoryFile.coupling_score.desc())\
        .limit(5).all()

    # 4. Security vulnerability counts by severity
    sec_counts = db.query(SecurityIssue.severity, func.count(SecurityIssue.id))\
        .filter(SecurityIssue.repository_id == repo_id)\
        .group_by(SecurityIssue.severity).all()
    sec_map = {s: c for s, c in sec_counts}

    # 5. Key vulnerability titles
    sec_titles = db.query(SecurityIssue.severity, SecurityIssue.title, SecurityIssue.file_path)\
        .filter(SecurityIssue.repository_id == repo_id)\
        .order_by(SecurityIssue.severity.asc())\
        .limit(5).all()

    arch = repo.architecture_summary or {}
    dup_details = arch.get("duplicate_files_details") or []
    dup_count = arch.get("duplicate_files_count", 0)

    # If duplicate info not in arch summary, check RepositoryFile content hashes
    if dup_count == 0:
        hash_counts = db.query(RepositoryFile.content_hash, func.count(RepositoryFile.id))\
            .filter(RepositoryFile.repository_id == repo_id, RepositoryFile.is_text == True)\
            .group_by(RepositoryFile.content_hash)\
            .having(func.count(RepositoryFile.id) > 1).all()
        dup_count = sum(c - 1 for h, c in hash_counts if h and not h.startswith("empty_"))

    entry_points_val = arch.get('entry_points', 0)
    # If entry_points was erroneously set to all un-imported files (>30), query true entry points
    if isinstance(entry_points_val, int) and entry_points_val > 30:
        from app.services.analysis.pipeline import is_entry_point
        repo_file_paths = [r[0] for r in db.query(RepositoryFile.path).filter(RepositoryFile.repository_id == repo_id, RepositoryFile.is_text == True).all()]
        true_entries = [p for p in repo_file_paths if is_entry_point(p)]
        entry_points_val = len(true_entries)

    sheet = []
    sheet.append(f"--- Repository Fact Sheet: {repo_name} ---")
    
    # A3: Not analysed is not clean (LOC 0 handling)
    if (repo.total_lines_of_code or 0) == 0:
        sheet.append(f"Health Rating: Not enough analysable code | Total LOC: 0 | Modules: {repo.total_files}")
        sheet.append("Status: Not analysed: notebook cells are not scanned")
    else:
        sheet.append(f"Health Rating: {repo.health_score}/100 (Grade {repo.health_grade}) | Total LOC: {repo.total_lines_of_code:,} | Modules: {repo.total_files}")
        
    sheet.append(f"Language Breakdown: {json.dumps(repo.language_breakdown or {})}")
    sheet.append(f"Architecture: Pattern={arch.get('pattern', 'Modular')}, True Entry Points={entry_points_val}")
    
    # A2: Option A duplicate files finding
    if dup_count > 0:
        dup_summary = f"{dup_count} duplicate files detected"
        if dup_details:
            dup_summary += f" ({', '.join(dup_details[:2])})"
        sheet.append(f"Code Duplication: {repo.duplication_percentage}% | {dup_summary} (analyzed once under Option A policy)")
    else:
        sheet.append(f"Code Duplication: {repo.duplication_percentage}% (Duplicate folders: None)")
    
    if smell_counts:
        sheet.append("Top Code Smells: " + ", ".join(f"{st}: {c}" for st, c in smell_counts))
    else:
        sheet.append("Top Code Smells: None detected")

    if top_smell_files:
        sheet.append("Top Files by Smells: " + ", ".join(f"{fp.split('/')[-1]} ({c})" for fp, c in top_smell_files))
    else:
        sheet.append("Top Files by Smells: None")

    if coupled_files:
        sheet.append("Most Coupled Files: " + ", ".join(f"{fp.split('/')[-1]} (coupling {cs})" for fp, cs in coupled_files))
    else:
        sheet.append("Most Coupled Files: None")

    sheet.append(f"Security Vulnerabilities: Critical={sec_map.get('Critical', 0)}, High={sec_map.get('High', 0)}, Medium={sec_map.get('Medium', 0)}, Low={sec_map.get('Low', 0)}")
    if sec_titles:
        sheet.append("Key Vulnerabilities: " + "; ".join(f"[{s}] {t} in {fp.split('/')[-1]}" for s, t, fp in sec_titles))

    return "\n".join(sheet)
