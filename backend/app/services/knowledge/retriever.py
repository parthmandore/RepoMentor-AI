import logging
import uuid
from app.db.session import SessionLocal
from app.services.knowledge.embedder import generate_embeddings
from app.repositories.vector_repository import VectorRepository
from app.services.expert.cache import mentor_cache
from app.core.config import settings

logger = logging.getLogger(__name__)

def compute_architectural_boost(file_path: str) -> float:
    """
    Subtle architectural preference for core entry files and domain modules.
    Must never override semantic relevance from RRF fusion.
    """
    if not file_path:
        return 0.0
    path_lower = file_path.lower()
    
    # Exclude synthetic or summary documents
    if any(synth in path_lower for synth in ["repo summary", "virtual_", "repository summary"]):
        return 0.0
    
    # Entry points & core server configurations (subtle 0.03 preference)
    if any(k in path_lower for k in ["main.py", "app.py", "server.ts", "index.ts", "route.ts", "routes.py", "application.java"]):
        return 0.03
        
    # Core schema & models
    if any(k in path_lower for k in ["schema", "model", "entity", "database"]):
        return 0.02
        
    return 0.0

def retrieve_grounded_context(repo_id: str, query: str, limit: int = 5, db = None) -> list[dict]:
    """
    Retrieve the most relevant evidence/code chunks for a query from pgvector database.
    Semantic similarity and RRF fusion scores are strictly preserved.
    Any path-based boost is capped at under 10% of the top fused score,
    and is never applied to evidence documents.
    """
    session_provided = db is not None
    session = db if session_provided else SessionLocal()
    try:
        repo_uuid = uuid.UUID(repo_id) if isinstance(repo_id, str) else repo_id
        
        # 1. Inspect repository stored embedding model and vector census
        from sqlalchemy import text
        stored_emb_info = session.execute(text("""
            SELECT max(embedding_model) as model, max(embedding_dim) as dim, count(embedding) as count_vectors
            FROM repository_embeddings
            WHERE repository_id = :rid
        """), {"rid": repo_uuid}).fetchone()
        stored_model = stored_emb_info[0] if stored_emb_info else None
        stored_dim = stored_emb_info[1] if stored_emb_info else None
        count_vectors = stored_emb_info[2] if stored_emb_info else 0

        # 2. Check Query Embedding Cache or fall back to keyword search
        from app.services.knowledge.embedder import get_active_embedding_provider, generate_embeddings, EmbeddingGenerationError
        active_provider = get_active_embedding_provider()
        query_embedding = None
        
        # Vector search requires:
        # a) active provider configured
        # b) stored vectors actually exist (count_vectors > 0)
        # c) stored model and dimension match active provider exactly
        can_use_vector = (
            active_provider is not None and
            count_vectors > 0 and
            stored_model == active_provider.model_name and
            stored_dim == active_provider.dimension
        )

        if can_use_vector:
            emb_model = active_provider.model_name
            emb_dim = active_provider.dimension
            query_embedding = mentor_cache.get_query_embedding(query, emb_model, emb_dim)
            if query_embedding is None:
                try:
                    query_embedding = generate_embeddings([query])[0]
                    mentor_cache.set_query_embedding(query, emb_model, emb_dim, query_embedding)
                except EmbeddingGenerationError as emb_err:
                    logger.warning(f"Query embedding generation failed: {emb_err}. Falling back to full-text keyword search.")
                    query_embedding = None

        vector_repo = VectorRepository(session)
        candidate_limit = max(10, limit * 2)
        
        if query_embedding is not None:
            grounded_chunks = vector_repo.search_hybrid(
                repository_id=repo_uuid,
                query_text=query,
                query_vector=query_embedding,
                limit=candidate_limit
            )
        else:
            # Fall back strictly to PostgreSQL full-text keyword search (zero meaningless vectors)
            logger.info(f"Retrieving chunks via PostgreSQL full-text keyword search for repository {repo_uuid} (stored_model={stored_model}, active={active_provider.model_name if active_provider else 'None'})")
            grounded_chunks = vector_repo.search_keyword_chunks(
                repository_id=repo_uuid,
                query_text=query,
                limit=candidate_limit
            )
        
        if not grounded_chunks:
            return []
            
        top_fused_score = max((ch.get("similarity_score", 0.0) for ch in grounded_chunks), default=0.0)
        # Bounded boost cap: strictly under 10% of top fused score
        max_boost_cap = top_fused_score * 0.08
        
        ranked_chunks = []
        for ch in grounded_chunks:
            similarity = ch.get("similarity_score", 0.0)
            file_path = ch.get("file_path", "")
            chunk_type = (ch.get("chunk_type") or ch.get("source_type") or "").lower()
            
            # Evidence documents and summaries must never receive code boost
            is_evidence = (
                chunk_type in ("evidence", "evidence_document") or
                file_path.startswith("Repo summary:") or
                file_path in ("Repository Summary", "README.md")
            )
            
            if is_evidence:
                boost = 0.0
            else:
                raw_boost = compute_architectural_boost(file_path)
                boost = min(raw_boost, max_boost_cap)
                
            ch["boosted_score"] = round(similarity + boost, 5)
            ranked_chunks.append(ch)
            
        ranked_chunks.sort(key=lambda x: (-x["boosted_score"], x.get("metadata", {}).get("chunk_id", "")))
        return ranked_chunks[:limit]
    except Exception as e:
        logger.error(f"Internal vector retrieval failure: {e}")
        return []
    finally:
        if not session_provided:
            session.close()
