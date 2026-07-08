import logging
import uuid
from app.db.session import SessionLocal
from app.services.knowledge.embedder import generate_embeddings
from app.repositories.vector_repository import VectorRepository

logger = logging.getLogger(__name__)

def compute_architectural_boost(file_path: str) -> float:
    if not file_path:
        return 0.0
    path_lower = file_path.lower()
    
    # 1. AI & RAG Pipeline (Highest boost)
    if any(k in path_lower for k in ["rag", "pipeline", "agent", "embed", "prompt"]):
        return 0.35
        
    # 2. Security & Secrets (High boost)
    if any(k in path_lower for k in ["security", "secret", "keyring", "crypt", "auth"]):
        return 0.30
        
    # 3. Database schema & patterns
    if any(k in path_lower for k in ["schema", "model", "database", "session", "db."]):
        return 0.25
        
    # 4. Entry points & core configurations
    if any(k in path_lower for k in ["main.py", "app.py", "server.ts", "index.ts", "route.ts", "routes.py", "docker-compose"]):
        return 0.20
        
    # 5. Core Business engines (like GymBuddy engines)
    if any(k in path_lower for k in ["workout", "engine", "adaptive", "processor", "rule"]):
        return 0.15
        
    return 0.0

def retrieve_grounded_context(repo_id: str, query: str, limit: int = 5, db = None) -> list[dict]:
    """
    Retrieve the most relevant evidence/code chunks for a query from pgvector database,
    re-ranked to prioritize core architectural, database, and security logic.
    """
    session_provided = db is not None
    session = db if session_provided else SessionLocal()
    try:
        repo_uuid = uuid.UUID(repo_id) if isinstance(repo_id, str) else repo_id
        
        # Generate query embedding
        query_embedding = generate_embeddings([query])[0]
        
        vector_repo = VectorRepository(session)
        candidate_limit = max(10, limit * 2)
        grounded_chunks = vector_repo.search_similar_chunks(
            repository_id=repo_uuid,
            query_vector=query_embedding,
            limit=candidate_limit
        )
        
        # Apply architectural re-ranking boost
        ranked_chunks = []
        for ch in grounded_chunks:
            similarity = ch.get("similarity_score", 0.0)
            file_path = ch.get("file_path", "")
            boost = compute_architectural_boost(file_path)
            ch["boosted_score"] = similarity * (1.0 + boost)
            ranked_chunks.append(ch)
            
        ranked_chunks.sort(key=lambda x: x["boosted_score"], reverse=True)
        return ranked_chunks[:limit]
    except Exception as e:
        logger.error(f"Internal vector retrieval failure: {e}")
        return []
    finally:
        if not session_provided:
            session.close()
