import os
import time
import math
import hashlib
import random
import logging
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingGenerationError(Exception):
    """Exception raised when remote or local embedding generation fails."""
    pass

class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """
    Google Gemini text-embedding-004 provider.
    Free Tier: 1,500 requests per minute (RPM).
    Dimension: 768.
    Batches requests via batchEmbedContents with exponential backoff and jitter.
    """
    def __init__(self, api_key: str, model_name: str = "text-embedding-004", dimension: int = 768):
        self._api_key = api_key
        self._model = model_name
        self._dimension = dimension
        self._batch_size = 50
        self._endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:batchEmbedContents"

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model

    def _embed_sub_batch(self, sub_batch: List[str]) -> List[List[float]]:
        max_retries = 4
        base_backoff = 1.5

        requests_payload = [
            {
                "model": f"models/{self._model}",
                "content": {"parts": [{"text": text[:8000]}]},
                "outputDimensionality": self._dimension
            }
            for text in sub_batch
        ]

        payload = {"requests": requests_payload}
        params = {"key": self._api_key}

        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(
                    self._endpoint,
                    params=params,
                    json=payload,
                    timeout=30.0,
                    headers={"Content-Type": "application/json"}
                )

                if resp.status_code == 200:
                    data = resp.json()
                    embeddings_raw = data.get("embeddings", [])
                    results = []
                    for item in embeddings_raw:
                        vec = item.get("values", [])
                        # Normalize vector length
                        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
                        results.append([x / norm for x in vec])
                    return results

                # Handle rate limit (429) or transient server errors (500, 503)
                if resp.status_code in (429, 500, 502, 503, 504):
                    jitter = random.uniform(0.1, 0.5)
                    sleep_time = (base_backoff ** attempt) + jitter
                    logger.warning(
                        f"Gemini embedding API HTTP {resp.status_code}. Retrying attempt {attempt}/{max_retries} in {sleep_time:.2f}s..."
                    )
                    time.sleep(sleep_time)
                    continue

                error_msg = resp.text[:300]
                raise EmbeddingGenerationError(f"Gemini Embedding API failed with HTTP {resp.status_code}: {error_msg}")

            except requests.RequestException as req_err:
                if attempt == max_retries:
                    raise EmbeddingGenerationError(f"Gemini API request failed after {max_retries} retries: {req_err}")
                sleep_time = (base_backoff ** attempt) + random.uniform(0.1, 0.5)
                time.sleep(sleep_time)

        raise EmbeddingGenerationError("Gemini embedding failed after maximum retries.")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self._batch_size):
            chunk = texts[i : i + self._batch_size]
            sub_results = self._embed_sub_batch(chunk)
            all_embeddings.extend(sub_results)
            # Small pacing between large batches to respect rate limits
            if i + self._batch_size < len(texts):
                time.sleep(0.05)

        return all_embeddings


class OpenAICompatibleEmbeddingProvider(BaseEmbeddingProvider):
    """
    OpenAI-compatible embedding endpoint (e.g. Voyage, Jina, Mistral, Ollama).
    """
    def __init__(self, api_key: str, base_url: str, model_name: str, dimension: int = 768):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model_name
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        resp = requests.post(
            f"{self._base_url}/embeddings",
            headers=headers,
            json={"model": self._model, "input": texts},
            timeout=30.0
        )
        if resp.status_code != 200:
            raise EmbeddingGenerationError(f"Embedding API error HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        results = [item["embedding"] for item in data["data"]]
        return results


# Singleton provider instance
_provider: Optional[BaseEmbeddingProvider] = None

def get_active_embedding_provider() -> Optional[BaseEmbeddingProvider]:
    global _provider
    if _provider is not None:
        return _provider

    provider_type = getattr(settings, "EMBEDDING_PROVIDER", "gemini").lower()
    api_key = getattr(settings, "EMBEDDING_API_KEY", "") or os.getenv("GEMINI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    dimension = getattr(settings, "EMBEDDING_DIMENSION", 768)
    model = getattr(settings, "EMBEDDING_MODEL", "gemini-embedding-001")

    if not api_key:
        logger.warning("No EMBEDDING_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY configured. Remote embeddings disabled.")
        return None

    if provider_type == "gemini":
        logger.info(f"Using GeminiEmbeddingProvider (model={model}, dimension={dimension})")
        _provider = GeminiEmbeddingProvider(api_key=api_key, model_name=model, dimension=dimension)
    elif provider_type == "openai":
        base_url = os.getenv("EMBEDDING_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
        logger.info(f"Using OpenAICompatibleEmbeddingProvider (base_url={base_url}, model={model}, dimension={dimension})")
        _provider = OpenAICompatibleEmbeddingProvider(api_key=api_key, base_url=base_url, model_name=model, dimension=dimension)
    else:
        logger.warning(f"Unknown EMBEDDING_PROVIDER '{provider_type}'.")
        return None

    return _provider


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Standard interface for generating embeddings across both ingestion and mentor queries.
    Guarantees index and query consistency using the same active provider.
    Raises EmbeddingGenerationError if no provider is configured (never uses fake vectors).
    """
    if not texts:
        return []
    provider = get_active_embedding_provider()
    if provider is None:
        raise EmbeddingGenerationError("No embedding provider is configured or available. Please configure EMBEDDING_API_KEY.")
    return provider.embed_batch(texts)


def verify_embeddings_status() -> None:
    """Verifies that the embedding provider is operational."""
    provider = get_active_embedding_provider()
    if provider is not None:
        logger.info(f"Embedding Provider verified: {provider.model_name} (dim={provider.dimension})")
    else:
        logger.info("Embedding Provider: None (Full-text keyword fallback active)")
