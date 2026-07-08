import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class RepositoryFile(Base):
    __tablename__ = "repository_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    path = Column(String, nullable=False)
    extension = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=False)
    content_hash = Column(String, nullable=False)
    is_text = Column(Boolean, nullable=False, default=True)

    # File-level analysis metrics (Phase 3)
    lines_of_code = Column(Integer, default=0, nullable=False)
    complexity = Column(Integer, default=0, nullable=False)
    code_smells_count = Column(Integer, default=0, nullable=False)
    analysis_metadata = Column(JSON, nullable=True)

    # Architecture Explorer Metrics (Phase 4)
    module_type = Column(String, default="Unknown", nullable=False)
    incoming_dependencies = Column(JSON, default=list, nullable=False)
    outgoing_dependencies = Column(JSON, default=list, nullable=False)
    coupling_score = Column(Integer, default=0, nullable=False)
    instability_score = Column(Float, default=0.0, nullable=False)
    in_dependency_cycle = Column(Boolean, default=False, nullable=False)

    repository = relationship("Repository", back_populates="files")
