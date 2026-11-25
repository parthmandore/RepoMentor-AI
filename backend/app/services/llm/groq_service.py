import logging
import requests
import json
import time
import re
import random
import threading
from typing import Optional, Generator
from app.core.config import settings

logger = logging.getLogger(__name__)

class GroqProviderError(Exception):
    """Structured exception for Groq LLM provider failures."""
    def __init__(self, status_code: int, message: str, retryable: bool = False, retry_after: Optional[float] = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.retryable = retryable
        self.retry_after = retry_after

# Global connection pooling and concurrency control
_groq_session: Optional[requests.Session] = None
_groq_lock = threading.Lock()
_concurrency_semaphore = threading.Semaphore(3)  # Max 3 concurrent LLM requests

# Thread-local storage to track which model answered
_thread_local = threading.local()

def get_groq_session() -> requests.Session:
    global _groq_session
    if _groq_session is None:
        with _groq_lock:
            if _groq_session is None:
                s = requests.Session()
                adapter = requests.adapters.HTTPAdapter(
                    pool_connections=5,
                    pool_maxsize=10,
                    max_retries=0,
                    pool_block=False
                )
                s.mount("https://", adapter)
                _groq_session = s
    return _groq_session

class GroqService:
    """
    Dedicated high-performance service for LLM execution using Groq API.
    Features keep-alive connection reuse, exponential backoff with jitter on 429,
    fallback to backup model on persistent rate limits, token usage logging,
    and seed / zero-temperature determinism.
    """
    
    @classmethod
    def get_last_model_used(cls) -> str:
        """Returns the model that answered the most recent call on the current thread."""
        return getattr(_thread_local, "last_model_used", settings.GROQ_MODEL)

    @classmethod
    def _parse_retry_after(cls, res: requests.Response, attempt: int) -> float:
        wait_s = 1.5 * (2 ** attempt) + random.uniform(0.1, 0.4)
        try:
            retry_header = res.headers.get("Retry-After")
            if retry_header:
                wait_s = float(retry_header) + 0.2
            else:
                err_json = res.json().get("error", {})
                msg = err_json.get("message", "")
                match = re.search(r"try again in ([\d\.]+)s", msg)
                if match:
                    wait_s = float(match.group(1)) + 0.3
        except Exception:
            pass
        return min(wait_s, 6.0)

    @classmethod
    def generate(
        cls,
        prompt: str,
        system_instruction: str = None,
        history: list[dict] = None,
        temperature: float = 0.0
    ) -> str:
        """
        Executes completions via Groq API with bounded retries, 429 fallback, and token logging.
        """
        if not settings.GROQ_API_KEY:
            logger.error("GROQ_API_KEY is not configured in environment variables.")
            raise GroqProviderError(500, "Groq API Key is missing. Please configure GROQ_API_KEY.", False)

        endpoint = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        if history:
            for msg in history:
                messages.append({"role": msg.get("role"), "content": msg.get("content")})
        messages.append({"role": "user", "content": prompt})

        session = get_groq_session()
        primary_model = settings.GROQ_MODEL
        fallback_model = getattr(settings, "GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant")
        models_to_try = [primary_model, fallback_model]

        with _concurrency_semaphore:
            for model_idx, current_model in enumerate(models_to_try):
                max_attempts = 3 if model_idx == 0 else 2
                for attempt in range(max_attempts):
                    payload = {
                        "model": current_model,
                        "messages": messages,
                        "temperature": 0.0,
                        "seed": 42,
                        "top_p": 1.0,
                        "max_tokens": 2048,
                        "stream": False
                    }
                    try:
                        res = session.post(
                            endpoint,
                            headers=headers,
                            json=payload,
                            timeout=(5.0, settings.GROQ_TIMEOUT)
                        )
                        
                        if res.status_code == 200:
                            data = res.json()
                            usage = data.get("usage", {})
                            prompt_tokens = usage.get("prompt_tokens", 0)
                            completion_tokens = usage.get("completion_tokens", 0)
                            _thread_local.last_model_used = current_model
                            logger.info(f"[Groq LLM Usage] Model: {current_model} | prompt_tokens={prompt_tokens} | completion_tokens={completion_tokens}")
                            
                            choices = data.get("choices")
                            if choices and len(choices) > 0:
                                return choices[0].get("message", {}).get("content", "").strip()
                            return "Error: Groq returned no completions choices."

                        elif res.status_code in (429, 503):
                            wait_s = cls._parse_retry_after(res, attempt)
                            if attempt < max_attempts - 1:
                                logger.warning(f"Groq API {res.status_code} ({current_model}). Retrying in {wait_s:.1f}s (attempt {attempt+1}/{max_attempts})")
                                time.sleep(wait_s)
                                continue
                            elif model_idx == 0:
                                logger.warning(f"Groq primary model {primary_model} rate-limited after retries. Switching to fallback {fallback_model}...")
                                break  # break attempt loop to switch to fallback model
                            else:
                                raise GroqProviderError(429, "Rate limit reached. Please wait a moment and try again.", True, wait_s)

                        elif res.status_code == 400:
                            raise GroqProviderError(400, "Context length exceeded or invalid model parameters.", False)
                        else:
                            raise GroqProviderError(res.status_code, f"Groq API call failed: status {res.status_code}", True)

                    except requests.Timeout:
                        if attempt < max_attempts - 1:
                            time.sleep(1.0)
                            continue
                        if model_idx == 0:
                            logger.warning(f"Groq timeout on {primary_model}. Trying fallback {fallback_model}...")
                            break
                        raise GroqProviderError(504, f"Groq request timed out after {settings.GROQ_TIMEOUT} seconds.", True)

                    except requests.RequestException as e:
                        if attempt < max_attempts - 1:
                            time.sleep(1.0)
                            continue
                        if model_idx == 0:
                            logger.warning(f"Groq connection error on {primary_model}: {e}. Trying fallback...")
                            break
                        raise GroqProviderError(503, f"Failed to connect to Groq: {str(e)}", True)

        raise GroqProviderError(503, "Groq provider retries and fallback exhausted.", True)

    @classmethod
    def generate_stream(
        cls,
        prompt: str,
        system_instruction: str = None,
        history: list[dict] = None,
        temperature: float = 0.0
    ) -> Generator[str, None, None]:
        """
        Queries Groq API with stream=True, yielding tokens as they arrive.
        Enforces temperature=0, seed=42, stream_options include_usage,
        429 exponential backoff with jitter and fallback model.
        """
        if not settings.GROQ_API_KEY:
            logger.error("GROQ_API_KEY is not configured in environment variables.")
            raise GroqProviderError(500, "Groq API Key is missing. Please configure GROQ_API_KEY.", False)

        endpoint = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        if history:
            for msg in history:
                messages.append({"role": msg.get("role"), "content": msg.get("content")})
        messages.append({"role": "user", "content": prompt})

        session = get_groq_session()
        primary_model = settings.GROQ_MODEL
        fallback_model = getattr(settings, "GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant")
        models_to_try = [primary_model, fallback_model]

        with _concurrency_semaphore:
            for model_idx, current_model in enumerate(models_to_try):
                max_attempts = 3 if model_idx == 0 else 2
                for attempt in range(max_attempts):
                    payload = {
                        "model": current_model,
                        "messages": messages,
                        "temperature": 0.0,
                        "seed": 42,
                        "top_p": 1.0,
                        "max_tokens": 2048,
                        "stream": True,
                        "stream_options": {"include_usage": True}
                    }
                    try:
                        res = session.post(
                            endpoint,
                            headers=headers,
                            json=payload,
                            timeout=(5.0, settings.GROQ_TIMEOUT),
                            stream=True
                        )
                        
                        if res.status_code == 200:
                            _thread_local.last_model_used = current_model
                            tokens_emitted = 0
                            try:
                                for line in res.iter_lines():
                                    if not line:
                                        continue
                                    decoded_line = line.decode("utf-8").strip()
                                    if decoded_line.startswith("data: "):
                                        data_str = decoded_line[6:].strip()
                                        if data_str == "[DONE]":
                                            break
                                        try:
                                            chunk_data = json.loads(data_str)
                                            # Check for usage object
                                            if "usage" in chunk_data and chunk_data["usage"]:
                                                usage = chunk_data["usage"]
                                                p_tokens = usage.get("prompt_tokens", 0)
                                                c_tokens = usage.get("completion_tokens", 0)
                                                logger.info(f"[Groq LLM Stream Usage] Model: {current_model} | prompt_tokens={p_tokens} | completion_tokens={c_tokens}")
                                                
                                            choices = chunk_data.get("choices")
                                            if choices and len(choices) > 0:
                                                delta = choices[0].get("delta", {})
                                                token = delta.get("content", "")
                                                if token:
                                                    tokens_emitted += 1
                                                    yield token
                                        except Exception:
                                            pass
                                # Clean completion
                                return
                            except Exception as stream_err:
                                logger.error(f"Groq mid-stream network drop after {tokens_emitted} tokens: {stream_err}")
                                raise GroqProviderError(500, "Connection dropped while generating answer.", True)

                        elif res.status_code in (429, 503):
                            wait_s = cls._parse_retry_after(res, attempt)
                            if attempt < max_attempts - 1:
                                logger.warning(f"Groq API {res.status_code} stream rate limit ({current_model}). Backing off {wait_s:.1f}s (attempt {attempt+1}/{max_attempts})")
                                time.sleep(wait_s)
                                continue
                            elif model_idx == 0:
                                logger.warning(f"Groq stream primary {primary_model} 429 exhausted. Switching to fallback {fallback_model}...")
                                break
                            else:
                                raise GroqProviderError(429, "LLM rate limit reached. Please wait a moment and try again.", True, wait_s)

                        elif res.status_code == 400:
                            raise GroqProviderError(400, "Query context or prompt size exceeded LLM limit.", False)
                        elif res.status_code == 401:
                            raise GroqProviderError(401, "LLM authorization failed. Check GROQ_API_KEY.", False)
                        else:
                            raise GroqProviderError(res.status_code, f"Groq provider status {res.status_code}", True)

                    except requests.Timeout:
                        if attempt < max_attempts - 1:
                            time.sleep(1.0)
                            continue
                        if model_idx == 0:
                            logger.warning(f"Groq stream timeout on {primary_model}. Trying fallback {fallback_model}...")
                            break
                        raise GroqProviderError(504, f"Groq stream timed out after {settings.GROQ_TIMEOUT} seconds.", True)

                    except requests.RequestException as e:
                        if attempt < max_attempts - 1:
                            time.sleep(1.0)
                            continue
                        if model_idx == 0:
                            logger.warning(f"Groq stream connection error on {primary_model}: {e}. Trying fallback...")
                            break
                        raise GroqProviderError(503, f"Failed to connect to Groq stream: {str(e)}", True)

        raise GroqProviderError(503, "Groq stream retries and fallback exhausted.", True)
