import os
import re
import stat
import shutil
import tarfile
import logging
import requests
import subprocess
from app.core.config import settings

logger = logging.getLogger(__name__)

# Security & Bounded Resource Limits
MAX_SINGLE_FILE_SIZE = 25 * 1024 * 1024  # 25 MB max per file
MAX_TOTAL_ARCHIVE_SIZE = 250 * 1024 * 1024  # 250 MB total extraction limit
TAR_CHUNK_SIZE = 64 * 1024  # 64 KB streaming buffer

class IngestionError(Exception):
    pass

def validate_github_url(url: str) -> bool:
    """Validates if the provided string is a valid GitHub repository URL."""
    regex = r"^https?://(?:www\.)?github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(?:\.git)?/?$"
    return bool(re.match(regex, url.strip()))

def parse_github_owner_repo(url: str) -> tuple[str, str] | None:
    """Extracts (owner, repo) from a GitHub repository URL."""
    regex = r"^https?://(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$"
    match = re.match(regex, url.strip())
    if match:
        owner = match.group(1)
        repo = match.group(2)
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo
    return None

def _handle_readonly(func, path, exc_info):
    """Callback for shutil.rmtree to clear read-only file attributes."""
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IWUSR)
        func(path)
    except Exception:
        pass

def safe_clean_dir(path: str) -> None:
    """
    Safely and reliably purges a directory across both Linux and Windows in a platform-neutral way.
    Clears read-only flags and avoids shell or cmd.exe subprocesses.
    """
    if not os.path.exists(path):
        return

    # Attempt 1: Standard shutil.rmtree with read-only handler
    try:
        shutil.rmtree(path, onerror=_handle_readonly)
        return
    except Exception as e:
        logger.debug(f"Initial shutil.rmtree pass on {path}: {e}")

    # Attempt 2: Walk directory bottom-up, clear read-only, remove files and subdirectories
    if os.path.exists(path):
        try:
            for root, dirs, files in os.walk(path, topdown=False):
                for fname in files:
                    file_p = os.path.join(root, fname)
                    try:
                        os.chmod(file_p, stat.S_IWRITE | stat.S_IWUSR)
                        os.unlink(file_p)
                    except Exception:
                        pass
                for dname in dirs:
                    dir_p = os.path.join(root, dname)
                    try:
                        os.rmdir(dir_p)
                    except Exception:
                        pass
            if os.path.exists(path):
                os.rmdir(path)
        except Exception as e:
            logger.warning(f"Platform-neutral directory cleanup encountered error on {path}: {e}")

def _is_safe_tar_member(member: tarfile.TarInfo, dest_path: str) -> tuple[bool, str]:
    """
    Validates a tar archive entry against path traversal, symlink attacks, and unsafe types.
    Returns (is_safe, relative_target_path).
    """
    # Reject dangerous types: symlinks, hardlinks, FIFOs, block/char devices
    if member.issym() or member.islnk() or member.ischr() or member.isblk() or member.isfifo():
        return False, ""

    raw_name = member.name.replace("\\", "/")
    # Reject absolute root paths immediately
    if raw_name.startswith("/") or raw_name.startswith("\\") or os.path.isabs(member.name):
        return False, ""

    # GitHub tarballs prefix files with '{repo}-{commit}/'. Strip top-level directory prefix.
    parts = raw_name.split("/", 1)
    if len(parts) <= 1 or not parts[1]:
        return False, ""  # The top-level root directory itself

    rel_subpath = parts[1]
    norm_path = os.path.normpath(rel_subpath)

    # Path traversal rejection: reject parent directory traversals ('..') and absolute paths
    if norm_path.startswith("..") or os.path.isabs(norm_path) or norm_path.startswith("/") or norm_path.startswith("\\"):
        return False, ""

    # Ensure resolved path is strictly within dest_path boundary
    dest_abs = os.path.abspath(dest_path)
    target_abs = os.path.abspath(os.path.join(dest_abs, norm_path))
    if not target_abs.startswith(dest_abs + os.sep) and target_abs != dest_abs:
        return False, ""

    return True, norm_path

