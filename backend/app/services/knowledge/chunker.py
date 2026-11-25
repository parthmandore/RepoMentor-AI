import os
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

def should_skip_file(path: str, extension: str, size_bytes: int, content: str) -> tuple[bool, str]:
    """
    General guard to filter files that offer zero or negative semantic code value.
    Detects empty files, placeholder dotfiles, large data dumps, CSVs, SQL dumps,
    binary assets, and minified bundles.
    """
    fn = path.lower().split('/')[-1]
    
    # 1. Empty files or empty text content or null bytes
    if size_bytes == 0 or not content.strip():
        return True, "Empty file (0 bytes)"
    if "\x00" in content:
        return True, "Contains null bytes (binary file)"
        
    # 2. Placeholder dotfiles
    if fn in {".gitkeep", ".keep", ".touch", ".placeholder"} or (fn.startswith(".") and size_bytes < 50):
        return True, "Placeholder dotfile"
        
    # 3. Package lockfiles
    if fn in {
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "cargo.lock",
        "poetry.lock", "go.sum", "composer.lock", "pipfile.lock", "mix.lock"
    }:
        return True, "Package lockfile"
        
    # 4. Assets, audio, video & graphics
    ext = extension.lower() if extension else ""
    if ext in {
        ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".otf",
        ".map", ".webp", ".avif", ".bmp", ".tiff", ".wav", ".mp3", ".ogg", ".flac", ".aac",
        ".m4a", ".webm", ".avi", ".mov", ".mp4", ".mkv", ".zip", ".tar", ".gz", ".rar", ".7z"
    }:
        return True, "Asset / media / audio / binary file"
        
    # 5. Data dumps, tables, binary datasets, model weights
    if ext in {".csv", ".tsv", ".parquet", ".arrow", ".feather", ".dat", ".h5", ".pkl", ".bin", ".onnx", ".pt", ".pth"}:
        return True, "Data / binary dataset"
        
    # 6. Minified production bundles
    if ".min." in fn or "-min." in fn:
        return True, "Minified production bundle"
        
    # 7. SQL database dumps: only skip if clearly a massive dump (>512 KB or >100 INSERT rows)
    if ext == ".sql":
        insert_count = len(re.findall(r'(?i)\binsert\s+into\b', content))
        if size_bytes > 512 * 1024 or insert_count > 100:
            return True, f"SQL data dump ({size_bytes // 1024} KB, {insert_count} inserts)"
        
    # 8. Large data JSON files
    if ext == ".json" and fn not in {"package.json", "tsconfig.json", "docker-compose.yml"} and size_bytes > 50 * 1024:
        return True, "Large data JSON (>50 KB)"
        
    # 9. Maximum general file size guard (256 KB) - except .ipynb which is parsed and pruned
    if size_bytes > 256 * 1024 and ext != ".ipynb":
        return True, f"File exceeds 256 KB max limit ({size_bytes // 1024} KB)"
        
    # 10. Test mocks and fixtures
    path_lower = path.lower()
    if "/mocks/" in path_lower or "/fixtures/" in path_lower or "__mocks__" in path_lower:
        return True, "Test mock / fixture"

    return False, ""

