import os
import uuid
import logging
import time
from typing import Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.security_issue import SecurityIssue
from app.models.code_smell import CodeSmell
from app.services.knowledge.evidence_builder import build_evidence_documents
from app.services.knowledge.chunker import chunk_repository, select_best_chunks
from app.services.knowledge.embedder import verify_embeddings_status, generate_embeddings, EmbeddingGenerationError
from app.repositories.vector_repository import VectorRepository

logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class FileSnapshot:
    id: uuid.UUID
    path: str
    extension: str | None
    is_text: bool
    content_hash: str
    size_bytes: int
    lines_of_code: int
    complexity: float | None
    code_smells_count: int
    module_type: str | None
    coupling_score: float | None
    analysis_metadata: dict

def log_info(msg: str):
    """Bulletproof logger helper to write to both python logging and standard output."""
    logger.info(msg)
    print(msg, flush=True)

def build_knowledge_base(repo_id: uuid.UUID, clone_path: str, file_contents: dict = None) -> None:
    db = SessionLocal()
    
    # Initialize metrics for final diagnostic summary
    files_processed = 0
    chunks_generated = 0
    t_embed_duration = 0.0
    t_vector_db_duration = 0.0
    total_duration = 0.0
    embedding_requests = 0
    vector_db_insert_count = 0
    failure_stage = "None"
    failure_reason = "None"
    total_chunk_chars = 0
    max_chunk_char = 0
    
    t_kb_start = time.perf_counter()
    t_kb_loop_start = time.time()
    timeout_seconds = getattr(settings, "KNOWLEDGE_TIMEOUT_SECONDS", 300)
    
    try:
        # 1. Repository Load
        log_info("[Knowledge] START Repository Load")
        t_stage_start = time.perf_counter()
        
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            logger.error(f"Repository {repo_id} not found in database.")
            return

        # Skip rebuild if already completed
        if repo.knowledge_status == "completed":
            logger.info(f"Knowledge base already built for repository {repo_id}. Skipping rebuilding.")
            t_stage_duration = time.perf_counter() - t_stage_start
            log_info(f"[Knowledge] END Repository Load ({t_stage_duration:.2f}s)")
            return

        # Preparing repository knowledge status
        repo.status_message = "Preparing repository knowledge..."
        repo.knowledge_status = "indexing"
        db.commit()

        # Connect to pgvector via VectorRepository (Component 4 & 5)
        vector_repo = VectorRepository(db)
        
        # Verify pgvector table and index structure is ready
        vector_repo.ensure_vector_table(dimension=settings.EMBEDDING_DIMENSION)
        
        # Clear existing embeddings for this repository to prevent duplicates on manual re-index
        vector_repo.delete_repository_vectors(repo_id)

        t_stage_duration = time.perf_counter() - t_stage_start
        log_info(f"[Knowledge] END Repository Load ({t_stage_duration:.2f}s)")

        # 2. File Discovery
        failure_stage = "File Discovery"
        log_info("[Knowledge] START File Discovery")
        t_stage_start = time.perf_counter()
        
        repo.status_message = "Creating evidence documents..."

        # Gather previous analysis metrics
        db_files_orm = db.query(RepositoryFile).filter(RepositoryFile.repository_id == repo_id).all()
        files_processed = len(db_files_orm)
        
        # Instantiate immutable snapshots and immediately expunge ORM objects
        db_files = []
        for f in db_files_orm:
            snapshot = FileSnapshot(
                id=f.id,
                path=f.path,
                extension=f.extension,
                is_text=f.is_text,
                content_hash=f.content_hash,
                size_bytes=f.size_bytes,
                lines_of_code=f.lines_of_code,
                complexity=f.complexity,
                code_smells_count=f.code_smells_count,
                module_type=f.module_type,
                coupling_score=f.coupling_score,
                analysis_metadata=dict(f.analysis_metadata or {})
            )
            db_files.append(snapshot)
            db.expunge(f)
            
        # Files metadata gathering
        files_metadata = [
            {
                "path": f.path,
                "extension": f.extension,
                "size_bytes": f.size_bytes,
                "is_text": f.is_text,
                "lines_of_code": f.lines_of_code,
                "complexity": f.complexity,
                "module_type": f.module_type,
                "analysis_metadata": f.analysis_metadata
            }
            for f in db_files
        ]
        db_smells = db.query(CodeSmell).filter(CodeSmell.repository_id == repo_id).all()
        smells = [
            {"smell_type": s.smell_type, "category": s.category, "severity": s.severity, 
             "line_number": s.line_number, "measured_value": s.measured_value, "threshold": s.threshold, "reason": s.reason, "file_path": s.file_path}
            for s in db_smells
        ]
        for s in db_smells:
            db.expunge(s)
 
        db_sec = db.query(SecurityIssue).filter(SecurityIssue.repository_id == repo_id).all()
        sec_issues = [
            {"title": s.title, "severity": s.severity, "category": s.category, "line_number": s.line_number,
             "evidence": s.evidence, "snippet": s.snippet, "reason": s.reason, "file_path": s.file_path}
            for s in db_sec
        ]
        for s in db_sec:
            db.expunge(s)

        repo_data = {
            "id": repo.id,
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
            "architecture_score": repo.architecture_score,
            "architecture_grade": repo.architecture_grade,
            "architecture_summary": repo.architecture_summary,
            "security_score": repo.security_score,
            "security_grade": repo.security_grade
        }

        evidence_docs = build_evidence_documents(repo_data, files_metadata, smells, sec_issues)
        
        t_stage_duration = time.perf_counter() - t_stage_start
        log_info(f"[Knowledge] END File Discovery ({t_stage_duration:.2f}s)")

        # 3. Chunker & Cache Checker Pipeline
        failure_stage = "Chunking and Caching"
        log_info("[Knowledge] START Chunking & Caching")
        
        # Priority mapping for files
        def get_file_priority(path: str) -> int:
            path_lower = path.lower()
            filename = path_lower.split("/")[-1]
            if filename == "readme.md":
                return 0
            if filename in {"package.json", "pom.xml", "requirements.txt", "go.mod", "cargo.toml", "gemfile"}:
                return 1
            if "src/" in path_lower or "app/" in path_lower:
                return 2
            if "services/" in path_lower:
                return 3
            if "controllers/" in path_lower or "routes/" in path_lower:
                return 4
            if "models/" in path_lower:
                return 5
            if "tests/" in path_lower or "test/" in path_lower or "spec/" in path_lower:
                return 8
            if "docs/" in path_lower:
                return 9
            return 6
            
        # Priority sort db_files
        db_files = sorted(db_files, key=lambda f: get_file_priority(f.path))
        
        # Retrieve git HEAD hash
        import subprocess
        local_hash = None
        try:
            local_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=clone_path,
                text=True
            ).strip()
        except Exception:
            pass

        # 3a. Process Evidence Chunks (Batch 0) - Unlock progressively
        evidence_chunks = []
        for doc in evidence_docs:
            chunk_content = f"Title: {doc['title']}\nType: {doc['document_type']}\nSummary: {doc['summary']}\nEvidence: {doc['evidence']}\nPhase: {doc['source_phase']}"
            evidence_chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "document_id": doc["document_id"],
                "repo_id": str(repo_id),
                "source_phase": doc["source_phase"],
                "document_type": doc["document_type"],
                "file_path": doc["source_file"],
                "language": "Text",
                "module_type": "Unknown",
                "chunk_type": "Evidence",
                "start_line": 1,
                "end_line": 1,
                "content": chunk_content
            })
            
        if evidence_chunks:
            log_info(f"[Knowledge] Embedding {len(evidence_chunks)} Evidence documents for progressive unlock...")
            ev_prompts = [c["content"] for c in evidence_chunks]
            ev_embeddings = generate_embeddings(ev_prompts)
            vector_repo.insert_embeddings(repo_id, evidence_chunks, ev_embeddings)
            
            # Mark indexing in-memory (no progressive unlock DB commit)
            repo.knowledge_status = "indexing"
            
        # 3b. Setup Thread queues for pipeline execution
        import queue
        import threading
        
        chunk_queue = queue.Queue(maxsize=1000)
        db_queue = queue.Queue(maxsize=500)
        
        file_cache_hits = 0
        file_cache_misses = 0
        chunks_generated = len(evidence_chunks)
        total_files = len(db_files)
        total_chunk_chars = sum(len(c["content"]) for c in evidence_chunks)
        max_chunk_char = max([len(c["content"]) for c in evidence_chunks]) if evidence_chunks else 0
        
        # Estimate total chunks: average 4 chunks per file + evidence
        total_chunks_est = (total_files * 4) + len(evidence_chunks)

        embed_durations = []
        db_durations = []
        t_chunker_duration = 0.0
        num_embedders = 2

        # Thread 1: Chunker & Cache Checker
        def chunker_worker():
            nonlocal file_cache_hits, file_cache_misses, chunks_generated, total_chunk_chars, max_chunk_char, t_chunker_duration
            t_c_start = time.perf_counter()
            try:
                # Batched cache check: query all chunk metadata for this repository once
                all_cached_metadata = vector_repo.get_all_repository_chunks_metadata(repo_id)
                
                paths_to_delete = []
                for f in db_files:
                    cached_chunks = all_cached_metadata.get(f.path, [])
                    if cached_chunks and cached_chunks[0].get("metadata", {}).get("file_hash") == f.content_hash:
                        file_cache_hits += 1
                        chunks_generated += len(cached_chunks)
                        continue
                    file_cache_misses += 1
                    if cached_chunks:
                        paths_to_delete.append(f.path)
                
                if paths_to_delete:
                    vector_repo.delete_files_vectors(repo_id, paths_to_delete)
                
                candidate_chunks = []
                for f in db_files:
                    # In-memory file-level cache check
                    cached_chunks = all_cached_metadata.get(f.path, [])
                    
                    # If cached chunks exist and their metadata's file_hash matches f.content_hash, cache hit!
                    if cached_chunks and cached_chunks[0].get("metadata", {}).get("file_hash") == f.content_hash:
                        continue
                        
                    if not f.is_text:
                        continue

                    # 1. Filter supported extensions for chunking
                    supported_extensions = {
                        ".java", ".py", ".js", ".jsx", ".ts", ".tsx",
                        ".go", ".rs", ".cs", ".cpp", ".c", ".h", ".hpp",
                        ".html", ".css"
                    }
                    if f.extension not in supported_extensions:
                        continue

                    # 2. Skip lock files, minified files, configs with no explanatory value
                    fn_lower = os.path.basename(f.path).lower()
                    if fn_lower in {
                        "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                        "cargo.lock", "poetry.lock", "go.sum", "composer.lock",
                        "pipfile.lock", "mix.lock"
                    }:
                        continue
                        
                    if ".min." in fn_lower or "-min." in fn_lower:
                        continue

                    # 3. Size-based thresholds for configs/docs
                    if f.extension == ".json" and f.size_bytes > 50 * 1024:
                        continue
                    if f.extension == ".md" and f.size_bytes > 100 * 1024:
                        continue
                    if f.extension in (".yaml", ".yml") and f.size_bytes > 50 * 1024:
                        continue
                        
                    abs_path = os.path.join(clone_path, f.path)
                    if not os.path.isfile(abs_path):
                        continue
                        
                    f_content = ""
                    if file_contents and f.path in file_contents:
                        f_content = file_contents[f.path]
                    else:
                        try:
                            with open(abs_path, "r", encoding="utf-8", errors="replace") as file_obj:
                                f_content = file_obj.read()
                        except OSError:
                            continue
                        
                    # Generate adaptive chunks for this file
                    f_meta_list = [
                        {
                            "path": f.path,
                            "extension": f.extension,
                            "size_bytes": f.size_bytes,
                            "is_text": f.is_text,
                            "lines_of_code": f.lines_of_code,
                            "complexity": f.complexity,
                            "module_type": f.module_type,
                            "analysis_metadata": f.analysis_metadata
                        }
                    ]
                    f_chunks = chunk_repository(f_meta_list, {f.path: f_content}, [], str(repo_id))
                    candidate_chunks.extend(f_chunks)
                
                # Enforce dynamic global budget to hit the target 180-250 chunks.
                # Evidence chunks are embedded in Batch 0 (len(evidence_chunks)).
                # Target total chunks: 240. So target code chunks = 240 - len(evidence_chunks).
                target_code_chunks = max(100, 240 - len(evidence_chunks))
                
                selected_chunks = select_best_chunks(candidate_chunks, max_budget=target_code_chunks, sec_issues=sec_issues)
                log_info(f"[Knowledge] Global budget enforcement: selected {len(selected_chunks)} chunks from {len(candidate_chunks)} candidates. Target was {target_code_chunks}.")
                
                # Add surviving chunks to queue
                for chunk in selected_chunks:
                    chunk_queue.put(chunk)
                    chunk_len = len(chunk["content"])
                    total_chunk_chars += chunk_len
                    max_chunk_char = max(max_chunk_char, chunk_len)
                        
            except Exception as w_err:
                logger.error(f"Chunker worker failed: {w_err}", exc_info=True)
            finally:
                t_chunker_duration = time.perf_counter() - t_c_start
                # Signal each embedder that chunking is finished
                for _ in range(num_embedders):
                    chunk_queue.put(None)

        # Thread 2: Parallel Embedder
        def embedder_worker():
            try:
                batch = []
                batch_size = 128  # Safe large batch size for local FastEmbed TextEmbedding
                
                while True:
                    chunk = chunk_queue.get()
                    if chunk is None:
                        # Process remaining in batch
                        if batch:
                            prompts = [c["content"] for c in batch]
                            t_emb_call_start = time.perf_counter()
                            embeddings = generate_embeddings(prompts)
                            embed_durations.append(time.perf_counter() - t_emb_call_start)
                            db_queue.put((batch, embeddings))
                        break
                        
                    batch.append(chunk)
                    if len(batch) >= batch_size:
                        prompts = [c["content"] for c in batch]
                        t_emb_call_start = time.perf_counter()
                        embeddings = generate_embeddings(prompts)
                        embed_durations.append(time.perf_counter() - t_emb_call_start)
                        db_queue.put((batch, embeddings))
                        batch = []
                        
            except Exception as w_err:
                logger.error(f"Embedder worker failed: {w_err}", exc_info=True)
            finally:
                db_queue.put(None)  # Sentinel

        # Start background threads
        log_info("[Knowledge] START Chunking & Caching")
        log_info("[Knowledge] START Chunking")
        log_info("[Knowledge] START Embedding")
        log_info("[Knowledge] START DB Writes")
        
        t_chunker = threading.Thread(target=chunker_worker, daemon=True)
        t_chunker.start()
        
        embedder_threads = []
        for _ in range(num_embedders):
            t_emb = threading.Thread(target=embedder_worker, daemon=True)
            t_emb.start()
            embedder_threads.append(t_emb)
        
        # DB Writer (runs in main thread context)
        t_embed_start = time.perf_counter()
        t_vector_db_start = time.perf_counter()
        
        s_db = SessionLocal()
        s_repo = s_db.query(Repository).filter(Repository.id == repo_id).first()
        s_vector_repo = VectorRepository(s_db)
        
        processed_files = 0
        chunks_embedded = len(evidence_chunks)
        sentinels_received = 0
        
        while True:
            # Watchdog timeout check
            elapsed = time.time() - t_kb_loop_start
            if elapsed > timeout_seconds:
                raise TimeoutError(f"Knowledge Base compilation exceeded maximum allowed duration of {timeout_seconds} seconds.")
                
            item = db_queue.get()
            if item is None:
                sentinels_received += 1
                if sentinels_received >= num_embedders:
                    break
                continue
                
            batch_chunks, batch_embeddings = item
            t_db_call_start = time.perf_counter()
            s_vector_repo.insert_embeddings(repo_id, batch_chunks, batch_embeddings)
            db_durations.append(time.perf_counter() - t_db_call_start)
            
            chunks_embedded += len(batch_chunks)
            chunks_generated += len(batch_chunks)
            
            # Recalculate progressive stats
            processed_files = int((chunks_embedded / max(1, total_chunks_est)) * total_files)
            processed_files = min(processed_files, total_files)
            
            pct = min(99, int((chunks_embedded / max(1, total_chunks_est)) * 100))
            
            # Only update status message and commit at most once every 2.0 seconds
            t_now = time.time()
            if 'last_progress_commit' not in locals():
                last_progress_commit = 0.0
            if t_now - last_progress_commit >= 2.0:
                # Estimate remaining time
                t_elapsed = time.perf_counter() - t_embed_start
                rate = chunks_embedded / max(0.1, t_elapsed)
                remaining_chunks = max(0, total_chunks_est - chunks_embedded)
                eta = int(remaining_chunks / rate) if rate > 0 else 0
                
                # Do not perform intermediate progress commits
                pass
                last_progress_commit = t_now
            
        t_chunker.join()
        for t_emb in embedder_threads:
            t_emb.join()
        
        t_chunking_caching_duration = time.perf_counter() - t_embed_start
        log_info(f"[Knowledge] END Chunking ({t_chunker_duration:.2f}s)")
        log_info(f"[Knowledge] END Embedding ({sum(embed_durations):.2f}s)")
        log_info(f"[Knowledge] END DB Writes ({sum(db_durations):.2f}s)")
        log_info(f"[Knowledge] END Chunking & Caching ({t_chunking_caching_duration:.2f}s)")
        
        # Save cache commit hash & total durations
        t_embed_duration = time.perf_counter() - t_embed_start
        t_vector_db_duration = time.perf_counter() - t_vector_db_start
        
        # final DB update
        s_repo.status_message = "Knowledge base compilation finalized."
        s_db.commit()
        
        # Store file cache hits stats in metadata for Performance Dashboard
        summary_details = dict(s_repo.knowledge_summary or {})
        summary_details["file_cache_hits"] = file_cache_hits
        summary_details["file_cache_misses"] = file_cache_misses
        s_repo.knowledge_summary = summary_details
        s_db.commit()
        
        s_db.close()

        # 6. Metadata Save
        failure_stage = "Metadata Save"
        log_info("[Knowledge] START Metadata Save")
        t_stage_start = time.perf_counter()
        
        repo.status_message = "Repository ready for AI..."
        db.commit()

        supported_langs = list(repo.language_breakdown.keys()) if repo.language_breakdown else []
        indexed_files = [f.path for f in db_files if f.is_text and f.path != "README.md"]

        # Load all structured data to build health score and dashboard breakdowns
        from app.services.analysis.scoring import calculate_weighted_health_score, calculate_grade
        
        # Aggregate details
        current_summary = repo.knowledge_summary or {}
        arch_knowledge = current_summary.get("architecture_knowledge") or {}
        timing_data = current_summary.get("timing_metadata") or {}
        
        # Count components for summary description
        layers = arch_knowledge.get("layers", {})
        controller_count = len(layers.get("controllers", []))
        service_count = len(layers.get("services", []))
        repo_count = len(layers.get("repositories", []))
        model_count = len(layers.get("entities", []))
        util_count = len(layers.get("utilities", []))
        
        # Primary framework / package manager
        fw_list = repo.tech_stack.get("frameworks", []) if repo.tech_stack else []
        primary_fw = fw_list[0] if fw_list else "None"
        pkg_manager = repo.tech_stack.get("package_manager", "None") if repo.tech_stack else "None"
        
        # Find business logic location
        biz_file = "None"
        max_loc = 0
        for f in db_files:
            if f.module_type == "Service" or "service" in f.path.lower():
                if f.lines_of_code > max_loc:
                    max_loc = f.lines_of_code
                    biz_file = os.path.basename(f.path)

        # Structure MVC text summary
        cycle_count = len(arch_knowledge.get("circular_dependencies", []))
        mvc_text = f"MVC layered architecture. " if controller_count or service_count or repo_count else ""
        summary_desc = (
            f"{mvc_text}{repo.total_files} files parsed. "
            f"{controller_count} Controllers, {service_count} Services, {repo_count} Repositories. "
            f"Business logic primarily located inside {biz_file if biz_file != 'None' else 'Services'}. "
            f"{'Circular dependencies detected' if cycle_count > 0 else 'No circular dependencies detected'}."
        )

        # Health Scoring
        db_sec = db.query(SecurityIssue).filter(SecurityIssue.repository_id == repo_id).all()
        sec_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for s in db_sec:
            sec_counts[s.severity] = sec_counts.get(s.severity, 0) + 1

        highly_coupled_count = sum(1 for f in db_files if f.coupling_score > 8)
        
        # Average comment ratio
        comment_ratios = []
        for f in db_files:
            if f.analysis_metadata and "metrics" in f.analysis_metadata:
                comment_ratios.append(f.analysis_metadata["metrics"].get("comment_ratio", 0.0))
        avg_comment_ratio = sum(comment_ratios) / len(comment_ratios) if comment_ratios else 0.0

        # Calculate final weighted health score
        health_data = calculate_weighted_health_score(
            average_complexity=repo.average_complexity,
            total_smells=repo.total_smells,
            security_counts=sec_counts,
            cycle_count=cycle_count,
            highly_coupled_count=highly_coupled_count,
            comment_ratio=avg_comment_ratio,
            duplication_percentage=repo.duplication_percentage
        )
        
        repo.health_score = health_data["final_score"]
        repo.health_grade = calculate_grade(health_data["final_score"])

        # Build structured knowledge objects list for AI foundation
        knowledge_objects = {
            "repository": {
                "id": str(repo_id),
                "url": repo.url,
                "health_score": repo.health_score,
                "health_grade": repo.health_grade,
                "timing": timing_data
            },
            "files": [
                {
                    "path": f.path,
                    "extension": f.extension,
                    "loc": f.lines_of_code,
                    "complexity": f.complexity,
                    "smells_count": f.code_smells_count,
                    "declarations": [],
                    "dependencies": []
                }
                for f in db_files
            ],
            "smells": smells,
            "security_findings": repo.security_findings
        }

        # 1. Populating Wiki Cards
        wiki_controllers = []
        for path in layers.get("controllers", []):
            wiki_controllers.append(path)
        
        wiki_services = []
        for path in layers.get("services", []):
            wiki_services.append(path)
            
        wiki_repositories = []
        for path in layers.get("repositories", []):
            wiki_repositories.append(path)
            
        wiki_entities = []
        for path in layers.get("entities", []):
            wiki_entities.append(path)
            
        wiki_utilities = []
        for path in layers.get("utilities", []):
            wiki_utilities.append(path)
            
        wiki_configs = []
        for f in db_files:
            fn = os.path.basename(f.path).lower()
            if fn in ["package.json", "pom.xml", "build.gradle", "pyproject.toml", "requirements.txt", "settings.py", "setup.py", "config.js", "config.ts", ".env", "application.properties", "application.yml"]:
                wiki_configs.append(f.path)
                
        wiki_entry_points = []
        for f in db_files:
            fn = os.path.basename(f.path).lower()
            if fn in ["main.py", "app.py", "server.js", "index.js", "index.ts", "main.go", "app.java"] or "main" in fn:
                wiki_entry_points.append(f.path)
                
        wiki_important_files = [f.path for f in sorted(db_files, key=lambda x: x.lines_of_code, reverse=True)[:5]]
        
        dependencies_detected = repo.tech_stack.get("frameworks", []) if repo.tech_stack else []
        if repo.tech_stack and repo.tech_stack.get("package_manager"):
            dependencies_detected.append(repo.tech_stack["package_manager"])
        
        wiki_data = {
            "controllers": {
                "items": wiki_controllers,
                "reason_if_empty": "No controllers or API routing files were detected because this codebase represents a utility library, service layer, or CLI tool rather than a web application or REST API."
            },
            "services": {
                "items": wiki_services,
                "reason_if_empty": "No service layers found. Business logic may be coupled inside routes, utilities, or main entry files."
            },
            "repositories": {
                "items": wiki_repositories,
                "reason_if_empty": "No database repositories detected. This project may use memory cache, local files, or external APIs instead of SQL/ORM storage."
            },
            "entities": {
                "items": wiki_entities,
                "reason_if_empty": "No database models or entities were detected. Data persistence structures are either external or represented by plain dictionary objects."
            },
            "utilities": {
                "items": wiki_utilities,
                "reason_if_empty": "No dedicated utility helper files detected. Cross-cutting concerns are directly written inside service files."
            },
            "configurations": {
                "items": wiki_configs,
                "reason_if_empty": "No environment setup or configuration files detected. Configuration details might be hardcoded inside system scripts."
            },
            "architecture": {
                "items": [f"Grading: {repo.architecture_grade}", f"Total Modules: {len(db_files)}", f"Coupling Score: {highly_coupled_count} coupled"],
                "reason_if_empty": "Architecture summary is empty because no dependency graph links could be mapped."
            },
            "entry_points": {
                "items": wiki_entry_points,
                "reason_if_empty": "No main startup script or standard executable entry point detected."
            },
            "important_files": {
                "items": wiki_important_files,
                "reason_if_empty": "No important source files were indexed."
            },
            "dependencies": {
                "items": dependencies_detected,
                "reason_if_empty": "No external dependency manifests or package managers were detected."
            }
        }

        # 2. Build Knowledge Graph relationships (disabled for performance)
        knowledge_graph = {
            "nodes": [],
            "edges": []
        }

        # 3. Build Learning Report
        purpose = (
            f"This project is a {primary_fw if primary_fw != 'None' else 'custom'} application built using "
            f"{', '.join(supported_langs) if supported_langs else 'programming languages'}. "
            f"It consists of {repo.total_files} files with {repo.total_lines_of_code:,} total lines of code."
        )
        
        detected_patterns = []
        if controller_count > 0:
            detected_patterns.append("MVC Architectural Pattern (Controllers, Services)")
        if repo_count > 0:
            detected_patterns.append("Data Access Repository Pattern")
        if util_count > 0:
            detected_patterns.append("Utility Helper Delegation Pattern")
        if not detected_patterns:
            detected_patterns.append("Procedural/Modular Scripting Pattern")
            
        strengths = [
            f"Clear programming language breakdown: {', '.join(supported_langs) if supported_langs else 'clean structure'}.",
            f"Average code complexity of {repo.average_complexity:.2f} is within healthy bounds."
        ]
        if controller_count > 0 and service_count > 0:
            strengths.append("Modular Separation of Concerns using Controllers and Services.")
            
        weaknesses = []
        if len(sec_issues) > 0:
            weaknesses.append(f"Security Vulnerabilities: Found {len(sec_issues)} security warnings.")
        if len(smells) > 0:
            weaknesses.append(f"Code Smells: Detected {len(smells)} code smells that lower maintainability.")
        if cycle_count > 0:
            weaknesses.append(f"Architecture: Detected {cycle_count} circular dependency loops.")
        if not weaknesses:
            weaknesses.append("No critical code smells, vulnerability alerts, or cycles detected.")
            
        interview_q = [
            "Explain the overall architecture and layering of this project.",
            f"How would you refactor the largest modules (e.g. {wiki_important_files[0] if wiki_important_files else 'main components'}) to simplify maintenance?"
        ]
        if len(sec_issues) > 0:
            interview_q.append("What security vulnerabilities exist here, and how would you resolve them?")
            
        resume_h = [
            f"Analyzed and orchestrated a {primary_fw if primary_fw != 'None' else 'custom'} repository of {repo.total_lines_of_code:,} LOC, maintaining clean-code practices.",
            f"Maintained codebase health rating of {repo.health_score}/100."
        ]
        if len(sec_issues) > 0 or len(smells) > 0:
            resume_h.append(f"Identified and prioritized refactoring steps for {len(smells) + len(sec_issues)} quality issues.")
            
        recruiter_summary = (
            f"A functional codebase written in {', '.join(supported_langs) if supported_langs else 'code'}. "
            f"The architecture follows {primary_fw if primary_fw != 'None' else 'custom modular'} patterns, "
            f"maintaining a health score of {repo.health_score}/100. Best suited for deployment in structured environments."
        )
        
        learning_report = {
            "purpose": purpose,
            "architecture": mvc_text + f"The project contains {controller_count} entry routers, {service_count} service handlers, and {repo_count} database access layers.",
            "tech_stack": f"Languages: {', '.join(supported_langs)}. Frameworks: {', '.join(fw_list)}. Package Manager: {pkg_manager}.",
            "design_patterns": detected_patterns,
            "complexity": f"Average complexity = {repo.average_complexity:.2f}. Max complexity = {repo.max_complexity}.",
            "security": f"Vulnerabilities found: {len(sec_issues)}. Security Score: {repo.security_score}/100.",
            "maintainability": f"Smells count: {repo.total_smells}. Duplication: {repo.duplication_percentage}%.",
            "strengths": strengths,
            "weaknesses": weaknesses,
            "top_improvements": [s["smell_type"] for s in smells[:5]] + [s["title"] for s in sec_issues[:5]],
            "interview_questions": interview_q,
            "resume_highlights": resume_h,
            "recruiter_summary": recruiter_summary
        }

        # Populate performance metrics (Task 10)
        t_embeds = sum(embed_durations)
        t_db = sum(db_durations)
        t_kb_total = time.perf_counter() - t_kb_start
        
        performance_metrics = {
            "clone": timing_data.get("clone", 0.0),
            "parser": timing_data.get("parsing", 0.0),
            "architecture": timing_data.get("architecture", 0.0),
            "security": timing_data.get("security", 0.0),
            "chunking": round(t_chunker_duration, 2),
            "embeddings": round(t_embeds, 2),
            "database": round(t_db, 2),
            "knowledge": round(t_kb_total, 2),
            "total": round(timing_data.get("total_phase_a", 0.0) + t_kb_total, 2)
        }

        # Combine everything into final knowledge_summary JSON
        summary_data = {
            "total_chunks": chunks_generated,
            "code_chunks": chunks_generated - len(evidence_chunks),
            "evidence_documents": len(evidence_chunks),
            "indexed_files": len(indexed_files),
            "supported_languages": supported_langs,
            "build_status": "completed",
            "last_commit_hash": local_hash,
            "file_cache_hits": file_cache_hits,
            "file_cache_misses": file_cache_misses,
            "embedding_status": "Local BAAI/bge-small-en-v1.5 active",
            "evidence_docs_list": [
                {
                    "document_type": d["document_type"],
                    "title": d["title"],
                    "summary": d["summary"],
                    "source_file": d["source_file"]
                }
                for d in evidence_docs
            ],
            "architecture_knowledge": arch_knowledge,
            "timing_metadata": timing_data,
            "health_metadata": health_data,
            "security_metadata": current_summary.get("security_metadata") or {},
            "knowledge_objects": knowledge_objects,
            "summary_description": summary_desc,
            "wiki_data": wiki_data,
            "knowledge_graph": knowledge_graph,
            "learning_report": learning_report,
            "performance": performance_metrics
        }

        repo.knowledge_status = "completed"
        repo.knowledge_summary = summary_data
        repo.status_message = None
        db.commit()
        
        t_stage_duration = time.perf_counter() - t_stage_start
        log_info(f"[Knowledge] END Metadata Save ({t_stage_duration:.2f}s)")
        log_info("[Knowledge] Knowledge Build Complete")
        failure_stage = "None"
        
    except Exception as e:
        failure_reason = str(e)
        logger.error(f"Knowledge Base build failed at stage '{failure_stage}': {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass

        try:
            repo = db.query(Repository).filter(Repository.id == repo_id).first()
            if repo:
                repo.knowledge_status = "failed"
                if "timed out" in str(e).lower() or isinstance(e, TimeoutError):
                    repo.status_message = "Knowledge build timed out"
                else:
                    repo.status_message = "Failed: Cloud Embeddings error"
                repo.error_message = f"Knowledge base compilation error: {str(e)}"
                
                # Update knowledge_summary with failed metadata and knowledge_error
                summary = repo.knowledge_summary or {}
                summary["knowledge_error"] = str(e)
                summary["build_status"] = "failed"
                repo.knowledge_summary = summary
                
                db.commit()
        except Exception as db_err:
            logger.critical(f"Failed to update failed knowledge status: {db_err}")
    finally:
        total_duration = time.perf_counter() - t_kb_start
        
        # Calculate statistics
        avg_chunk_size = total_chunk_chars / max(1, chunks_generated)
        largest_chunk = max_chunk_char
            
        # Log statistics
        log_info(f"Total Files Processed: {files_processed}")
        log_info(f"Total Chunks Generated: {chunks_generated}")
        log_info(f"Average Chunk Size: {avg_chunk_size:.2f} chars")
        log_info(f"Largest Chunk Size: {largest_chunk} chars")
        log_info(f"Embedding Requests Executed: {embedding_requests}")
        log_info(f"pgvector Insert Count: {vector_db_insert_count}")

        # Final diagnostic summary formatted exactly as required
        summary_str = (
            "Knowledge Build Summary\n"
            "-----------------------\n"
            f"Files Processed: {files_processed}\n"
            f"Chunks Generated: {chunks_generated}\n"
            f"Embedding Time: {t_embed_duration:.2f}s\n"
            f"pgvector Write Time: {t_vector_db_duration:.2f}s\n"
            f"Total Duration: {total_duration:.2f}s\n"
            f"Failure Stage: {failure_stage}\n"
            f"Failure Reason: {failure_reason}"
        )
        log_info(f"\n{summary_str}")
        
        # Save diagnostics summary to repo metadata if possible
        try:
            repo = db.query(Repository).filter(Repository.id == repo_id).first()
            if repo:
                summary = repo.knowledge_summary or {}
                summary["diagnostics"] = {
                    "files_processed": files_processed,
                    "chunks_generated": chunks_generated,
                    "embedding_time_sec": t_embed_duration,
                    "pgvector_write_time_sec": t_vector_db_duration,
                    "total_duration_sec": total_duration,
                    "failure_stage": failure_stage,
                    "failure_reason": failure_reason,
                    "average_chunk_size": avg_chunk_size,
                    "largest_chunk": largest_chunk,
                    "embedding_requests": embedding_requests,
                    "pgvector_inserts": vector_db_insert_count
                }
                repo.knowledge_summary = summary
                db.commit()
        except Exception:
            pass
            
        db.close()