def download_and_extract_archive(owner: str, repo: str, dest_path: str, timeout_sec: int = 60) -> tuple[str, str]:
    """
    Downloads and extracts a GitHub repository tarball incrementally via streaming.
    Memory usage is strictly bounded (O(1) buffer size, ~64 KB).
    Returns (dest_path, commit_hash).
    """
    safe_clean_dir(dest_path)
    os.makedirs(dest_path, exist_ok=True)

    # Endpoints to try (HEAD archive automatically resolves the repository's default branch)
    candidate_urls = [
        f"https://github.com/{owner}/{repo}/archive/HEAD.tar.gz",
        f"https://api.github.com/repos/{owner}/{repo}/tarball"
    ]

    session = requests.Session()
    req_headers = {
        "User-Agent": "RepoMentor-AI-Ingestion/1.0",
        "Accept": "application/vnd.github.v3+json, application/x-gzip, */*"
    }

    last_error = ""
    for archive_url in candidate_urls:
        try:
            logger.info(f"Connecting to repository archive stream at {archive_url}...")
            response = session.get(
                archive_url,
                stream=True,
                headers=req_headers,
                timeout=(10.0, timeout_sec),
                allow_redirects=True
            )

            if response.status_code == 404:
                last_error = f"Repository {owner}/{repo} not found or is private (HTTP 404)."
                continue
            if response.status_code == 403:
                last_error = f"GitHub API rate limit or access denied for {owner}/{repo} (HTTP 403)."
                continue
            if response.status_code != 200:
                last_error = f"HTTP {response.status_code} while fetching archive."
                continue

            # Extract commit hash from final redirected URL if available (e.g., .../tar.gz/<hash>)
            commit_hash = None
            if response.url:
                hash_match = re.search(r"/(?:tar\.gz|legacy\.tar\.gz)/([a-fA-F0-9]{40})", response.url)
                if hash_match:
                    commit_hash = hash_match.group(1)

            # Streamingly unpack tar archive
            raw_stream = response.raw
            raw_stream.decode_content = True  # Ensure transparent gzip decompression

            total_extracted_bytes = 0
            file_count = 0

            with tarfile.open(mode="r|*", fileobj=raw_stream) as tar_stream:
                for member in tar_stream:
                    # Capture commit hash from root folder prefix if not yet determined
                    if not commit_hash and "/" in member.name:
                        root_prefix = member.name.split("/")[0]
                        prefix_match = re.search(r"-([a-fA-F0-9]{40})$", root_prefix)
                        if prefix_match:
                            commit_hash = prefix_match.group(1)

                    is_safe, rel_path = _is_safe_tar_member(member, dest_path)
                    if not is_safe:
                        continue

                    target_file = os.path.join(dest_path, rel_path)

                    if member.isdir():
                        os.makedirs(target_file, exist_ok=True)
                    elif member.isfile():
                        if member.size > MAX_SINGLE_FILE_SIZE:
                            logger.warning(f"Skipping oversized file in archive: {rel_path} ({member.size} bytes)")
                            continue

                        if total_extracted_bytes + member.size > MAX_TOTAL_ARCHIVE_SIZE:
                            raise IngestionError(
                                f"Repository exceeds total extraction size limit ({MAX_TOTAL_ARCHIVE_SIZE // (1024 * 1024)} MB)"
                            )

                        if file_count >= 10000:
                            raise IngestionError(
                                "Repository exceeds size limits for rapid analysis (>10,000 files). Please submit a repository or submodule under 10,000 files."
                            )

                        os.makedirs(os.path.dirname(target_file), exist_ok=True)
                        f_in = tar_stream.extractfile(member)
                        if f_in:
                            with open(target_file, "wb") as f_out:
                                shutil.copyfileobj(f_in, f_out, length=TAR_CHUNK_SIZE)
                            total_extracted_bytes += member.size
                            file_count += 1

            logger.info(f"Stream extraction complete: {file_count} files ({total_extracted_bytes / (1024 * 1024):.2f} MB) extracted to {dest_path}")
            return dest_path, commit_hash or ""

        except IngestionError:
            safe_clean_dir(dest_path)
            raise
        except Exception as e:
            last_error = f"Archive download/extraction failed for {archive_url}: {str(e)}"
            logger.warning(last_error)
            safe_clean_dir(dest_path)

    raise IngestionError(f"Unable to download repository archive. Last error: {last_error}")

def clone_repository(url: str, dest_path: str) -> str:
    """
    Downloads and extracts a public GitHub repository.
    First attempts bounded-memory HTTP tarball streaming.
    Falls back to shallow git clone if HTTP archive endpoints fail.
    """
    import time

    if not validate_github_url(url):
        raise IngestionError(f"Invalid GitHub repository URL: {url}")

    parsed = parse_github_owner_repo(url)
    timeout_sec = getattr(settings, "GIT_CLONE_TIMEOUT", 120)

    # 1. Primary Strategy: Bounded-Memory Tarball Stream
    if parsed:
        owner, repo = parsed
        try:
            dest, _ = download_and_extract_archive(owner, repo, dest_path, timeout_sec=min(timeout_sec, 60))
            if os.path.exists(dest) and os.listdir(dest):
                return dest
        except Exception as e:
            logger.warning(f"Streaming archive download failed ({e}), falling back to git clone...")

    # 2. Fallback Strategy: Shallow Git Clone
    safe_clean_dir(dest_path)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    max_retries = getattr(settings, "GIT_CLONE_RETRIES", 3)
    cmd = [
        "git", "clone",
        "--depth", "1",
        "--single-branch",
        "--no-tags",
        "--shallow-submodules",
        "--no-recurse-submodules",
        url,
        dest_path
    ]

    clone_env = {
        **os.environ,
        "GIT_LFS_SKIP_SMUDGE": "1",
        "GIT_TERMINAL_PROMPT": "0"
    }

    last_err = ""
    for attempt in range(1, max_retries + 1):
        try:
            safe_clean_dir(dest_path)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                env=clone_env
            )
            if result.returncode == 0:
                return dest_path

            err_msg = result.stderr.strip() if result.stderr else "Git clone return code non-zero"
            last_err = f"Attempt {attempt}/{max_retries} failed: {err_msg}"
        except subprocess.TimeoutExpired:
            last_err = f"Attempt {attempt}/{max_retries} timed out after {timeout_sec}s"
        except Exception as e:
            last_err = f"Attempt {attempt}/{max_retries} error: {str(e)}"

        if attempt < max_retries:
            time.sleep(2 ** attempt)

    safe_clean_dir(dest_path)
    raise IngestionError(f"All repository ingestion attempts failed. Last error: {last_err}")
