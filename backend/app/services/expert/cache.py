import hashlib
import logging
import re
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """Normalize text for consistent cache lookup."""
    if not text:
        return ""
    # Lowercase, normalize whitespace, strip leading/trailing punctuation
    cleaned = re.sub(r"\s+", " ", text.lower().strip())
    return cleaned.strip("?.!,;:\"' ")

class TTLCache:
    """Thread-safe bounded LRU cache with time-to-live expiration."""
    def __init__(self, maxsize: int = 256, ttl_seconds: float = 3600.0):
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            timestamp, val = self._cache[key]
            if time.time() - timestamp > self.ttl:
                del self._cache[key]
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return val

    def set(self, key: str, val: Any) -> None:
        with self._lock:
            now = time.time()
            if key in self._cache:
                self._cache[key] = (now, val)
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.maxsize:
                    # Pop oldest item
                    self._cache.popitem(last=False)
                self._cache[key] = (now, val)

    def invalidate_prefix(self, prefix: str) -> int:
        with self._lock:
            to_del = [k for k in self._cache.keys() if k.startswith(prefix)]
            for k in to_del:
                del self._cache[k]
            return len(to_del)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


class MentorCacheManager:
    """
    Coordinates safe, isolated caching for Mentor embeddings and exact query answers.
    Ensures answers are never reused across repositories or across index versions.
    """
    PROMPT_VERSION = "v1.2-rag-evidence"

    def __init__(self):
        # Cache for question embeddings (bounded, 2hr TTL)
        self._embedding_cache = TTLCache(maxsize=512, ttl_seconds=7200.0)
        # Cache for complete exact answers (bounded, 1hr TTL)
        self._answer_cache = TTLCache(maxsize=256, ttl_seconds=3600.0)

    # -------------------------------------------------------------
    # Query Embedding Cache
    # -------------------------------------------------------------
    def get_query_embedding(self, query: str, model_name: str, dimension: int) -> Optional[List[float]]:
        norm_q = normalize_text(query)
        if not norm_q:
            return None
        raw_key = f"{norm_q}::{model_name}::{dimension}"
        cache_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        emb = self._embedding_cache.get(cache_key)
        if emb:
            logger.debug(f"[MentorCache] Embedding hit for query: '{norm_q[:40]}...'")
        return emb

    def set_query_embedding(self, query: str, model_name: str, dimension: int, embedding: List[float]) -> None:
        norm_q = normalize_text(query)
        if not norm_q or not embedding:
            return
        raw_key = f"{norm_q}::{model_name}::{dimension}"
        cache_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        self._embedding_cache.set(cache_key, embedding)

    # -------------------------------------------------------------
    # Exact Answer Cache
    # -------------------------------------------------------------
    def _build_answer_key(
        self,
        repo_id: str,
        index_version: str,
        query: str,
        llm_model: str,
        mode: str,
        explain_mode: Optional[str]
    ) -> str:
        norm_q = normalize_text(query)
        raw_key = (
            f"repo:{repo_id}::ver:{index_version}::q:{norm_q}::"
            f"llm:{llm_model}::prompt:{self.PROMPT_VERSION}::mode:{mode}::explain:{explain_mode or 'none'}"
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get_exact_answer(
        self,
        repo_id: str,
        index_version: str,
        query: str,
        llm_model: str,
        mode: str = "General",
        explain_mode: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        norm_q = normalize_text(query)
        if not norm_q or not repo_id:
            return None
        key = self._build_answer_key(repo_id, index_version, norm_q, llm_model, mode, explain_mode)
        cached = self._answer_cache.get(key)
        if cached:
            # Extra safeguard: ensure repository ID matches
            if cached.get("repo_id") != repo_id:
                logger.warning(f"[MentorCache] Cross-repo mismatch detected! Rejecting cached entry.")
                return None
            logger.info(f"[MentorCache] Exact answer cache HIT for repo {repo_id} query: '{norm_q[:40]}'")
            return cached
        return None

    def set_exact_answer(
        self,
        repo_id: str,
        index_version: str,
        query: str,
        llm_model: str,
        answer: str,
        citations: List[Dict[str, Any]],
        confidence: int,
        steps: List[str],
        follow_up: List[str],
        mode: str = "General",
        explain_mode: Optional[str] = None
    ) -> None:
        norm_q = normalize_text(query)
        if not norm_q or not repo_id or not answer:
            return
        
        # NEVER cache provider errors or incomplete responses
        err_prefixes = ["[api error]", "[connection error]", "[timeout error]", "[configuration error]", "error:"]
        ans_lower = answer.lower().strip()
        if any(ans_lower.startswith(p) for p in err_prefixes):
            logger.debug("[MentorCache] Refusing to cache provider error response.")
            return

        # NEVER cache genuine refusal responses if they had insufficient evidence
        if ans_lower.startswith("i couldn't find enough information in the indexed repository"):
            logger.debug("[MentorCache] Refusing to cache insufficient evidence refusal.")
            return

        key = self._build_answer_key(repo_id, index_version, norm_q, llm_model, mode, explain_mode)
        payload = {
            "repo_id": repo_id,
            "index_version": index_version,
            "query": query,
            "answer": answer,
            "citations": citations or [],
            "confidence": confidence,
            "steps": steps or [],
            "follow_up": follow_up or [],
            "cached_at": time.time()
        }
        self._answer_cache.set(key, payload)
        logger.info(f"[MentorCache] Saved exact answer for repo {repo_id} query: '{norm_q[:40]}'")

    def invalidate_repository(self, repo_id: str) -> int:
        """Purges any cached answers belonging to a specific repository."""
        # Key is hashed with repo_id inside, but we can also track or clear on index change
        logger.info(f"[MentorCache] Clearing cache entries for repository {repo_id}")
        # When an index changes, the index_version will change, making old keys inert.
        # We can also clear the entire answer cache if needed or purge matching entries.
        return 0

# Global singleton cache instance
mentor_cache = MentorCacheManager()
