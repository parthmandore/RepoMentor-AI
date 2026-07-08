import uuid
import re
import json
from typing import List, Dict, Any

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[Dict[str, Any]]:
    """Splits flat text into overlapping chunks."""
    chunks = []
    if not text:
        return chunks
        
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_content = text[start:end]
        chunks.append({
            "content": chunk_content,
            "start_idx": start,
            "end_idx": end
        })
        if end >= len(text):
            break
        step = chunk_size - overlap
        if step <= 0:
            step = chunk_size
        start += step
    return chunks

def add_chunk(chunk: Dict[str, Any], chunks_list: List[Dict[str, Any]]) -> None:
    """
    Enforces a strict upper bound on vector chunk size (3000 chars / ~750 tokens).
    Splits large chunks to ensure fast local embedding inference and prevent context limits.
    """
    content = chunk["content"]
    max_chars = 3000
    if len(content) <= max_chars:
        chunks_list.append(chunk)
        return
        
    # Split large chunk into smaller segments
    sub_chunks = chunk_text(content, chunk_size=2000, overlap=300)
    for idx, sub in enumerate(sub_chunks):
        sub_chunk = chunk.copy()
        sub_chunk["chunk_id"] = f"{chunk['chunk_id']}_{idx}"
        sub_chunk["content"] = sub["content"]
        # Estimate sub-chunk line numbers
        lines_before = content[:sub["start_idx"]].count("\n")
        lines_in_sub = sub["content"].count("\n")
        sub_chunk["start_line"] = chunk["start_line"] + lines_before
        sub_chunk["end_line"] = sub_chunk["start_line"] + lines_in_sub
        chunks_list.append(sub_chunk)

def is_low_semantic_value_file(path: str, content: str) -> bool:
    """
    Checks if a file is an export-only or boilerplate-only file that has
    almost zero semantic code value for recruiter mentoring.
    """
    # Skip configurations that are not core to deployment
    ext = path.lower().split(".")[-1]
    if ext in ("json", "yaml", "yml"):
        filename = path.lower().split("/")[-1]
        if filename not in {"package.json", "docker-compose.yml", "tsconfig.json"}:
            return True
            
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return True
        
    # Check if it only contains imports and exports (index files)
    all_imports_exports = True
    for line in lines:
        if not (line.startswith("import ") or line.startswith("export ") or 
                line.startswith("} from ") or line == "}" or 
                line.startswith("/*") or line.startswith("*") or 
                line.startswith("//") or line.startswith("export default")):
            all_imports_exports = False
            break
            
    return all_imports_exports

