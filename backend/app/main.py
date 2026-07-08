from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints.health import router as health_router
from app.api.endpoints.repositories import router as repositories_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Server Shutdown Crash Recovery & Database Schema Initializations.
    """
    import logging
    from app.db.session import SessionLocal
    from app.models.repository import Repository, RepositoryStatus
    from app.repositories.vector_repository import VectorRepository

    logger = logging.getLogger("app.main")
    logger.info("Running startup diagnostics and crash recovery...")
    db = SessionLocal()
    try:
        # 1. Initialize pgvector Table and Index (Component 4 & 5)
        logger.info("Verifying/Initializing pgvector extensions and tables...")
        vector_repo = VectorRepository(db)
        vector_repo.ensure_vector_table(dimension=settings.EMBEDDING_DIMENSION)

        # 2. Find stuck deterministic ingestion jobs
        stuck_repos = db.query(Repository).filter(
            Repository.status.in_([
                RepositoryStatus.CLONING,
                RepositoryStatus.PARSING,
                RepositoryStatus.DETECTING_TECHNOLOGIES,
                RepositoryStatus.ANALYZING,
                RepositoryStatus.FINALIZING
            ])
        ).all()
        for repo in stuck_repos:
            logger.warning(f"Recovering repository {repo.id}: Ingestion was interrupted.")
            repo.status = RepositoryStatus.FAILED
            repo.status_message = "Ingestion failed"
            repo.error_message = "Ingestion interrupted due to server shutdown"
            
        # 3. Find stuck Knowledge indexing jobs
        stuck_kb_repos = db.query(Repository).filter(Repository.knowledge_status == "indexing").all()
        for repo in stuck_kb_repos:
            logger.warning(f"Recovering repository {repo.id} Knowledge Base status: Compilation was interrupted.")
            repo.knowledge_status = "interrupted"
            repo.status_message = "Knowledge build interrupted"
            
        if stuck_repos or stuck_kb_repos:
            db.commit()
            logger.info(f"Crash recovery complete. Cleaned up {len(stuck_repos)} ingestion tasks and {len(stuck_kb_repos)} indexing tasks.")
            
        # 4. Connection pool pre-heating/warm-up
        logger.info("Pre-heating database connection pool...")
        from concurrent.futures import ThreadPoolExecutor
        from sqlalchemy import text
        def warm_connection():
            w_db = SessionLocal()
            try:
                w_db.execute(text("SELECT 1"))
            except Exception as e:
                logger.warning(f"Connection warm-up error: {e}")
            finally:
                w_db.close()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(warm_connection) for _ in range(5)]
            for f in futures:
                f.result()
        logger.info("Database connection pool warmed up successfully.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during startup crash recovery / pgvector checks: {e}")
    finally:
        db.close()
    
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set CORS enabled origins
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routers under the API version prefix
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(repositories_router, prefix=settings.API_V1_STR)

# Also map health check at root for convenience
app.include_router(health_router)
