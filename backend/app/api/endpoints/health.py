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
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "repomentor-api",
        "database": "connected" if db_ok else "disconnected"
    }

@router.get("/ready")
def check_readiness(response: Response, db: Session = Depends(get_db)):
    """
    Readiness probe. Checks Postgres database connectivity and LLM configuration.
    """
    postgres_ok = False
    groq_ok = False

    # Check Postgres
    try:
        db.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception:
        pass

    # Check Groq API configuration status
    if settings.GROQ_API_KEY:
        groq_ok = True

    all_ok = postgres_ok and groq_ok
    status_str = "healthy" if all_ok else "unhealthy"

    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": status_str,
        "postgres": "healthy" if postgres_ok else "unhealthy",
        "groq_api": "healthy" if groq_ok else "unhealthy"
    }