def chunk_jupyter_notebook(
    file_path: str,
    content: str,
    repo_id: str,
    max_chunks: int = 20,
    truncated_files: list = None
) -> List[Dict[str, Any]]:
    """
    Parses a Jupyter Notebook (.ipynb) JSON:
    - Extracts only code cells and markdown narrative cells.
    - Completely drops all cell outputs (text outputs, error traces, base64 images, PNGs, plots).
    - Formats code cells as clean Python code with execution cell headers.
    - Merges related consecutive short cells to maintain logical context.
    - Enforces a max_chunks ceiling per notebook.
    """
    chunks = []
    try:
        nb = json.loads(content)
    except Exception as e:
        return chunks

    cells = nb.get("cells", [])
    if not cells:
        return chunks

    # Determine kernel language
    lang = "Python"
    kernelspec = nb.get("metadata", {}).get("kernelspec", {})
    lang_info = nb.get("metadata", {}).get("language_info", {})
    if kernelspec.get("language"):
        lang = kernelspec["language"].capitalize()
    elif lang_info.get("name"):
        lang = lang_info["name"].capitalize()

    code_blocks = []
    md_blocks = []

    for idx, cell in enumerate(cells):
        cell_type = cell.get("cell_type")
        source = cell.get("source", [])
        if isinstance(source, list):
            cell_text = "".join(source).strip()
        else:
            cell_text = str(source).strip()

        if not cell_text:
            continue

        if cell_type == "code":
            code_blocks.append((idx + 1, cell_text))
        elif cell_type == "markdown":
            md_blocks.append((idx + 1, cell_text))

    # 1. Chunk code cells (merge short consecutive code cells up to ~1,800 chars)
    current_group = []
    current_chars = 0
    start_cell_num = 1

    for cell_num, code_text in code_blocks:
        if not current_group:
            start_cell_num = cell_num

        cell_len = len(code_text)
        if current_chars + cell_len > 1800 and current_group:
            merged_content = f"// File: {file_path} (Jupyter Notebook)\n// Language: {lang}\n// Cells: In[{start_cell_num}] - In[{cell_num - 1}]\n\n" + "\n\n".join(current_group)
            add_chunk({
                "chunk_id": str(uuid.uuid4()),
                "document_id": str(uuid.uuid4()),
                "repo_id": repo_id,
                "source_phase": "Phase 3: Deterministic Analysis Engine",
                "document_type": "Code Structure",
                "file_path": file_path,
                "language": lang,
                "module_type": "Notebook",
                "chunk_type": "Notebook Code",
                "start_line": start_cell_num,
                "end_line": cell_num - 1,
                "content": merged_content
            }, chunks)
            current_group = [f"# In[{cell_num}]:\n{code_text}"]
            current_chars = cell_len
            start_cell_num = cell_num
        else:
            current_group.append(f"# In[{cell_num}]:\n{code_text}")
            current_chars += cell_len

    if current_group:
        end_cell_num = code_blocks[-1][0] if code_blocks else start_cell_num
        merged_content = f"// File: {file_path} (Jupyter Notebook)\n// Language: {lang}\n// Cells: In[{start_cell_num}] - In[{end_cell_num}]\n\n" + "\n\n".join(current_group)
        add_chunk({
            "chunk_id": str(uuid.uuid4()),
            "document_id": str(uuid.uuid4()),
            "repo_id": repo_id,
            "source_phase": "Phase 3: Deterministic Analysis Engine",
            "document_type": "Code Structure",
            "file_path": file_path,
            "language": lang,
            "module_type": "Notebook",
            "chunk_type": "Notebook Code",
            "start_line": start_cell_num,
            "end_line": end_cell_num,
            "content": merged_content
        }, chunks)

    # 2. Chunk markdown cells (narrative / documentation)
    if md_blocks:
        md_text = "\n\n".join([f"### Cell {c_num}\n{m_text}" for c_num, m_text in md_blocks])
        if len(md_text) > 100:
            md_chunks = chunk_text(md_text, chunk_size=1500, overlap=200)
            for m_idx, m_sub in enumerate(md_chunks):
                add_chunk({
                    "chunk_id": str(uuid.uuid4()),
                    "document_id": str(uuid.uuid4()),
                    "repo_id": repo_id,
                    "source_phase": "Phase 2: Repository Ingestion Pipeline",
                    "document_type": "Documentation",
                    "file_path": file_path,
                    "language": "Markdown",
                    "module_type": "Notebook",
                    "chunk_type": "Notebook Documentation",
                    "start_line": 1,
                    "end_line": max(1, m_sub["content"].count("\n") + 1),
                    "content": f"// File: {file_path} (Notebook Markdown)\n{m_sub['content']}"
                }, chunks)

    # Enforce maximum chunks cap per notebook
    if len(chunks) > max_chunks:
        dropped = len(chunks) - max_chunks
        if truncated_files is not None:
            truncated_files.append({
                "path": file_path,
                "reason": f"Notebook capped at {max_chunks} chunks ({dropped} dropped)",
                "total_chunks": len(chunks),
                "retained_chunks": max_chunks,
                "dropped_chunks": dropped
            })
        chunks = chunks[:max_chunks]

    return chunks

