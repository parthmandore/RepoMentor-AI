import os
import time
import shutil
import uuid
import logging
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.repository import Repository, RepositoryStatus
from app.models.repository_file import RepositoryFile
from app.core.config import settings
from app.services.ingestion.cloner import clone_repository, IngestionError
from app.services.ingestion.parser import parse_repository
from app.services.ingestion.tech_detector import detect_technologies

logger = logging.getLogger(__name__)


def update_pipeline_progress(db, repo, pipeline_id: str, stage_name: str, stage_status: str, duration: float = None, warning: str = None):
    """
    Updates the rich pipeline stage-level progress metadata inside repo.knowledge_summary JSON.
    """
    summary = dict(repo.knowledge_summary or {})
    meta = summary.get("pipeline_metadata", {
        "pipeline_id": pipeline_id,
        "current_stage": stage_name,
        "stages": {
            "clone": {"status": "pending"},
            "parse": {"status": "pending"},
            "tech_detect": {"status": "pending"},
            "metrics": {"status": "pending"},
            "architecture": {"status": "pending"},
            "security": {"status": "pending"},
            "knowledge": {"status": "pending"},
            "assessment": {"status": "pending"}
        },
        "warnings": []
    })
    
    meta["current_stage"] = stage_name
    if stage_name in meta["stages"]:
        meta["stages"][stage_name]["status"] = stage_status
        if duration is not None:
            meta["stages"][stage_name]["duration"] = round(duration, 2)
            
    if warning:
        if "warnings" not in meta:
            meta["warnings"] = []
        meta["warnings"].append(warning)
        
    summary["pipeline_metadata"] = meta
    repo.knowledge_summary = summary
    db.commit()


def calculate_health_score_from_db(db, repo_id: uuid.UUID, repo) -> tuple[int, str, dict]:
    """
    Helper to run deterministic health scoring calculations from DB state (Phase A metrics).
    """
    from app.services.analysis.scoring import calculate_weighted_health_score, calculate_grade
    from app.models.code_smell import CodeSmell
    from app.models.security_issue import SecurityIssue

    db_files = db.query(RepositoryFile).filter(RepositoryFile.repository_id == repo_id).all()
    db_smells = db.query(CodeSmell).filter(CodeSmell.repository_id == repo_id).all()
    db_sec = db.query(SecurityIssue).filter(SecurityIssue.repository_id == repo_id).all()

    # 1. Security counts
    sec_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for s in db_sec:
        sec_counts[s.severity] = sec_counts.get(s.severity, 0) + 1

    # 2. Cycle count
    arch_summary = repo.architecture_summary or {}
    cycle_count = len(arch_summary.get("circular_dependencies", []))

    # 3. Coupling count
    highly_coupled_count = sum(1 for f in db_files if f.coupling_score > 8)

    # 4. Average comment ratio
    comment_ratios = []
    for f in db_files:
        if f.analysis_metadata and "metrics" in f.analysis_metadata:
            comment_ratios.append(f.analysis_metadata["metrics"].get("comment_ratio", 0.0))
    avg_comment_ratio = sum(comment_ratios) / len(comment_ratios) if comment_ratios else 0.0

    # 5. Calculate
    health_data = calculate_weighted_health_score(
        average_complexity=repo.average_complexity,
        total_smells=repo.total_smells,
        security_counts=sec_counts,
        cycle_count=cycle_count,
        highly_coupled_count=highly_coupled_count,
        comment_ratio=avg_comment_ratio,
        duplication_percentage=repo.duplication_percentage
    )

    final_score = health_data["final_score"]
    grade = calculate_grade(final_score)
    return final_score, grade, health_data


