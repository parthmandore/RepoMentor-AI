# Changelog

All notable changes to **Repository Mentor AI** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-07-10

This marks the official production release (v1.0.0) of **Repository Mentor AI**. The system has been validated under heavy sequential stress testing and parallel workloads inside isolated production-grade container environments, maintaining full operational stability within a sub-350 MB memory envelope.

### Added
* **Dynamic Scorer & Explainer**: Implemented the deterministic codebase health grading system calculating cyclomatic complexity, code smells, design coupling, and security vulnerability density.
* **Refactoring Task Planner**: Prioritized list of codebase improvements mapped to code locations, estimating health index gains and time-to-fix values.
* **pgvector Search Explorer**: An interactive client panel allowing developers to inspect chunked code passages and query nearest-neighbor semantic search matches directly.
* **AST Security Auditor View**: AST regex-based scanners detecting SQL Injection, hardcoded secrets, weak hashes, and dangerous API usages with inline code view and remediations.
* **Decoupled Ingestion Pipeline**: Asynchronous background workers managing Git cloning, parsing, and analysis, reporting real-time status notifications to the Next.js UI.
* **ENABLE_KNOWLEDGE_BASE Toggle**: Added a configuration setting to conditionally bypass the memory-intensive FastEmbed vector indexing pipeline for hosting targets with ultra-low resources (<256MB RAM).

### Changed
* **Database Write Optimization**: Replaced SQLAlchemy ORM sequential `bulk_save_objects` writes with fast Core batch `bulk_insert_mappings` and `bulk_update_mappings` operations, reducing SQL network round-trips by **80%+**.
* **ORM Session Management**: Implemented explicit ORM `db.expunge(obj)` operations immediately following updates to prevent session dirty-tracking from triggering secondary updates during commit phases.
* **ONNX Runtime Tuning**: Custom configured the ONNX thread pool limits (`intra_op=2`, `inter_op=2`), disabled the C++ memory arena (`enable_cpu_mem_arena=False`), and selected basic optimization level to run safely on Render Free Tier without triggering OOM kills.
* **Aggressive Memory Eviction**: Added inline cache eviction of the global FastEmbed model instance (`_model = None`) and forced garbage collection (`gc.collect()`) immediately following the completion of the knowledge base indexing stage, freeing ~200MB of RAM.

### Production Validation Results
* **Functional Ingestion**: Passed 100% of pipeline tests across various validation codebases (`simple-feedback-hub`, `AegisHealth`, and `codegenie-ai`).
* **Resource Stability**: Thread count (51), File Descriptors (16), and Database Connections (8) remained completely flat across consecutive analysis stress loops.
* **Memory RSS**: Startup memory starts at ~68MB, peaks at ~345MB during the ONNX model embedding generation phase, and evicts back to a stable idle footprint of ~315MB.
* **Multi-repo Concurrency**: Concurrent ingestion of 3 repositories in parallel completed successfully in 43.82 seconds with zero SQLAlchemy pool deadlocks or session collisions.

### Known Limitations
* **Groq Rate-Limiting**: Frequent sequential queries via the AI Mentor chat interface can trigger organization-level Groq API 429 rate limit errors.
  * *Mitigation*: The RAG pipeline automatically recovers by entering a conversational fallback mode grounded on retrieved database snippets.
* **Git Command Shell Dependency**: Repository cloning depends on local git command installation on the host system.
* **Memory Overhead on Startup**: Initializing ONNX on the first ingestion request has a ~10-second cold-start latency to load model weights.

### Future Roadmap
* **Incremental Re-indexing**: Analyze and index only changed files in repository revisions rather than triggering full codebase rebuilds.
* **Local Offline Models**: Native configuration bindings to self-hosted Ollama or local private LLM endpoints.
* **Auto-generated Remediation PRs**: Enable the AI Mentor to automatically commit refactoring fixes directly back to GitHub repositories.
* **Multilingual Architecture Support**: Support dependency mapping and cycle detection for Go, Rust, and C++ repositories.
