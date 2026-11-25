from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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
        from sqlalchemy import text
        w_db = SessionLocal()
        try:
            w_db.execute(text("SELECT 1"))
        except Exception as e:
            logger.warning(f"Connection warm-up error: {e}")
        finally:
            w_db.close()
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
cors_origins = [str(o).rstrip("/") for o in settings.CORS_ORIGINS] if settings.CORS_ORIGINS else []
for origin in ["https://repomentor.netlify.app", "http://localhost:3000", "http://localhost:3010", "http://127.0.0.1:3000", "http://127.0.0.1:3010"]:
    if origin not in cors_origins:
        cors_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging, traceback
    logging.getLogger("app.main").error(f"Global unhandled exception on {request.method} {request.url}: {exc}\n{traceback.format_exc()}")
    origin = request.headers.get("origin")
    resp_headers = {}
    if origin and any(origin == o or o == "*" for o in cors_origins):
        resp_headers["Access-Control-Allow-Origin"] = origin
        resp_headers["Access-Control-Allow-Credentials"] = "true"
    else:
        resp_headers["Access-Control-Allow-Origin"] = "https://repomentor.netlify.app"
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
        headers=resp_headers
    )

# Include API routers under the API version prefix and convenience roots
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(health_router, prefix="/api")
app.include_router(health_router)
app.include_router(repositories_router, prefix=settings.API_V1_STR)

# Also map health check at root for convenience
@app.get("/")
async def root():
    return {
        "project": "RepoMentor AI",
        "status": "Running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }
