import logging
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

# Lazily initialized model instance
_model = None

class EmbeddingGenerationError(Exception):
    """Exception raised when embedding generation fails."""
    pass

def get_embedding_model() -> TextEmbedding:
    """Returns the lazily initialized local FastEmbed TextEmbedding instance."""
    global _model
    if _model is None:
        logger.info("Initializing local FastEmbed model BAAI/bge-small-en-v1.5 (dimension 384)...")
        _model = TextEmbedding()
    return _model

def verify_embeddings_status() -> None:
    """FastEmbed is always available since it runs locally inside the process context."""
    pass

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generates embeddings locally using FastEmbed.
    Does not make any external network requests.
    """
    try:
        model = get_embedding_model()
        # model.embed returns a generator of numpy arrays
        embeddings_generator = model.embed(texts)
        # Convert generator of arrays to list of lists of standard floats
        return [list(map(float, emb)) for emb in embeddings_generator]
    except Exception as e:
        logger.error(f"Local embedding generation failed: {str(e)}")
        raise EmbeddingGenerationError(f"Local embedding generation failed. Error: {str(e)}")