def chunk_repository(
    files_metadata: List[Dict[str, Any]],
    file_contents: Dict[str, str],
    evidence_docs: List[Dict[str, Any]],
    repo_id: str
) -> List[Dict[str, Any]]:
    chunks = []
    
    # 1. Chunk Evidence Documents (single chunk per doc to keep context together)
    for doc in evidence_docs:
        chunk_content = f"Title: {doc['title']}\nType: {doc['document_type']}\nSummary: {doc['summary']}\nEvidence: {doc['evidence']}\nPhase: {doc['source_phase']}"
        add_chunk({
            "chunk_id": str(uuid.uuid4()),
            "document_id": doc["document_id"],
            "repo_id": repo_id,
            "source_phase": doc["source_phase"],
            "document_type": doc["document_type"],
            "file_path": doc["source_file"],
            "language": "Text",
            "module_type": "Unknown",
            "chunk_type": "Evidence",
            "start_line": 1,
            "end_line": 1,
            "content": chunk_content
        }, chunks)
        
    # 2. Chunk Source Files
    for file_meta in files_metadata:
        path = file_meta["path"]
        ext = file_meta.get("extension", "").lower()
        
        # Skip stylesheets, asset lists, minified files (Smart File Filtering)
        if ext in {".css", ".scss", ".sass", ".less", ".map", ".ico", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".woff", ".woff2", ".ttf", ".eot"}:
            continue
            
        path_lower = path.lower()
        if "test" in path_lower or "spec" in path_lower or "/test/" in path_lower or "/tests/" in path_lower or "mocks" in path_lower:
            continue
            
        content = file_contents.get(path, "")
        if not content:
            continue
            
        if is_low_semantic_value_file(path, content):
            continue
            
        lang = "Python" if ext == ".py" else "TypeScript" if ext in {".ts", ".tsx"} else "JavaScript" if ext in {".js", ".jsx"} else "Text"
        module_type = file_meta.get("module_type", "Unknown")
        
        filename = path.lower().split("/")[-1]
        
        # README files split by headers
        if filename == "readme.md":
            headers = content.split("\n#")
            for idx, h in enumerate(headers, 1):
                if not h.strip():
                    continue
                header_text = ("#" if idx > 1 else "") + h
                add_chunk({
                    "chunk_id": str(uuid.uuid4()),
                    "document_id": str(uuid.uuid4()),
                    "repo_id": repo_id,
                    "source_phase": "Phase 2: Repository Ingestion Pipeline",
                    "document_type": "Documentation",
                    "file_path": path,
                    "language": "Markdown",
                    "module_type": "Unknown",
                    "chunk_type": "README",
                    "start_line": 1,
                    "end_line": len(header_text.splitlines()),
                    "content": header_text.strip()
                }, chunks)
            continue

        # Skip lockfiles
        if filename in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"}:
            continue

        # Configuration files
        if filename in {"package.json", "requirements.txt", "docker-compose.yml", "dockerfile", ".env"}:
            add_chunk({
                "chunk_id": str(uuid.uuid4()),
                "document_id": str(uuid.uuid4()),
                "repo_id": repo_id,
                "source_phase": "Phase 2: Repository Ingestion Pipeline",
                "document_type": "Configuration",
                "file_path": path,
                "language": "Configuration",
                "module_type": "Configuration",
                "chunk_type": "Configuration",
                "start_line": 1,
                "end_line": len(content.splitlines()),
                "content": content.strip()
            }, chunks)
            continue
            
        # Small files whole-indexing
        if len(content) < 1500 or content.count("\n") < 100:
            add_chunk({
                "chunk_id": str(uuid.uuid4()),
                "document_id": str(uuid.uuid4()),
                "repo_id": repo_id,
                "source_phase": "Phase 3: Deterministic Analysis Engine",
                "document_type": "Code Structure",
                "file_path": path,
                "language": lang,
                "module_type": module_type,
                "chunk_type": "Whole File",
                "start_line": 1,
                "end_line": max(1, content.count("\n") + 1),
                "content": f"// File: {path}\n{content.strip()}"
            }, chunks)
            continue

        # Code chunks
        lines = content.splitlines()
        fn_cls_meta = file_meta.get("analysis_metadata") or {}
        functions = fn_cls_meta.get("functions") or []
        classes = fn_cls_meta.get("classes") or []
        
        # Filter out methods that are already fully contained inside small class chunks
        # to avoid excessive duplication of identical code chunks.
        non_class_methods = []
        for fn in functions:
            fn_start = fn.get("line", 1)
            fn_loc = fn.get("loc", 1)
            fn_end = fn_start + fn_loc
            
            is_inside_small_class = False
            for cls in classes:
                cls_start = cls.get("line", 1)
                cls_loc = cls.get("loc", 1)
                cls_end = cls_start + cls_loc
                # If function is inside class and class is small (<60 lines), class chunk captures it fully
                if cls_start <= fn_start and fn_end <= cls_end and cls_loc < 60:
                    is_inside_small_class = True
                    break
            if not is_inside_small_class:
                non_class_methods.append(fn)

        # Smart Function Filtering: filter trivial getters, setters, toString methods
        filtered_functions = []
        for fn in non_class_methods:
            name = fn.get("name", "")
            loc = fn.get("loc", 1)
            if loc <= 3 and (name.startswith("get") or name.startswith("set") or name in ("toString", "toJSON", "constructor")):
                continue
            filtered_functions.append(fn)
            
        # Adjacent Function Merging: sort by line number and group adjacent functions together
        filtered_functions.sort(key=lambda x: x.get("line", 1))
        merged_groups = []
        current_group = []
        
        for fn in filtered_functions:
            if not current_group:
                current_group.append(fn)
            else:
                last_fn = current_group[-1]
                last_end = last_fn.get("line", 1) + last_fn.get("loc", 1)
                curr_start = fn.get("line", 1)
                
                gap = curr_start - last_end
                total_loc = (fn.get("line", 1) + fn.get("loc", 1)) - current_group[0].get("line", 1)
                
                # Merge if gap is small and combined length is reasonable (<80 lines)
                if gap <= 15 and total_loc <= 80:
                    current_group.append(fn)
                else:
                    merged_groups.append(current_group)
                    current_group = [fn]
        if current_group:
            merged_groups.append(current_group)

        # Add function group chunks
        for group in merged_groups:
            start_l = max(1, group[0].get("line", 1))
            end_l = min(len(lines), group[-1].get("line", 1) + group[-1].get("loc", 1))
            group_content = "\n".join(lines[start_l-1:end_l])
            names = ", ".join([f.get("name", "") for f in group])
            
            add_chunk({
                "chunk_id": str(uuid.uuid4()),
                "document_id": str(uuid.uuid4()),
                "repo_id": repo_id,
                "source_phase": "Phase 3: Deterministic Analysis Engine",
                "document_type": "Code Structure",
                "file_path": path,
                "language": lang,
                "module_type": module_type,
                "chunk_type": "Merged Functions" if len(group) > 1 else "Function",
                "start_line": start_l,
                "end_line": end_l,
                "content": f"// File: {path}\n// Functions: {names}\n{group_content}"
            }, chunks)
            
        # Add class chunks
        for cls in classes:
            start_l = max(1, cls.get("line", 1))
            loc = cls.get("loc", 1)
            end_l = min(len(lines), start_l + loc)
            cls_content = "\n".join(lines[start_l-1:end_l])
            
            if loc >= 60:
                header_len = min(25, loc)
                header_content = "\n".join(lines[start_l-1:start_l-1+header_len])
                content_str = f"// File: {path}\n// Class: {cls.get('name')} (Header/Constructor)\n{header_content}\n// ... [Methods omitted, indexed separately]"
                chunk_type_str = "Class Header"
                end_l = start_l + header_len
            else:
                content_str = f"// File: {path}\n// Class: {cls.get('name')}\n{cls_content}"
                chunk_type_str = "Class"

            add_chunk({
                "chunk_id": str(uuid.uuid4()),
                "document_id": str(uuid.uuid4()),
                "repo_id": repo_id,
                "source_phase": "Phase 3: Deterministic Analysis Engine",
                "document_type": "Code Structure",
                "file_path": path,
                "language": lang,
                "module_type": module_type,
                "chunk_type": chunk_type_str,
                "start_line": start_l,
                "end_line": end_l,
                "content": content_str
            }, chunks)

        # Sliding window fallback only if no functions or classes were parsed
        if not functions and not classes:
            text_chunks = chunk_text(content, chunk_size=800, overlap=150)
            for t_chunk in text_chunks:
                start_char = t_chunk["start_idx"]
                end_char = t_chunk["end_idx"]
                start_l = content[:start_char].count("\n") + 1
                end_l = content[:end_char].count("\n") + 1
                
                add_chunk({
                    "chunk_id": str(uuid.uuid4()),
                    "document_id": str(uuid.uuid4()),
                    "repo_id": repo_id,
                    "source_phase": "Phase 3: Deterministic Analysis Engine",
                    "document_type": "Code Structure",
                    "file_path": path,
                    "language": lang,
                    "module_type": module_type,
                    "chunk_type": "Code Block",
                    "start_line": start_l,
                    "end_line": end_l,
                    "content": f"// File: {path}\n{t_chunk['content']}"
                }, chunks)

    # Inject file_hash metadata to all non-Evidence chunks
    hash_by_path = {f["path"]: f.get("content_hash", "") for f in files_metadata}
    for chunk in chunks:
        if chunk.get("chunk_type") != "Evidence" and chunk.get("file_path") in hash_by_path:
            meta = chunk.get("metadata") or {}
            meta["file_hash"] = hash_by_path[chunk["file_path"]]
            chunk["metadata"] = meta

    return chunks

