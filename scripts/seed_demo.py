#!/usr/bin/env python3
"""
Seed Demo Repositories for RepoMentor AI
Runs the full ingestion and analysis pipeline for demo repositories listed in demo_repos.json
and ensures they are fully indexed in the production Supabase database.
"""
import os
import sys
import json
import time
import subprocess
import logging

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, backend_dir)

from app.db.session import SessionLocal
from app.models.repository import Repository, RepositoryStatus
from app.services.ingestion.pipeline import ingest_repository

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_demo")

def get_remote_head_hash(url: str) -> str:
    """Gets the latest commit hash from GitHub remote."""
    try:
        res = subprocess.run(
            ["git", "ls-remote", url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.split()[0].strip()
    except Exception as e:
        logger.warning(f"Could not fetch remote HEAD for {url}: {e}")
    return ""

def seed_demo_repos(config_path: str = None):
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), "demo_repos.json")

    with open(config_path, "r", encoding="utf-8") as f:
        demo_repos = json.load(f)

    db = SessionLocal()
    print("=" * 70)
    print(f"SEEDING {len(demo_repos)} DEMO REPOSITORIES INTO REPOMENTOR PRODUCTION DB")
    print("=" * 70)

    summary = []

    for item in demo_repos:
        name = item["name"]
        url = item["url"]
        desc = item["desc"]
        print(f"\n---> Checking Demo Repo: {name} ({url})")

        t0 = time.perf_counter()
        remote_hash = get_remote_head_hash(url)

        repo = db.query(Repository).filter(Repository.url == url).first()

        if repo and repo.status == RepositoryStatus.READY and (repo.files_analyzed or 0) > 0:
            cached_hash = None
            if repo.knowledge_summary and isinstance(repo.knowledge_summary, dict):
                cached_hash = repo.knowledge_summary.get("commit_hash")

            if remote_hash and cached_hash == remote_hash:
                elapsed = time.perf_counter() - t0
                print(f" [INSTANT CACHE] {name} is already analyzed at commit {remote_hash[:8]}. Status: READY ({elapsed*1000:.1f}ms)")
                summary.append({
                    "name": name,
                    "url": url,
                    "id": str(repo.id),
                    "status": "ready (cached)",
                    "files": repo.files_analyzed,
                    "health": repo.health_grade,
                    "time_s": round(elapsed, 2)
                })
                continue
            elif not remote_hash:
                elapsed = time.perf_counter() - t0
                print(f" [EXISTING READY] {name} is already analyzed in DB. Status: READY ({elapsed*1000:.1f}ms)")
                summary.append({
                    "name": name,
                    "url": url,
                    "id": str(repo.id),
                    "status": "ready (existing)",
                    "files": repo.files_analyzed,
                    "health": repo.health_grade,
                    "time_s": round(elapsed, 2)
                })
                continue

        # Needs ingestion
        if not repo:
            repo = Repository(url=url, status=RepositoryStatus.QUEUED, status_message="Repository queued")
            db.add(repo)
            db.commit()
            db.refresh(repo)

        repo_id = repo.id
        db.close()

        print(f" [INGESTING] Running full pipeline for {name} (ID: {repo_id})...")
        t_ingest_start = time.perf_counter()
        try:
            ingest_repository(repo_id)
            t_ingest = time.perf_counter() - t_ingest_start
            
            # Reopen session to check result
            db = SessionLocal()
            refreshed = db.query(Repository).filter(Repository.id == repo_id).first()
            print(f" [SUCCESS] {name} completed in {t_ingest:.2f}s! Status: {refreshed.status.value}")
            summary.append({
                "name": name,
                "url": url,
                "id": str(repo_id),
                "status": refreshed.status.value,
                "files": refreshed.files_analyzed,
                "health": refreshed.health_grade,
                "time_s": round(t_ingest, 2)
            })
        except Exception as e:
            t_ingest = time.perf_counter() - t_ingest_start
            print(f" [FAILED] {name} failed: {e}")
            summary.append({
                "name": name,
                "url": url,
                "id": str(repo_id),
                "status": "failed",
                "error": str(e),
                "time_s": round(t_ingest, 2)
            })
            db = SessionLocal()

    db.close()

    print("\n" + "=" * 70)
    print("DEMO SEEDING SUMMARY")
    print("=" * 70)
    for s in summary:
        print(f"• {s['name']:<20} | Status: {s['status']:<16} | Files: {s.get('files', 0):<5} | Grade: {s.get('health', 'N/A'):<3} | Time: {s['time_s']}s")
    print("=" * 70)

if __name__ == "__main__":
    seed_demo_repos()
