import os
import hashlib
from typing import Dict, List, Tuple

# Folders to skip during parsing
SKIP_FOLDERS = {
    ".git", "node_modules", "build", "dist", "vendor", "__pycache__", ".next",
    ".vscode", ".idea", "out", "target", "bin", "obj", "coverage", ".svelte-kit", ".nuxt"
}

def is_text_file(file_path: str) -> bool:
    """Detects if a file is a text file by reading the first 1024 bytes and checking for null bytes."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return False
            try:
                chunk.decode("utf-8")
                return True
            except UnicodeDecodeError:
                # Fallback check for Latin-1 (commonly used in legacy text files)
                chunk.decode("latin-1")
                return True
    except Exception:
        return False

def calculate_sha256(file_path: str) -> str:
    """Computes the SHA-256 hash of a file's content in chunks to preserve memory."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return "unknown_hash"

def parse_repository(root_path: str) -> Tuple[List[Dict], Dict, Dict[str, str]]:
    """
    Walks the cloned repository structure, compiles structural statistics, and reads text contents.
    Returns:
      - List of file metadata dicts
      - Dict containing statistics (total_files, total_folders, text_file_count, binary_file_count)
      - Dict of relative paths mapping to text content string
    """
    files_metadata = []
    file_contents = {}
    
    total_files = 0
    total_folders = 0
    text_file_count = 0
    binary_file_count = 0

    root_path = os.path.abspath(root_path)

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Skip forbidden/generated directories in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_FOLDERS]
        
        # Count current directory as a folder (excluding the root directory itself)
        if dirpath != root_path:
            total_folders += 1
            
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(file_path, root_path).replace("\\", "/")
            
            size_bytes = 0
            try:
                size_bytes = os.path.getsize(file_path)
            except OSError:
                continue

            _, ext = os.path.splitext(filename)
            ext = ext.lower() if ext else ""

            # Skip lock files, compiled binaries, media, archives, and web assets
            filename_lower = filename.lower()
            if filename_lower in {
                "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock",
                "cargo.lock", "poetry.lock", "mix.lock", "pipfile.lock"
            }:
                continue

            if ext in {
                ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".mp4", ".zip",
                ".tar.gz", ".tar", ".gz", ".rar", ".pdf", ".woff", ".woff2", ".ttf",
                ".eot", ".exe", ".dll", ".so", ".dylib", ".class", ".pyc", ".pyo",
                ".db", ".sqlite", ".war", ".ear", ".jar", ".map", ".css", ".scss",
                ".sass", ".less"
            }:
                continue

            is_txt = False
            content_str = ""
            content_hash = "unknown_hash"
            
            if size_bytes < 10 * 1024 * 1024:  # Under 10MB limit
                try:
                    with open(file_path, "rb") as f:
                        raw_data = f.read()
                    content_hash = hashlib.sha256(raw_data).hexdigest()
                    if b"\x00" not in raw_data[:1024]:
                        try:
                            content_str = raw_data.decode("utf-8")
                            is_txt = True
                        except UnicodeDecodeError:
                            try:
                                content_str = raw_data.decode("latin-1")
                                is_txt = True
                            except Exception:
                                pass
                except Exception:
                    pass

            files_metadata.append({
                "path": rel_path,
                "extension": ext,
                "size_bytes": size_bytes,
                "content_hash": content_hash,
                "is_text": is_txt
            })

            if is_txt:
                file_contents[rel_path] = content_str
                text_file_count += 1
            else:
                binary_file_count += 1
                
            total_files += 1

    stats = {
        "total_files": total_files,
        "total_folders": total_folders,
        "text_file_count": text_file_count,
        "binary_file_count": binary_file_count
    }

    return files_metadata, stats, file_contents