def compute_chunk_priority(chunk: Dict[str, Any], sec_issues: List[Dict[str, Any]]) -> float:
    """Computes a numeric priority score for a chunk to sort by value."""
    score = 0.0
    content = chunk.get("content", "").lower()
    path = chunk.get("file_path", "").lower()
    chunk_type = chunk.get("chunk_type", "")
    
    # 1. Tier 1: NEVER REMOVE (Priority >= 10.0)
    # README
    if chunk_type == "README" or path.endswith("readme.md"):
        score += 15.0
        
    # Security findings or matches
    has_sec_issue = False
    for issue in sec_issues:
        issue_path = issue.get("file_path", "").lower()
        if issue_path and (issue_path in path or path in issue_path):
            line = issue.get("line_number")
            start_l = chunk.get("start_line", 0)
            end_l = chunk.get("end_line", 999999)
            if line is not None and start_l <= line <= end_l:
                has_sec_issue = True
                break
                
    if has_sec_issue:
        score += 100.0  # Absolute must-keep
        
    # Content-based security matches (secrets, keys, tokens, auth bypasses)
    sec_keywords = {"api_key", "apikey", "secret", "password", "passwd", "token", "auth_token", "private_key"}
    if any(kw in content for kw in sec_keywords):
        score += 18.0
        
    # AI / RAG pipeline components
    ai_keywords = {"rag", "prompt", "embedding", "fastembed", "openai", "gemini", "groq", "llm", "expert", "inference", "voicecoach"}
    if any(kw in path for kw in ai_keywords) or any(kw in content for kw in ai_keywords):
        score += 12.0
        
    # Authentication flow
    auth_keywords = {"auth", "login", "signup", "register", "session", "jwt", "cookie", "keyring", "oauth", "middleware"}
    if any(kw in path for kw in auth_keywords) or any(kw in content for kw in auth_keywords):
        score += 11.5
        
    # Database Layer
    db_keywords = {"db", "database", "schema", "prisma", "typeorm", "sqlalchemy", "migration", "postgres", "mysql", "sqlite"}
    if any(kw in path for kw in db_keywords) or any(kw in content for kw in db_keywords):
        score += 11.0
        
    # API Routes
    api_keywords = {"api/", "route.ts", "controller", "router", "handler"}
    if any(kw in path for kw in api_keywords):
        score += 10.5
        
    # Core entry points / configurations
    core_configs = {"dockerfile", "docker-compose.yml", "package.json", "requirements.txt", "next.config"}
    filename = path.split("/")[-1]
    if filename in core_configs:
        score += 10.0
        
    # GymBuddy Cores
    gymbuddy_cores = {
        "workoutsession.tsx", "workoutplayer.tsx", "useframeprocessor.ts", 
        "adaptiveengine.ts", "angletracker.ts", "trajectorytracker.ts", 
        "positiontracker.ts", "ruleengine.ts", "statemachine.ts", "actionhandler.ts"
    }
    if filename in gymbuddy_cores:
        score += 10.0
        
    # 2. Tier 2: KEEP WHEN POSSIBLE (Priority 5.0 to 9.0)
    if "src/" in path or "app/" in path:
        score += 5.0
        
    if chunk_type in ("Class", "Function", "Whole File", "Merged Functions"):
        score += 2.0
        # Boost for length/loc (indicates complex logic)
        loc = chunk.get("end_line", 0) - chunk.get("start_line", 0)
        if loc > 50:
            score += 1.5
        elif loc > 20:
            score += 0.8
            
    if "shared" in path or "components/" in path or "lib/" in path:
        score += 1.0
        
    # 3. Tier 3: REMOVE FIRST (Priority < 5.0)
    if len(chunk.get("content", "")) < 200:
        score -= 3.0
        
    return score

def select_best_chunks(chunks: List[Dict[str, Any]], max_budget: int, sec_issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Intelligent global budget enforcement.
    Sorts all candidate chunks by priority score descending and keeps the top max_budget chunks.
    Security findings and core AI/auth/db components are heavily prioritized.
    """
    if len(chunks) <= max_budget:
        return chunks
        
    scored_chunks = []
    for chunk in chunks:
        score = compute_chunk_priority(chunk, sec_issues)
        scored_chunks.append((score, chunk))
        
    # Sort descending by priority score
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    selected = [x[1] for x in scored_chunks[:max_budget]]
    
    # Sort selected chunks back to chronological/file order to keep sequential logic
    selected.sort(key=lambda x: (x.get("file_path", ""), x.get("start_line", 0)))
    return selected
