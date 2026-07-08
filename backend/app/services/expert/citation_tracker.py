import logging

logger = logging.getLogger(__name__)

def validate_citations(chunks: list[dict]) -> bool:
    """
    Validate that we have at least one valid citation.
    Relaxes checks if repository metadata, README chunks, or high-similarity blocks are present.
    """
    if not chunks:
        return False
        
    # Check if any chunk represents metadata, summary, or has high similarity
    for ch in chunks:
        source_type = ch.get("source_type", "")
        # Metadata or README source types are trusted
        if source_type in ["Metadata", "Summary", "README", "Graph"]:
            return True
            
    max_sim = max(chunk.get("similarity_score", 0.0) for chunk in chunks)
    return max_sim >= 0.15  # Relaxed from 0.30 to allow fuzzy vector matches
