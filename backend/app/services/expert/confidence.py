def calculate_confidence(chunks: list[dict], repo_metadata: dict | None = None) -> int:
    """
    Calculate a confidence percentage score (0-100) based on:
    - Maximum similarity of evidence chunks
    - Total evidence count
    - Repository file coverage
    - Completeness of architecture graph references
    """
    if not chunks:
        return 0

    # 1. Similarity contribution (max similarity * 65)
    max_sim = max(chunk.get("similarity_score", 0.0) for chunk in chunks)
    sim_component = min(65.0, max_sim * 65.0)

    # 2. Evidence count contribution (up to 20 points, 4 points per chunk up to 5 chunks)
    count_component = min(20, len(chunks) * 4)

    # 3. Code coverage / file diversity component (up to 15 points)
    # Award points if we hit multiple distinct files (which indicates broader grounding)
    distinct_files = len(set(chunk.get("file_path", "") for chunk in chunks if chunk.get("file_path")))
    file_diversity_component = min(15, distinct_files * 5)

    score = int(sim_component + count_component + file_diversity_component)
    return max(10, min(100, score))
