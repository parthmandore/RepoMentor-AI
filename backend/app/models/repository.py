import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum, Integer, JSON, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class RepositoryStatus(str, enum.Enum):
    QUEUED = "queued"
    CLONING = "cloning"
    PARSING = "parsing"
    DETECTING_TECHNOLOGIES = "detecting_technologies"
    ANALYZING = "analyzing"
    FINALIZING = "finalizing"
    READY = "ready"
    FAILED = "failed"


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String, unique=True, nullable=False, index=True)
    status = Column(Enum(RepositoryStatus, values_callable=lambda x: [e.value for e in x]), default=RepositoryStatus.QUEUED, nullable=False)
    status_message = Column(String, nullable=True)

    # Discovery Statistics (Phase 2)
    total_files = Column(Integer, default=0, nullable=False)
    total_folders = Column(Integer, default=0, nullable=False)
    text_file_count = Column(Integer, default=0, nullable=False)
    binary_file_count = Column(Integer, default=0, nullable=False)

    # Technology breakdowns
    language_breakdown = Column(JSON, nullable=True)
    tech_stack = Column(JSON, nullable=True)

    # Analysis Health Summary (Phase 3)
    health_score = Column(Integer, default=100, nullable=False)
    health_grade = Column(String, default="A", nullable=False)
    total_lines_of_code = Column(Integer, default=0, nullable=False)
    average_complexity = Column(Float, default=0.0, nullable=False)
    max_complexity = Column(Integer, default=0, nullable=False)
    total_smells = Column(Integer, default=0, nullable=False)
    duplication_percentage = Column(Float, default=0.0, nullable=False)
    files_analyzed = Column(Integer, default=0, nullable=False)
    files_skipped = Column(Integer, default=0, nullable=False)

    # Architecture Summary (Phase 4)
    architecture_score = Column(Integer, default=100, nullable=False)
    architecture_grade = Column(String, default="A", nullable=False)
    architecture_summary = Column(JSON, nullable=True)
    architecture_findings = Column(JSON, nullable=True)

    # Security Summary (Phase 5)
    security_score = Column(Integer, default=100, nullable=False)
    security_grade = Column(String, default="A", nullable=False)
    security_summary = Column(JSON, nullable=True)
    security_findings = Column(JSON, nullable=True)

    # Knowledge Summary (Phase 6)
    knowledge_status = Column(String, default="pending", nullable=False)
    knowledge_summary = Column(JSON, nullable=True)

    # Ingestion Execution Tracking (Phase 2)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Analysis Execution Tracking (Phase 3)
    analysis_started_at = Column(DateTime(timezone=True), nullable=True)
    analysis_completed_at = Column(DateTime(timezone=True), nullable=True)
    analysis_duration_seconds = Column(Float, nullable=True)

    # Error state
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    files = relationship("RepositoryFile", back_populates="repository", cascade="all, delete-orphan")
    smells = relationship("CodeSmell", back_populates="repository", cascade="all, delete-orphan")
    security_issues = relationship("SecurityIssue", back_populates="repository", cascade="all, delete-orphan")