def run_phase_b(db, repo, repo_id: uuid.UUID, clone_path: str, pipeline_id: str, file_contents: dict = None) -> None:
    """
    Executes Phase B (Knowledge Base indexing + Assessment generation) sequentially in the background.
    """
    # 6. KNOWLEDGE BASE INDEXING (Component 1 Stage B)
    t_kb_start = time.perf_counter()
    logger.info(f"[Pipeline {pipeline_id}] START Knowledge Base Indexing")
    update_pipeline_progress(db, repo, pipeline_id, "knowledge", "running")
    
    try:
        from app.services.knowledge.pipeline import build_knowledge_base
        build_knowledge_base(repo_id, clone_path, file_contents)
        
        t_kb = time.perf_counter() - t_kb_start
        logger.info(f"[Pipeline {pipeline_id}] END Knowledge Base Indexing ({t_kb:.2f}s)")
        db.expire(repo, ['knowledge_summary'])
        db.refresh(repo)
        update_pipeline_progress(db, repo, pipeline_id, "knowledge", "completed", t_kb)
    except Exception as kb_err:
        t_kb = time.perf_counter() - t_kb_start
        logger.error(f"[Pipeline {pipeline_id}] FAILED Knowledge Base Indexing: {kb_err}", exc_info=True)
        update_pipeline_progress(db, repo, pipeline_id, "knowledge", "failed", t_kb, f"Knowledge base failed: {str(kb_err)}")
        try:
            db.refresh(repo)
            repo.knowledge_status = "failed"
            db.commit()
        except Exception:
            db.rollback()

    # 7. ASSESSMENT GENERATION (Component 1 Stage B)
    t_assess_start = time.perf_counter()
    logger.info(f"[Pipeline {pipeline_id}] START Assessment Compilation")
    update_pipeline_progress(db, repo, pipeline_id, "assessment", "running")
    
    try:
        from app.services.assessment.orchestrator import run_assessment
        run_assessment(db, repo_id)
        
        t_assess = time.perf_counter() - t_assess_start
        logger.info(f"[Pipeline {pipeline_id}] END Assessment Compilation ({t_assess:.2f}s)")
        db.expire(repo, ['knowledge_summary'])
        db.refresh(repo)
        update_pipeline_progress(db, repo, pipeline_id, "assessment", "completed", t_assess)
    except Exception as assess_err:
        t_assess = time.perf_counter() - t_assess_start
        logger.error(f"[Pipeline {pipeline_id}] FAILED Assessment Compilation: {assess_err}", exc_info=True)
        update_pipeline_progress(db, repo, pipeline_id, "assessment", "failed", t_assess, f"Assessment failed: {str(assess_err)}")

    # Clean up local clone files to preserve disk space (Component 14)
    if os.path.exists(clone_path):
        shutil.rmtree(clone_path, ignore_errors=True)
    
    try:
        db.refresh(repo)
        repo.status_message = "Ready"
        db.commit()
    except Exception as final_err:
        logger.warning(f"Failed to set final status message: {final_err}")
        
    db.close()


