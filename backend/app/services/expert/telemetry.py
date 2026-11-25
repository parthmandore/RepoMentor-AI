import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger("mentor.telemetry")

class MentorTelemetry:
    """
    Lightweight, high-precision telemetry tracker for the Mentor question-to-answer pipeline.
    Uses monotonic clocks (time.perf_counter) to avoid clock skew.
    Never logs repository source code, user secrets, or credentials.
    """
    def __init__(self, repo_id: str, session_id: str):
        self.repo_id = repo_id
        self.session_id = session_id
        self.t_start = time.perf_counter()
        
        # Monotonic timestamps
        self.ts_received = self.t_start
        self.ts_cache_checked: Optional[float] = None
        self.ts_retrieval_done: Optional[float] = None
        self.ts_prompt_ready: Optional[float] = None
        self.ts_llm_initiated: Optional[float] = None
        self.ts_first_token: Optional[float] = None
        self.ts_completed: Optional[float] = None
        
        # Telemetry metrics
        self.cache_hit: bool = False
        self.retrieved_chunks_count: int = 0
        self.context_tokens_est: int = 0
        self.tokens_generated: int = 0
        self.provider_error: Optional[str] = None

    def mark_cache_checked(self, hit: bool):
        self.ts_cache_checked = time.perf_counter()
        self.cache_hit = hit

    def mark_retrieval_done(self, chunk_count: int):
        self.ts_retrieval_done = time.perf_counter()
        self.retrieved_chunks_count = chunk_count

    def mark_prompt_ready(self, prompt_len_chars: int):
        self.ts_prompt_ready = time.perf_counter()
        self.context_tokens_est = prompt_len_chars // 4

    def mark_llm_initiated(self):
        self.ts_llm_initiated = time.perf_counter()

    def mark_first_token(self):
        if self.ts_first_token is None:
            self.ts_first_token = time.perf_counter()
        self.tokens_generated += 1

    def increment_token(self):
        self.tokens_generated += 1

    def mark_error(self, err_type: str):
        self.provider_error = err_type

    def mark_completed(self) -> Dict[str, Any]:
        self.ts_completed = time.perf_counter()
        
        total_duration_ms = (self.ts_completed - self.t_start) * 1000
        ttft_ms = ((self.ts_first_token - self.t_start) * 1000) if self.ts_first_token else None
        llm_gen_ms = ((self.ts_completed - (self.ts_first_token or self.ts_llm_initiated or self.t_start)) * 1000)
        
        report = {
            "repo_id": self.repo_id,
            "session_id": self.session_id,
            "cache_hit": self.cache_hit,
            "ttft_ms": round(ttft_ms, 2) if ttft_ms is not None else None,
            "llm_generation_ms": round(llm_gen_ms, 2),
            "total_duration_ms": round(total_duration_ms, 2),
            "retrieved_chunks": self.retrieved_chunks_count,
            "context_tokens_est": self.context_tokens_est,
            "tokens_generated": self.tokens_generated,
            "provider_error": self.provider_error
        }
        
        logger.info(
            f"[MentorTelemetry] repo={self.repo_id[:8]} cache_hit={self.cache_hit} "
            f"ttft={report['ttft_ms']}ms total={report['total_duration_ms']}ms "
            f"chunks={self.retrieved_chunks_count} tokens={self.tokens_generated} err={self.provider_error}"
        )
        return report
