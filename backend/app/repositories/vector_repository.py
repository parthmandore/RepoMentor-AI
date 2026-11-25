import logging
import uuid
import json
import time
from sqlalchemy import text
from sqlalchemy.orm import Session
from psycopg2.extras import execute_values
from app.core.config import settings

logger = logging.getLogger(__name__)

class VectorRepository:
    """
    Handles all PostgreSQL vector operations using raw SQL via pgvector extension.
    Encapsulates schema verification, chunk insertions, and similarity/neighbor search operations.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def ensure_vector_table(self, dimension: int) -> None:
        """
        Creates pgvector extension, table, and HNSW index if they do not exist.
        Dimension determines the size of the embedding vector.
        """
        try:
            self.db.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            self.db.commit()
            logger.info("Checked/Enabled pgvector extension.")
        except Exception as extension_err:
            self.db.rollback()
            logger.warning(f"Could not check/enable pgvector extension (might not be superuser): {extension_err}")

        # Check if table already exists or matches dimension
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS repository_embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
            chunk_id VARCHAR(255) NOT NULL UNIQUE,
            document_id VARCHAR(255) NOT NULL,
            file_path TEXT NOT NULL,
            start_line INTEGER,
            end_line INTEGER,
            chunk_type VARCHAR(50),
            source_phase VARCHAR(100),
            content TEXT NOT NULL,
            metadata JSONB,
            embedding vector({dimension}),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            self.db.execute(text(create_table_sql))
            # HNSW index for cosine distance similarity
            self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS repository_embeddings_hnsw_idx 
                ON repository_embeddings 
                USING hnsw (embedding vector_cosine_ops);
            """))
            # Normal index on repository_id for fast filtering
            self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS repository_embeddings_repo_id_idx 
                ON repository_embeddings (repository_id);
            """))
            self.db.commit()
            logger.info(f"pgvector table 'repository_embeddings' with vector({dimension}) verified/created successfully.")

            # Verify dimension matches if table already existed
            dim_check = self.db.execute(text("""
                SELECT atttypmod 
                FROM pg_attribute 
                WHERE attrelid = 'repository_embeddings'::regclass AND attname = 'embedding';
            """)).scalar()
            if dim_check is not None and dim_check != dimension:
                logger.warning(f"Vector dimension mismatch (found {dim_check}, expected {dimension}). Altering column...")
                self.db.execute(text("DROP INDEX IF EXISTS repository_embeddings_hnsw_idx;"))
                self.db.execute(text(f"ALTER TABLE repository_embeddings ALTER COLUMN embedding TYPE vector({dimension}) USING NULL;"))
                self.db.execute(text("""
                    CREATE INDEX IF NOT EXISTS repository_embeddings_hnsw_idx 
                    ON repository_embeddings 
                    USING hnsw (embedding vector_cosine_ops);
                """))
                self.db.commit()
                logger.info(f"Successfully migrated embedding column to vector({dimension}).")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to verify/create pgvector table or indexes: {e}")
            raise e

    def insert_embeddings(self, repository_id: uuid.UUID, chunks: list[dict], embeddings: list[list[float]]) -> int:
        """
        Inserts list of chunks and their corresponding embedding vectors into pgvector.
        Uses psycopg2.extras.execute_values for true multi-row INSERT in a single
        network round-trip per batch, instead of one round-trip per row.
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks list and embeddings list must be of equal length.")

        insert_sql = """
        INSERT INTO repository_embeddings (
            repository_id, chunk_id, document_id, file_path, start_line, end_line, chunk_type, source_phase, content, metadata, embedding, embedding_model, embedding_dim
        ) VALUES %s
        ON CONFLICT (chunk_id) DO UPDATE SET
            content = EXCLUDED.content,
            metadata = EXCLUDED.metadata,
            embedding = EXCLUDED.embedding,
            embedding_model = EXCLUDED.embedding_model,
            embedding_dim = EXCLUDED.embedding_dim
        """
        
        inserted = 0
        try:
            # Build tuple list for execute_values
            emb_model_default = getattr(settings, "EMBEDDING_MODEL", "text-embedding-004")
            emb_dim_default = getattr(settings, "EMBEDDING_DIMENSION", 768)
            values_list = []
            for chunk, emb in zip(chunks, embeddings):
                emb_str = str(emb).replace(" ", "") if emb is not None else None
                emb_model = chunk.get("embedding_model", emb_model_default) if emb is not None else None
                emb_dim = chunk.get("embedding_dim", emb_dim_default) if emb is not None else None
                values_list.append((
                    str(repository_id),
                    chunk["chunk_id"],
                    chunk["document_id"],
                    chunk["file_path"],
                    chunk.get("start_line"),
                    chunk.get("end_line"),
                    chunk.get("chunk_type", "Block"),
                    chunk.get("source_phase", "Unknown"),
                    chunk["content"],
                    json.dumps(chunk.get("metadata", {})),
                    emb_str,
                    emb_model,
                    emb_dim
                ))
                
            # Use raw psycopg2 connection to call execute_values directly
            # This generates a single INSERT ... VALUES (...), (...), ... statement
            raw_conn = self.db.get_bind().raw_connection()
            cursor = raw_conn.cursor()
            
            t_insert_start = time.perf_counter()
            
            # execute_values with page_size controls how many rows per VALUES block
            # Using 500 rows per page to balance memory and network efficiency
            execute_values(
                cursor,
                insert_sql,
                values_list,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::vector, %s, %s)",
                page_size=500
            )
            inserted = len(values_list)
            
            raw_conn.commit()
            cursor.close()
            
            t_insert_duration = time.perf_counter() - t_insert_start
            logger.info(f"[VectorRepo] Batch-inserted {inserted} embeddings via execute_values in {t_insert_duration:.2f}s (round-trips: {max(1, len(values_list) // 500 + 1)})")
            return inserted
        except Exception as e:
            try:
                raw_conn.rollback()
                cursor.close()
            except Exception:
                pass
            self.db.rollback()
            logger.error(f"Failed to bulk insert embeddings in pgvector: {e}")
            raise e

    def delete_repository_vectors(self, repository_id: uuid.UUID) -> int:
        """
        Wipes all vectors belonging to a repository (useful for re-analysis cleanups).
        """
        query = "DELETE FROM repository_embeddings WHERE repository_id = :repository_id"
        try:
            res = self.db.execute(text(query), {"repository_id": repository_id})
            deleted_count = res.rowcount
            self.db.commit()
            logger.info(f"Deleted {deleted_count} vectors from pgvector for repo {repository_id}.")
            return deleted_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete repository vectors for {repository_id}: {e}")
            return 0

    def delete_file_vectors(self, repository_id: uuid.UUID, file_path: str) -> int:
        """
        Deletes all vector chunks belonging to a single file path in the repository.
        """
        query = "DELETE FROM repository_embeddings WHERE repository_id = :repository_id AND file_path = :file_path"
        try:
            res = self.db.execute(text(query), {"repository_id": repository_id, "file_path": file_path})
            deleted_count = res.rowcount
            self.db.commit()
            return deleted_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete file vectors for {file_path}: {e}")
            return 0

    def delete_files_vectors(self, repository_id: uuid.UUID, file_paths: list[str]) -> int:
        """
        Deletes all vector chunks belonging to a list of file paths in the repository.
        """
        if not file_paths:
            return 0
        query = "DELETE FROM repository_embeddings WHERE repository_id = :repository_id AND file_path IN :file_paths"
        try:
            res = self.db.execute(text(query), {"repository_id": repository_id, "file_paths": tuple(file_paths)})
            deleted_count = res.rowcount
            self.db.commit()
            return deleted_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete file vectors in batch: {e}")
            return 0

    def get_file_chunks_metadata(self, repository_id: uuid.UUID, file_path: str) -> list[dict]:
        """
        Fetches chunk IDs and metadata for a specific file path.
        """
        query = "SELECT chunk_id, metadata FROM repository_embeddings WHERE repository_id = :repository_id AND file_path = :file_path"
        try:
            res = self.db.execute(text(query), {"repository_id": repository_id, "file_path": file_path})
            return [{"chunk_id": row[0], "metadata": row[1] or {}} for row in res]
        except Exception as e:
            logger.error(f"Failed to fetch file chunks metadata for {file_path}: {e}")
            return []

    def get_all_repository_chunks_metadata(self, repository_id: uuid.UUID) -> dict[str, list[dict]]:
        """
        Fetches chunk IDs and metadata for all files in a repository.
        """
        query = "SELECT chunk_id, file_path, metadata FROM repository_embeddings WHERE repository_id = :repository_id"
        result_map = {}
        try:
            res = self.db.execute(text(query), {"repository_id": repository_id})
            for row in res:
                chunk_id, file_path, metadata = row[0], row[1], row[2]
                if file_path not in result_map:
                    result_map[file_path] = []
                result_map[file_path].append({"chunk_id": chunk_id, "metadata": metadata or {}})
            return result_map
        except Exception as e:
            logger.error(f"Failed to fetch all repository chunks metadata: {e}")
            return {}

    def search_similar_chunks(self, repository_id: uuid.UUID, query_vector: list[float], limit: int = 5) -> list[dict]:
        """
        Performs cosine similarity search using the operator <=> on pgvector.
        Returns matches sorted by similarity score descending.
        """
        query = """
        SELECT 
            chunk_id, document_id, file_path, start_line, end_line, chunk_type, source_phase, content, metadata,
            1.0 - (embedding <=> :query_vector) AS similarity
        FROM repository_embeddings
        WHERE repository_id = :repository_id
        ORDER BY embedding <=> :query_vector
        LIMIT :limit
        """
        qv_str = str(query_vector).replace(" ", "")
        
        try:
            res = self.db.execute(
                text(query),
                {
                    "repository_id": repository_id,
                    "query_vector": qv_str,
                    "limit": limit
                }
            )
            
            grounded_chunks = []
            for row in res:
                # Cosine similarity score
                similarity = round(float(row[9]), 4)
                
                # Standardize to fit retriever expectations
                grounded_chunks.append({
                    "similarity_score": similarity,
                    "source_type": row[5] or "Code",  # chunk_type or document_type
                    "file_path": row[2],
                    "line_numbers": f"{row[3]}-{row[4]}",
                    "evidence_type": row[5] or "Block",
                    "chunk_type": row[5] or "Block",
                    "content": row[7],
                    "start_line": int(row[3]) if row[3] is not None else 1,
                    "end_line": int(row[4]) if row[4] is not None else 1,
                    "metadata": {
                        "chunk_id": row[0],
                        "document_id": row[1],
                        "repo_id": str(repository_id),
                        "source_phase": row[6],
                        "document_type": row[5],
                        "file_path": row[2],
                        "chunk_type": row[5],
                        "start_line": row[3],
                        "end_line": row[4],
                        **(row[8] or {})
                    }
                })
            return grounded_chunks
        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            logger.error(f"Similarity search query failed on pgvector: {e}")
            return []

    def search_keyword_chunks(self, repository_id: uuid.UUID, query_text: str, limit: int = 10) -> list[dict]:
        """
        Performs PostgreSQL Full-Text Keyword Search with OR semantics and identifier tokenization
        using the GIN index on repository_embeddings.
        Deterministic tie-break by rank_score DESC, id ASC.
        """
        import re
        s1 = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', query_text)
        s2 = re.sub(r'[_/\-.:]', ' ', s1)
        s3 = re.sub(r'[^\w\s]', ' ', s2)
        raw_tokens = [t.strip().lower() for t in s3.split() if len(t.strip()) > 1]
        stopwords = {
            "where", "does", "the", "in", "is", "of", "and", "or", "to", "what", "how",
            "are", "there", "any", "two", "do", "for", "with", "can", "an", "as", "by"
        }
        filtered = [t for t in raw_tokens if t not in stopwords] or raw_tokens
        clean_tokens = [re.sub(r'[^a-zA-Z0-9]', '', t) for t in filtered if len(re.sub(r'[^a-zA-Z0-9]', '', t)) > 1]
        
        if clean_tokens:
            tsquery_str = " | ".join(clean_tokens)
            query = """
            SELECT 
                chunk_id, document_id, file_path, start_line, end_line, chunk_type, source_phase, content, metadata,
                ts_rank_cd(to_tsvector('english', content), to_tsquery('english', :query_text)) AS rank_score
            FROM repository_embeddings
            WHERE repository_id = :repository_id
              AND to_tsvector('english', content) @@ to_tsquery('english', :query_text)
            ORDER BY rank_score DESC, id ASC
            LIMIT :limit
            """
        else:
            tsquery_str = query_text
            query = """
            SELECT 
                chunk_id, document_id, file_path, start_line, end_line, chunk_type, source_phase, content, metadata,
                ts_rank_cd(to_tsvector('english', content), plainto_tsquery('english', :query_text)) AS rank_score
            FROM repository_embeddings
            WHERE repository_id = :repository_id
              AND to_tsvector('english', content) @@ plainto_tsquery('english', :query_text)
            ORDER BY rank_score DESC, id ASC
            LIMIT :limit
            """
        try:
            res = self.db.execute(
                text(query),
                {
                    "repository_id": repository_id,
                    "query_text": tsquery_str,
                    "limit": limit
                }
            )
            keyword_chunks = []
            for row in res:
                rank_score = round(float(row[9]), 4) if row[9] is not None else 0.0
                start_l = int(row[3]) if row[3] is not None else None
                end_l = int(row[4]) if row[4] is not None else None
                line_str = f"{start_l}-{end_l}" if start_l is not None and end_l is not None else None
                keyword_chunks.append({
                    "similarity_score": rank_score,
                    "source_type": row[5] or "Code",
                    "file_path": row[2],
                    "line_numbers": line_str,
                    "evidence_type": row[5] or "Block",
                    "chunk_type": row[5] or "Block",
                    "content": row[7],
                    "start_line": start_l,
                    "end_line": end_l,
                    "metadata": {
                        "chunk_id": row[0],
                        "document_id": row[1],
                        "repo_id": str(repository_id),
                        "source_phase": row[6],
                        "document_type": row[5],
                        "file_path": row[2],
                        "chunk_type": row[5],
                        "start_line": start_l,
                        "end_line": end_l,
                        **(row[8] or {})
                    }
                })
            return keyword_chunks
        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            logger.error(f"Keyword search query failed on Postgres: {e}")
            return []

    def search_hybrid(
        self,
        repository_id: uuid.UUID,
        query_text: str,
        query_vector: list[float],
        limit: int = 6,
        rrf_k: int = 60
    ) -> list[dict]:
        """
        Hybrid search combining pgvector cosine similarity and PostgreSQL full-text search.
        Merges results using Reciprocal Rank Fusion (RRF):
            Score(d) = sum(1 / (rrf_k + rank_i(d)))
        Deterministic tie-break: order by score DESC, chunk_id ASC.
        """
        candidate_limit = max(10, limit * 2)
        vector_results = self.search_similar_chunks(repository_id, query_vector, limit=candidate_limit)
        keyword_results = self.search_keyword_chunks(repository_id, query_text, limit=candidate_limit)
        
        scores: dict[str, float] = {}
        chunks_by_id: dict[str, dict] = {}
        
        # Rank from vector results
        for rank, chunk in enumerate(vector_results, start=1):
            cid = chunk["metadata"]["chunk_id"]
            chunks_by_id[cid] = chunk
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))
            
        # Rank from keyword results
        for rank, chunk in enumerate(keyword_results, start=1):
            cid = chunk["metadata"]["chunk_id"]
            if cid not in chunks_by_id:
                chunks_by_id[cid] = chunk
            # Exact keyword match receives a 1.25x weight in RRF
            scores[cid] = scores.get(cid, 0.0) + (1.25 / (rrf_k + rank))
            
        # Sort merged candidate pool by combined RRF score DESC, chunk_id ASC
        sorted_ids = sorted(scores.keys(), key=lambda cid: (-scores[cid], str(cid)))
        merged = []
        for cid in sorted_ids[:limit]:
            ch = chunks_by_id[cid]
            ch["rrf_score"] = round(scores[cid], 5)
            ch["similarity_score"] = min(1.0, max(ch.get("similarity_score", 0.0), round(scores[cid] * 30.0, 4)))
            merged.append(ch)
            
        return merged

    def fetch_neighbor_chunks(self, repository_id: uuid.UUID, file_path: str) -> list[dict]:
        """
        Fetches adjacent chunks in a file to enable neighborhood context expansion.
        """
        query = """
        SELECT 
            chunk_id, document_id, file_path, start_line, end_line, chunk_type, source_phase, content, metadata
        FROM repository_embeddings
        WHERE repository_id = :repository_id AND file_path = :file_path
        """
        try:
            res = self.db.execute(
                text(query),
                {
                    "repository_id": repository_id,
                    "file_path": file_path
                }
            )
            
            chunks = []
            for row in res:
                chunks.append({
                    "chunk_id": row[0],
                    "document_id": row[1],
                    "repo_id": str(repository_id),
                    "file_path": row[2],
                    "start_line": int(row[3]) if row[3] is not None else 1,
                    "end_line": int(row[4]) if row[4] is not None else 1,
                    "chunk_type": row[5],
                    "source_phase": row[6],
                    "content": row[7],
                    "metadata": row[8] or {}
                })
            return chunks
        except Exception as e:
            logger.error(f"Failed to fetch adjacent chunks: {e}")
            return []

    def fetch_neighbor_chunks_multiple(self, repository_id: uuid.UUID, file_paths: list[str]) -> dict[str, list[dict]]:
        """
        Fetches adjacent chunks for multiple files in a repository to enable neighborhood context expansion in a single roundtrip.
        """
        if not file_paths:
            return {}
        query = """
        SELECT 
            chunk_id, document_id, file_path, start_line, end_line, chunk_type, source_phase, content, metadata
        FROM repository_embeddings
        WHERE repository_id = :repository_id AND file_path IN :file_paths
        """
        result_map = {}
        try:
            res = self.db.execute(
                text(query),
                {
                    "repository_id": repository_id,
                    "file_paths": tuple(file_paths)
                }
            )
            for row in res:
                chunk_id, doc_id, file_path, start_line, end_line, chunk_type, source_phase, content, metadata = row
                chunk_dict = {
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "repo_id": str(repository_id),
                    "file_path": file_path,
                    "start_line": int(start_line) if start_line is not None else 1,
                    "end_line": int(end_line) if end_line is not None else 1,
                    "chunk_type": chunk_type,
                    "source_phase": source_phase,
                    "content": content,
                    "metadata": metadata or {}
                }
                if file_path not in result_map:
                    result_map[file_path] = []
                result_map[file_path].append(chunk_dict)
            return result_map
        except Exception as e:
            logger.error(f"Failed to fetch multiple neighbor chunks: {e}")
            return {}

    def count_repository_vectors(self, repository_id: uuid.UUID) -> int:
        """
        Returns the number of indexed chunks for a repository.
        """
        query = "SELECT COUNT(*) FROM repository_embeddings WHERE repository_id = :repository_id"
        try:
            res = self.db.execute(text(query), {"repository_id": repository_id})
            return res.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to count repository vectors: {e}")
            return 0