def chunk_repository(
    files_metadata: List[Dict[str, Any]],
    file_contents: Dict[str, str],
    evidence_docs: List[Dict[str, Any]],
    repo_id: str,
    truncated_files: list = None
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
            "chunk_type": "evidence",
            "start_line": None,
            "end_line": None,
            "content": chunk_content
        }, chunks)
        
    # 2. Chunk Source Files
    for file_meta in files_metadata:
        path = file_meta["path"]
        ext = file_meta.get("extension", "").lower()
        
        # Skip stylesheets, asset lists, media, audio, minified files (Smart File Filtering)
        if ext in {
            ".css", ".scss", ".sass", ".less", ".map", ".ico", ".png", ".jpg", ".jpeg",
            ".gif", ".svg", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".wav", ".mp3",
            ".ogg", ".flac", ".aac", ".m4a", ".webm", ".avi", ".mov", ".mp4", ".mkv",
            ".zip", ".tar", ".gz", ".rar", ".7z", ".pdf", ".bin"
        }:
            continue
            
        path_lower = path.lower()
        if "test" in path_lower or "spec" in path_lower or "/test/" in path_lower or "/tests/" in path_lower or "mocks" in path_lower:
            continue
            
        content = file_contents.get(path, "")
        if not content:
            continue
            
        if is_low_semantic_value_file(path, content):
            continue
            
        # Check general skip guard
        skip, skip_reason = should_skip_file(path, ext, file_meta.get("size_bytes", len(content)), content)
        if skip:
            continue

        # Jupyter Notebooks (.ipynb)
        if ext == ".ipynb":
            nb_chunks = chunk_jupyter_notebook(path, content, repo_id, max_chunks=20, truncated_files=truncated_files)
            chunks.extend(nb_chunks)
            continue

        lang = "Python" if ext == ".py" else "TypeScript" if ext in {".ts", ".tsx"} else "JavaScript" if ext in {".js", ".jsx"} else "Text"
        module_type = file_meta.get("module_type", "Unknown")
        
        filename = path.lower().split("/")[-1]
        file_chunks_start = len(chunks)
        
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

        # Enforce safety cap: 20 chunks for data-like files (JSON, CSV, SQL, SVG, XML, TXT); 100 for code
        is_data_file = ext in (".json", ".csv", ".sql", ".tsv", ".xml", ".txt")
        cap_limit = 20 if is_data_file else 100

        raw_count = len(chunks) - file_chunks_start
        if raw_count > cap_limit:
            dropped = raw_count - cap_limit
            if truncated_files is not None:
                truncated_files.append({
                    "path": path,
                    "reason": f"Data file safety cap ({dropped} dropped)" if is_data_file else f"Large file safety cap at {cap_limit} chunks ({dropped} dropped)",
                    "total_chunks": raw_count,
                    "retained_chunks": cap_limit,
                    "dropped_chunks": dropped
                })
            file_chunks = chunks[file_chunks_start:file_chunks_start + cap_limit]
            chunks = chunks[:file_chunks_start] + file_chunks

    # Inject file_hash metadata to all non-Evidence chunks
    hash_by_path = {f["path"]: f.get("content_hash", "") for f in files_metadata}
    for chunk in chunks:
        if chunk.get("chunk_type", "").lower() != "evidence" and chunk.get("file_path") in hash_by_path:
            meta = chunk.get("metadata") or {}
            meta["file_hash"] = hash_by_path[chunk["file_path"]]
            chunk["metadata"] = meta

    return chunks

def is_priority_1_chunk(chunk: Dict[str, Any]) -> bool:
    """
    Classifies whether a chunk belongs to Priority 1 (indexed first to unblock Mentor immediately):
    - Evidence docs
    - README files
    - Entry points (main.py, app.py, *Application.java, index.ts, server.js, main.go, app.java)
    - Controllers & API routes (*Controller.java, routes.py, /api/, controller/, routes/)
    - Services & Core business logic (*Service.java, service/, services/, notebook code cells In[...])
    - Core models & entities (*Entity.java, model/, models/, entity/, entities/, schema/)
    """
    chunk_type = chunk.get("chunk_type", "")
    if chunk_type.lower() == "evidence":
        return True
    
    path = (chunk.get("file_path") or "").lower()
    
    if "readme" in path or chunk_type == "README":
        return True
        
    fn = os.path.basename(path).lower()
    
    # Entry points
    entry_patterns = ["main.py", "app.py", "application.java", "index.ts", "index.js", "server.js", "server.ts", "main.go", "app.java"]
    if any(ep in fn for ep in entry_patterns) or fn.endswith("application.java"):
        return True
        
    # Auth, Security & Access Control
    if "auth" in path or "login" in path or "security" in path:
        return True

    # Controllers & Routes
    if "controller" in path or "route" in path or "/api/" in path or "endpoints" in path:
        return True
        
    # Services & Core logic
    if "service" in path or path.endswith(".ipynb") or chunk_type == "Notebook Code":
        return True
        
    # Entities, Models, Repositories
    if "entity" in path or "model" in path or "schema" in path or "repository" in path or "repo" in path:
        return True
        
    return False

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
        return list(chunks)
        
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