def ingest_repository(repo_id: uuid.UUID) -> None:
    """
    Orchestrated pipeline to ingest a repository.
    Phase A: Clone, Parse, Tech Detection, Metrics, Architecture, Security -> READY.
    Phase B: Knowledge Base Indexing, Assessment Generation -> Finished.
    """
    db = SessionLocal()

    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        logger.error(f"Repository {repo_id} not found in database.")
        db.close()
        return

    # Component 6 Lock: Prevent duplicate running ingestion jobs
    if repo.status in [RepositoryStatus.CLONING, RepositoryStatus.PARSING, RepositoryStatus.DETECTING_TECHNOLOGIES, RepositoryStatus.ANALYZING, RepositoryStatus.FINALIZING]:
        logger.warning(f"Ingestion job already running for repository {repo_id}. Skipping duplicate job.")
        db.close()
        return

    # Generate a unique pipeline ID for log grouping (Component 8)
    pipeline_id = str(uuid.uuid4())[:6]
    logger.info(f"[Pipeline {pipeline_id}] Starting ingestion run for repository {repo_id} ({repo.url})")

    # Fetch remote HEAD commit hash via git ls-remote for caching check
    import subprocess
    import re
    
    remote_hash = None
    try:
        res = subprocess.run(
            ["git", "ls-remote", repo.url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        )
        if res.returncode == 0 and res.stdout:
            match = re.match(r"^([a-fA-F0-9]{40})", res.stdout.strip())
            if match:
                remote_hash = match.group(1)
    except Exception as e:
        logger.warning(f"Failed to fetch remote HEAD commit hash via git ls-remote: {e}")

    # Check cache hit (commit hash matches and database is ready)
    if remote_hash:
        summary = dict(repo.knowledge_summary or {})
        prev_hash = summary.get("last_commit_hash")
        if prev_hash == remote_hash and repo.status == RepositoryStatus.READY and repo.knowledge_status == "completed":
            logger.info(f"[Pipeline {pipeline_id}] Cache Hit! Commit {remote_hash} already fully indexed. Instantly unlocking.")
            
            timing = summary.get("timing_metadata", {})
            timing["cache_hit"] = True
            summary["timing_metadata"] = timing
            repo.knowledge_summary = summary
            repo.status_message = "Ready"
            db.commit()
            
            # Instantly complete all pipeline progress stages
            update_pipeline_progress(db, repo, pipeline_id, "clone", "completed", 0.0)
            update_pipeline_progress(db, repo, pipeline_id, "parse", "completed", 0.0)
            update_pipeline_progress(db, repo, pipeline_id, "tech_detect", "completed", 0.0)
            update_pipeline_progress(db, repo, pipeline_id, "metrics", "completed", 0.0)
            update_pipeline_progress(db, repo, pipeline_id, "architecture", "completed", 0.0)
            update_pipeline_progress(db, repo, pipeline_id, "security", "completed", 0.0)
            update_pipeline_progress(db, repo, pipeline_id, "knowledge", "completed", 0.0)
            update_pipeline_progress(db, repo, pipeline_id, "assessment", "completed", 0.0)
            db.close()
            return

    started_at = datetime.now(timezone.utc)
    clone_path = os.path.abspath(os.path.join(settings.CLONE_DIR, str(repo_id)))

    # ==============================================================
    # PHASE A BYPASS CHECK (For retrying Phase B only)
    # ==============================================================
    if repo.status == RepositoryStatus.READY:
        logger.info(f"[Pipeline {pipeline_id}] Repository {repo_id} is already READY. Skipping Phase A. Running Phase B directly.")
        # Re-clone temporarily to read text file contents for embedding generation
        try:
            # Recreate clone directory if pre-existing
            if os.path.exists(clone_path):
                shutil.rmtree(clone_path, ignore_errors=True)
            
            clone_repository(repo.url, clone_path)
            # Re-run fast parser to populate file_contents dictionary in-memory
            _, _, file_contents = parse_repository(clone_path)
            
            update_pipeline_progress(db, repo, pipeline_id, "clone", "completed", 0.0)
            update_pipeline_progress(db, repo, pipeline_id, "parse", "completed", 0.0)
            update_pipeline_progress(db, repo, pipeline_id, "tech_detect", "completed", 0.0)
            update_pipeline_progress(db, repo, pipeline_id, "metrics", "completed", 0.0)
            update_pipeline_progress(db, repo, pipeline_id, "architecture", "completed", 0.0)
            update_pipeline_progress(db, repo, pipeline_id, "security", "completed", 0.0)
        except Exception as clone_err:
            logger.error(f"[Pipeline {pipeline_id}] Re-clone for Phase B failed: {clone_err}")
            update_pipeline_progress(db, repo, pipeline_id, "knowledge", "failed", 0.0, f"Temporary clone failed: {str(clone_err)}")
            try:
                db.refresh(repo)
                repo.knowledge_status = "failed"
                db.commit()
            except Exception:
                db.rollback()
            db.close()
            return
            
        repo.status_message = "Generating Knowledge"
        db.commit()
        # Jump directly to Phase B execution
        run_phase_b(db, repo, repo_id, clone_path, pipeline_id, file_contents)
        return

    # Normal execution - Initialize progress metadata and run Phase A
    update_pipeline_progress(db, repo, pipeline_id, "clone", "running")
    phase_a_success = True
    t_phase_a_start = time.perf_counter()

    # 1. CLONING (STOP on failure)
    t_clone_start = time.perf_counter()
    logger.info(f"[Pipeline {pipeline_id}] START Clone")
    try:
        repo.status = RepositoryStatus.CLONING
        repo.status_message = "Cloning repository..."
        repo.started_at = started_at
        repo.error_message = None
        db.commit()

        clone_repository(repo.url, clone_path)
        t_clone = time.perf_counter() - t_clone_start
        logger.info(f"[Pipeline {pipeline_id}] END Clone ({t_clone:.2f}s)")
        
        # Ingestion complete, set status message to "Repository Cloned"
        repo.status_message = "Repository Cloned"
        db.commit()
        
        update_pipeline_progress(db, repo, pipeline_id, "clone", "completed", t_clone)
    except Exception as e:
        phase_a_success = False
        t_clone = time.perf_counter() - t_clone_start
        logger.error(f"[Pipeline {pipeline_id}] FAILED Clone: {str(e)}", exc_info=True)
        update_pipeline_progress(db, repo, pipeline_id, "clone", "failed", t_clone, f"Clone failed: {str(e)}")
        handle_phase_a_failure(db, repo, clone_path, started_at, e)
        return

    # 2. PARSING & TECH DETECTION (STOP on failure)
    t_parse_start = time.perf_counter()
    logger.info(f"[Pipeline {pipeline_id}] START Parsing")
    try:
        update_pipeline_progress(db, repo, pipeline_id, "parse", "running")

        # parser now returns files_metadata, stats, and in-memory file_contents
        files_metadata, stats, file_contents = parse_repository(clone_path)

        # Clear existing file records
        db.query(RepositoryFile).filter(RepositoryFile.repository_id == repo_id).delete()
        
        # Optimize database writes by using bulk_insert_mappings
        mappings = [
            {
                "id": uuid.uuid4(),
                "repository_id": repo_id,
                "path": f["path"],
                "extension": f["extension"],
                "size_bytes": f["size_bytes"],
                "content_hash": f["content_hash"],
                "is_text": f["is_text"]
            }
            for f in files_metadata
        ]
        db.bulk_insert_mappings(RepositoryFile, mappings)
        db.commit()
        
        # Immediately clear mappings list to release memory
        mappings.clear()
        del mappings

        t_parse = time.perf_counter() - t_parse_start
        logger.info(f"[Pipeline {pipeline_id}] END Parsing ({t_parse:.2f}s)")
        update_pipeline_progress(db, repo, pipeline_id, "parse", "completed", t_parse)
    except Exception as e:
        phase_a_success = False
        t_parse = time.perf_counter() - t_parse_start
        logger.error(f"[Pipeline {pipeline_id}] FAILED Parsing: {str(e)}", exc_info=True)
        update_pipeline_progress(db, repo, pipeline_id, "parse", "failed", t_parse, f"Parsing failed: {str(e)}")
        handle_phase_a_failure(db, repo, clone_path, started_at, e)
        return

    # 2b. TECHNOLOGY DETECTION (STOP on failure)
    t_tech_start = time.perf_counter()
    logger.info(f"[Pipeline {pipeline_id}] START Technology Detection")
    try:
        update_pipeline_progress(db, repo, pipeline_id, "tech_detect", "running")
        tech = detect_technologies(clone_path, files_metadata)

        # Update stats
        repo.total_files = stats["total_files"]
        repo.total_folders = stats["total_folders"]
        repo.text_file_count = stats["text_file_count"]
        repo.binary_file_count = stats["binary_file_count"]
        repo.language_breakdown = tech["languages"]
        repo.tech_stack = {
            "frameworks": tech["frameworks"],
            "package_manager": tech["package_manager"]
        }
        db.commit()

        t_tech = time.perf_counter() - t_tech_start
        logger.info(f"[Pipeline {pipeline_id}] END Technology Detection ({t_tech:.2f}s)")
        update_pipeline_progress(db, repo, pipeline_id, "tech_detect", "completed", t_tech)
    except Exception as e:
        phase_a_success = False
        t_tech = time.perf_counter() - t_tech_start
        logger.error(f"[Pipeline {pipeline_id}] FAILED Tech Detection: {str(e)}", exc_info=True)
        update_pipeline_progress(db, repo, pipeline_id, "tech_detect", "failed", t_tech, f"Tech detection failed: {str(e)}")
        handle_phase_a_failure(db, repo, clone_path, started_at, e)
        return

    # 3. MERGED SCANNERS EXECUTION
    logger.info(f"[Pipeline {pipeline_id}] START Merged Codebase Scanners")
    t_parallel_start = time.perf_counter()
    
    repo.status = RepositoryStatus.ANALYZING
    repo.status_message = "Analyzing Repository"
    db.commit()
    
    update_pipeline_progress(db, repo, pipeline_id, "metrics", "running")
    update_pipeline_progress(db, repo, pipeline_id, "architecture", "running")
    update_pipeline_progress(db, repo, pipeline_id, "security", "running")

    # Run merged scans directly on main thread context
    from app.services.analysis.pipeline import analyze_repository
    
    err_scan = None
    try:
        analyze_repository(repo_id, clone_path, file_contents)
        status_scan = "completed"
    except Exception as scan_err:
        logger.error(f"[Pipeline {pipeline_id}] Merged Scanners Failed: {scan_err}", exc_info=True)
        status_scan = "failed"
        err_scan = f"Scanner failed: {str(scan_err)}"

    t_parallel = time.perf_counter() - t_parallel_start
    logger.info(f"[Pipeline {pipeline_id}] END Merged Codebase Scanners ({t_parallel:.2f}s)")

    # Retrieve fresh repo model instance
    db.refresh(repo)
    update_pipeline_progress(db, repo, pipeline_id, "metrics", status_scan, t_parallel, err_scan)
    update_pipeline_progress(db, repo, pipeline_id, "architecture", status_scan, 0.0)
    update_pipeline_progress(db, repo, pipeline_id, "security", status_scan, 0.0)

    if status_scan == "failed":
        handle_phase_a_failure(db, repo, clone_path, started_at, Exception(err_scan))
        return

    # ==============================================================
    # FINALIZING PHASE A: Set Repository to READY
    # ==============================================================
    t_phase_a = time.perf_counter() - t_phase_a_start
    completed_at = datetime.now(timezone.utc)
    
    try:
        # Calculate grade & health score from DB metrics immediately
        health_score, grade, health_meta = calculate_health_score_from_db(db, repo_id, repo)
        repo.health_score = health_score
        repo.health_grade = grade

        summary = repo.knowledge_summary or {}
        summary["health_metadata"] = health_meta
        summary["timing_metadata"] = {
            "clone": round(t_clone, 2),
            "parsing": round(t_parse + t_tech, 2),
            "metrics": round(t_parallel, 2),
            "architecture": 0.0,
            "security": 0.0,
            "total_phase_a": round(t_phase_a, 2),
            "cache_hit": False
        }
        repo.knowledge_summary = summary
        
        repo.status = RepositoryStatus.READY
        repo.status_message = "Generating Knowledge"
        repo.completed_at = completed_at
        repo.duration_seconds = round(t_phase_a, 2)
        db.commit()
        logger.info(f"[Pipeline {pipeline_id}] Phase A completed successfully in {t_phase_a:.2f}s. Repository {repo_id} set to READY.")
    except Exception as db_err:
        logger.critical(f"[Pipeline {pipeline_id}] Failed to save READY status: {db_err}")
        db.rollback()
        handle_phase_a_failure(db, repo, clone_path, started_at, db_err)
        return

    # Trigger Phase B sequentially
    run_phase_b(db, repo, repo_id, clone_path, pipeline_id, file_contents)


def handle_phase_a_failure(db, repo, clone_path: str, started_at: datetime, error: Exception):
    """Refactored fail-safe cleanup and update for Phase A stop failures."""
    if os.path.exists(clone_path):
        shutil.rmtree(clone_path, ignore_errors=True)

    try:
        db.rollback()
    except Exception:
        pass

    try:
        completed_at = datetime.now(timezone.utc)
        duration = (completed_at - started_at).total_seconds()
        repo.status = RepositoryStatus.FAILED
        repo.status_message = "Ingestion failed"
        repo.completed_at = completed_at
        repo.duration_seconds = round(duration, 2)
        repo.error_message = str(error)
        db.commit()
    except Exception as db_err:
        logger.critical(f"Failed to update repository FAILED status: {db_err}")
    finally:
        db.close()
