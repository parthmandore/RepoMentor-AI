import os
import re
import shutil
import subprocess
from app.core.config import settings

class IngestionError(Exception):
    pass

def validate_github_url(url: str) -> bool:
    regex = r"^https?://(www\.)?github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(\.git)?/?$"
    return bool(re.match(regex, url.strip()))

def clone_repository(url: str, dest_path: str) -> str:
    """
    Clones a public GitHub repository using a shallow git clone command.
    Includes exponential backoff retry strategy and configurable timeout.
    Raises IngestionError if it fails, ensuring any incomplete files are purged.
    """
    import time
    if not validate_github_url(url):
        raise IngestionError(f"Invalid GitHub repository URL: {url}")

    # Remove destination folder if it pre-exists to start fresh
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path, ignore_errors=True)

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    max_retries = getattr(settings, "GIT_CLONE_RETRIES", 3)
    timeout_sec = getattr(settings, "GIT_CLONE_TIMEOUT", 120)
    
    cmd = [
        "git", "clone",
        "--depth", "1",
        "--single-branch",
        "--no-tags",
        "--shallow-submodules",
        "--no-recurse-submodules",
        "--filter=blob:none",
        url,
        dest_path
    ]
    
    # Skip LFS and credential prompts
    clone_env = {
        **os.environ,
        "GIT_LFS_SKIP_SMUDGE": "1",
        "GIT_TERMINAL_PROMPT": "0"
    }
    
    last_err = ""
    for attempt in range(1, max_retries + 1):
        try:
            # Clean up path before each attempt
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path, ignore_errors=True)
            
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
            backoff_sec = 2 ** attempt
            time.sleep(backoff_sec)
            
    # Clean up destination directory on final failure
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path, ignore_errors=True)
    raise IngestionError(f"All clone attempts failed. Last error: {last_err}")
