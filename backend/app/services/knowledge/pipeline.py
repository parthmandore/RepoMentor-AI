from sqlalchemy.orm.attributes import flag_modified
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
from app.services.knowledge.chunker import chunk_repository, select_best_chunks, should_skip_file
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
                "chunk_type": "evidence",
                "start_line": None,
                "end_line": None,
                "content": chunk_content,
                "priority_tier": 1,
                "metadata": {"priority_tier": 1, "document_type": doc["document_type"]}
            })
            
        if evidence_chunks:
            log_info(f"[Knowledge] Embedding {len(evidence_chunks)} Evidence documents for progressive unlock...")
            ev_prompts = [c["content"] for c in evidence_chunks]
            try:
                ev_embeddings = generate_embeddings(ev_prompts)
                vector_repo.insert_embeddings(repo_id, evidence_chunks, ev_embeddings)
            except EmbeddingGenerationError as emb_err:
                log_info(f"[Knowledge] Embedding provider unavailable ({emb_err}). Storing evidence chunks without vectors for keyword search.")
                vector_repo.insert_embeddings(repo_id, evidence_chunks, [None] * len(evidence_chunks))
            
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
        t_emb_first = 0.0
        t_emb_last = 0.0
        t_chunker_duration = 0.0
        num_embedders = 1
        skipped_files = []
        truncated_files = []
        total_p1_target = 0
        total_expected_chunks = len(evidence_chunks)
        p1_embedded_count = 0
        p1_unlocked = False
        worker_errors = []

        # Thread 1: Chunker & Cache Checker
        def chunker_worker():
            nonlocal file_cache_hits, file_cache_misses, chunks_generated, total_chunk_chars, max_chunk_char, t_chunker_duration, skipped_files, truncated_files, total_p1_target, total_expected_chunks
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
                seen_content_hashes = set()
                for f in db_files:
                    # In-memory file-level cache check
                    cached_chunks = all_cached_metadata.get(f.path, [])
                    
                    # If cached chunks exist and their metadata's file_hash matches f.content_hash, cache hit!
                    if cached_chunks and cached_chunks[0].get("metadata", {}).get("file_hash") == f.content_hash:
                        continue

                    # Option A: Deduplicate identical files across folders (e.g. frontend/ vs FrontendN/)
                    if f.content_hash:
                        if f.content_hash in seen_content_hashes:
                            skipped_files.append({"path": f.path, "reason": "Option A: Duplicate file content", "size": f.size_bytes})
                            continue
                        seen_content_hashes.add(f.content_hash)
                        
                    if not f.is_text:
                        skipped_files.append({"path": f.path, "reason": "Binary non-text file", "size": f.size_bytes})
                        continue

                    abs_path = os.path.join(clone_path, f.path)
                    f_content = ""
                    if file_contents and f.path in file_contents:
                        f_content = file_contents[f.path]
                    elif os.path.isfile(abs_path):
                        try:
                            with open(abs_path, "r", encoding="utf-8", errors="replace") as file_obj:
                                f_content = file_obj.read()
                        except OSError:
                            continue

                    # 1. General guard check: empty files, dotfiles, data dumps, minified, oversized
                    should_skip, skip_reason = should_skip_file(f.path, f.extension, f.size_bytes, f_content)
                    if should_skip:
                        skipped_files.append({"path": f.path, "reason": skip_reason, "size": f.size_bytes})
                        continue

                    # 2. Supported file extensions for chunking
                    supported_extensions = {
                        ".java", ".py", ".js", ".jsx", ".ts", ".tsx",
                        ".go", ".rs", ".cs", ".cpp", ".c", ".h", ".hpp",
                        ".html", ".css", ".ipynb", ".md", ".json", ".txt", ".yaml", ".yml"
                    }
                    if f.extension and f.extension.lower() not in supported_extensions:
                        skipped_files.append({"path": f.path, "reason": f"Non-code file format ({f.extension})", "size": f.size_bytes})
                        continue

                    if not f_content:
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
                    f_chunks = chunk_repository(f_meta_list, {f.path: f_content}, [], str(repo_id), truncated_files=truncated_files)
                    candidate_chunks.extend(f_chunks)
                
                from app.services.knowledge.chunker import is_priority_1_chunk
                
                # Split candidate chunks into Priority 1 and Priority 2
                p1_candidates = []
                p2_candidates = []
                for c in candidate_chunks:
                    if "metadata" not in c or not isinstance(c["metadata"], dict):
                        c["metadata"] = {}
                    if is_priority_1_chunk(c):
                        c["priority_tier"] = 1
                        c["metadata"]["priority_tier"] = 1
                        p1_candidates.append(c)
                    else:
                        c["priority_tier"] = 2
                        c["metadata"]["priority_tier"] = 2
                        p2_candidates.append(c)
                        
                p1_selected = p1_candidates
                p2_selected = p2_candidates
                
                total_p1_target = len(p1_selected)
                total_expected_chunks = len(evidence_chunks) + len(p1_selected) + len(p2_selected)
                log_info(f"[Knowledge] Priority Partitioning: {len(p1_selected)} Priority 1 chunks, {len(p2_selected)} Priority 2 chunks (Total: {total_expected_chunks}).")
                
                # Add Priority 1 chunks to queue first
                for chunk in p1_selected:
                    chunk_queue.put(chunk)
                    chunk_len = len(chunk["content"])
                    total_chunk_chars += chunk_len
                    max_chunk_char = max(max_chunk_char, chunk_len)

                # Add Priority 2 chunks to queue next
                for chunk in p2_selected:
                    chunk_queue.put(chunk)
                    chunk_len = len(chunk["content"])
                    total_chunk_chars += chunk_len
                    max_chunk_char = max(max_chunk_char, chunk_len)

                candidate_chunks.clear()
                p1_candidates.clear()
                p2_candidates.clear()
                p1_selected.clear()
                p2_selected.clear()
                        
            except Exception as w_err:
                worker_errors.append(("Chunking", str(w_err)))
                logger.error(f"Chunker worker failed: {w_err}", exc_info=True)
                print(f"[ERROR] Chunker worker failed: {w_err}", flush=True)
                import traceback
                traceback.print_exc()
            finally:
                t_chunker_duration = time.perf_counter() - t_c_start
                # Signal each embedder that chunking is finished
                for _ in range(num_embedders):
                    chunk_queue.put(None)

        # Thread 2: Parallel Embedder
        def embedder_worker():
            nonlocal t_emb_first, t_emb_last
            try:
                batch = []
                batch_size = 64  # Optimal measured batch size for FastEmbed on CPU
                
                while True:
                    chunk = chunk_queue.get()
                    if chunk is None:
                        print(f"[DEBUG embedder] Received None. Batch length: {len(batch)}", flush=True)
                        # Process remaining in batch
                        if batch:
                            prompts = [c["content"] for c in batch]
                            t_emb_call_start = time.perf_counter()
                            if t_emb_first == 0.0:
                                t_emb_first = t_emb_call_start
                            try:
                                embeddings = generate_embeddings(prompts)
                            except EmbeddingGenerationError as emb_err:
                                logger.info(f"[Knowledge] Embedding API unavailable ({emb_err}). Storing batch of {len(batch)} chunks without vectors for keyword search.")
                                embeddings = [None] * len(batch)
                            t_emb_call_end = time.perf_counter()
                            t_emb_last = t_emb_call_end
                            t_emb_call = t_emb_call_end - t_emb_call_start
                            embed_durations.append(t_emb_call)
                            print(f"[DEBUG embedder] Embedded {len(batch)} chunks in {t_emb_call:.2f}s. Putting to db_queue", flush=True)
                            db_queue.put((batch, embeddings))
                        break
                        
                    batch.append(chunk)
                    if len(batch) >= batch_size:
                        prompts = [c["content"] for c in batch]
                        t_emb_call_start = time.perf_counter()
                        if t_emb_first == 0.0:
                            t_emb_first = t_emb_call_start
                        try:
                            embeddings = generate_embeddings(prompts)
                        except EmbeddingGenerationError as emb_err:
                            logger.info(f"[Knowledge] Embedding API unavailable ({emb_err}). Storing batch of {len(batch)} chunks without vectors for keyword search.")
                            embeddings = [None] * len(batch)
                        t_emb_call_end = time.perf_counter()
                        t_emb_last = t_emb_call_end
                        t_emb_call = t_emb_call_end - t_emb_call_start
                        embed_durations.append(t_emb_call)
                        print(f"[DEBUG embedder] Embedded full batch {len(batch)} chunks in {t_emb_call:.2f}s. Putting to db_queue", flush=True)
                        db_queue.put((batch, embeddings))
                        batch = []
                        
            except Exception as w_err:
                worker_errors.append(("Embedding", str(w_err)))
                logger.error(f"Embedder worker failed: {w_err}", exc_info=True)
                print(f"[ERROR] Embedder worker failed: {w_err}", flush=True)
                import traceback
                traceback.print_exc()
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
            if worker_errors:
                stage, err_msg = worker_errors[0]
                failure_stage = stage
                raise RuntimeError(f"{stage} worker crashed: {err_msg}")

            # Watchdog timeout check - graceful partial indexing instead of crashing
            elapsed = time.time() - t_kb_loop_start
            if elapsed > timeout_seconds:
                logger.warning(f"Knowledge Base compilation reached {timeout_seconds}s limit. Finalizing {chunks_embedded} chunks gracefully.")
                try:
                    s_repo.knowledge_status = "ready" if p1_unlocked else "partial"
                    s_repo.status_message = f"Chat index: {min(99, int((chunks_embedded / max(1, total_expected_chunks)) * 100))}% ({chunks_embedded} chunks indexed)"
                    s_db.commit()
                except Exception:
                    pass
                break
                
            item = db_queue.get()
            if item is None:
                sentinels_received += 1
                print(f"[DEBUG db_loop] Received sentinel {sentinels_received}/{num_embedders}", flush=True)
                if sentinels_received >= num_embedders:
                    break
                continue
                
            batch_chunks, batch_embeddings = item
            batch_size = len(batch_chunks)
            print(f"[DEBUG db_loop] Got batch of {batch_size} chunks from db_queue. Inserting into pgvector...", flush=True)
            t_db_call_start = time.perf_counter()
            s_vector_repo.insert_embeddings(repo_id, batch_chunks, batch_embeddings)
            db_durations.append(time.perf_counter() - t_db_call_start)
            
            for chunk in batch_chunks:
                if chunk.get("priority_tier") == 1:
                    p1_embedded_count += 1

            if not p1_unlocked and (p1_embedded_count >= total_p1_target or total_p1_target == 0):
                p1_unlocked = True
                try:
                    s_db.expire_all()
                    s_db.refresh(s_repo)
                    s_repo.knowledge_status = "ready"
                    pct = int(((len(evidence_chunks) + p1_embedded_count) / max(1, total_expected_chunks)) * 100)
                    pct = min(99, max(50, pct))
                    s_repo.status_message = f"Chat index: {pct}%"
                    summary_details = dict(s_repo.knowledge_summary or {})
                    summary_details["chat_index_progress"] = pct
                    s_repo.knowledge_summary = summary_details
                    flag_modified(s_repo, "knowledge_summary")
                    s_db.commit()
                    log_info(f"[Knowledge] Priority 1 indexing ready ({p1_embedded_count} chunks). Mentor unblocked. Chat index: {pct}%")
                except Exception as p1_err:
                    logger.warning(f"Failed to commit P1 unlock state: {p1_err}")

            # Release batch memory immediately
            batch_chunks.clear()
            batch_embeddings.clear()
            del batch_chunks
            del batch_embeddings
            
            chunks_embedded += batch_size
            chunks_generated += batch_size
            
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
        
        if worker_errors:
            stage, err_msg = worker_errors[0]
            failure_stage = stage
            raise RuntimeError(f"{stage} worker crashed: {err_msg}")
        
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
        
        # Release the ONNX embedding model global cache and trigger garbage collection immediately.
        # This frees ~2.0 GB of native RAM before entering the final Metadata Save phase.
        from app.services.knowledge import embedder
        import gc
        embedder._model = None
        gc.collect()

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
        db.refresh(repo)
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

        # Populate performance metrics with real wall-clock measurements
        t_embed_wall = round(t_emb_last - t_emb_first, 3) if t_emb_last > t_emb_first else round(sum(embed_durations), 3)
        t_db_wall = round(sum(db_durations), 3)
        t_kb_total = round(time.perf_counter() - t_kb_start, 3)
        t_phase_a_total = timing_data.get("total_phase_a", 0.0)
        t_total_pipeline = round(t_phase_a_total + t_kb_total, 3)
        
        stages_sum = round(
            timing_data.get("clone", 0.0) +
            timing_data.get("parsing", 0.0) +
            timing_data.get("metrics", 0.0) +
            timing_data.get("architecture", 0.0) +
            timing_data.get("security", 0.0) +
            t_chunker_duration +
            t_embed_wall +
            t_db_wall +
            timing_data.get("assessment", 0.0),
            3
        )
        other_unaccounted = max(0.0, round(t_total_pipeline - stages_sum, 3))

        performance_metrics = {
            "clone": timing_data.get("clone", 0.0),
            "parser": timing_data.get("parsing", 0.0),
            "metrics": timing_data.get("metrics", 0.0),
            "architecture": timing_data.get("architecture", 0.0),
            "security": timing_data.get("security", 0.0),
            "time_to_first_page": t_phase_a_total,
            "chunking": round(t_chunker_duration, 3),
            "embeddings": t_embed_wall,
            "database": t_db_wall,
            "vector_database": t_db_wall,
            "assessment": timing_data.get("assessment", 0.0),
            "other_unaccounted": other_unaccounted,
            "knowledge": t_kb_total,
            "total": t_total_pipeline,
            "skipped_files": skipped_files,
            "skipped_files_count": len(skipped_files),
            "truncated_files": truncated_files,
            "truncated_files_count": len(truncated_files)
        }

        # Combine everything into final knowledge_summary JSON
        summary_data = {
            "total_chunks": chunks_generated,
            "code_chunks": max(0, chunks_generated - len(evidence_chunks)),
            "evidence_documents": len(evidence_chunks),
            "expected_chunk_count": total_expected_chunks,
            "stored_chunk_count": chunks_generated,
            "embedding_model": getattr(settings, "EMBEDDING_MODEL", "text-embedding-004"),
            "embedding_dim": getattr(settings, "EMBEDDING_DIMENSION", 768),
            "indexed_files": len(indexed_files),
            "supported_languages": supported_langs,
            "build_status": "completed",
            "last_commit_hash": local_hash,
            "file_cache_hits": file_cache_hits,
            "file_cache_misses": file_cache_misses,
            "skipped_files": skipped_files,
            "truncated_files": truncated_files,
            "embedding_provider": f"External API ({getattr(settings, 'EMBEDDING_MODEL', 'text-embedding-004')})",
            "embedding_status": f"External {getattr(settings, 'EMBEDDING_MODEL', 'text-embedding-004')} active",
            "chat_index_progress": 100,
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
        repo.knowledge_summary = dict(summary_data)
        flag_modified(repo, "knowledge_summary")
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
                    repo.status_message = f"Failed: {failure_stage}"
                repo.error_message = f"Knowledge base compilation error in stage '{failure_stage}': {str(e)}"
                
                # Update knowledge_summary with failed metadata and failure details
                summary = dict(repo.knowledge_summary or {})
                summary["knowledge_error"] = str(e)
                summary["build_status"] = "failed"
                summary["failure_stage"] = failure_stage
                summary["failure_reason"] = failure_reason
                repo.knowledge_summary = summary
                flag_modified(repo, "knowledge_summary")
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
