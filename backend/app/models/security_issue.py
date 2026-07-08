import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class SecurityIssue(Base):
    __tablename__ = "security_issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    file_path = Column(String, nullable=False)
    line_number = Column(Integer, nullable=True)
    severity = Column(String, nullable=False)  # Critical, High, Medium, Low
    category = Column(String, nullable=False)  # Secrets, Dependencies, Injection, etc.
    title = Column(String, nullable=False)
    evidence = Column(String, nullable=False)
    snippet = Column(String, nullable=True)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    repository = relationship("Repository", back_populates="security_issues")
