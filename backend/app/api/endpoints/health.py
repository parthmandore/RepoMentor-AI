from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import settings

router = APIRouter()

@router.get("/health")
def check_health(db: Session = Depends(get_db)):
    """
    Render Health & Liveness probe. Runs fast SELECT 1 with no auth.
    """
    db_ok = True
    db_err = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_ok = False
        db_err = f"{type(e).__name__}: {str(e)}"

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "repomentor-api",
        "database": "connected" if db_ok else "disconnected",
        "database_error": db_err
    }

@router.get("/ready")
def check_readiness(response: Response, db: Session = Depends(get_db)):
    """
    Readiness probe. Checks Postgres database connectivity and LLM configuration.
    """
    postgres_ok = False
    groq_ok = False
    pg_error = None

    # Check Postgres
    try:
        db.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception as e:
        pg_error = f"{type(e).__name__}: {str(e)}"

    # Check Groq API configuration status
    if settings.GROQ_API_KEY:
        groq_ok = True

    all_ok = postgres_ok and groq_ok
    status_str = "healthy" if all_ok else "unhealthy"

    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    # Mask password but show user, host, port, db name for remote debugging
    masked_db = "Not configured"
    try:
        from urllib.parse import urlparse
        parsed = urlparse(settings.DATABASE_URL)
        masked_db = f"{parsed.scheme}://{parsed.username}@{parsed.hostname}:{parsed.port}{parsed.path}"
    except Exception:
        pass

    return {
        "status": status_str,
        "postgres": "healthy" if postgres_ok else "unhealthy",
        "groq_api": "healthy" if groq_ok else "unhealthy",
        "database_target": masked_db,
        "database_error": pg_error
    }
