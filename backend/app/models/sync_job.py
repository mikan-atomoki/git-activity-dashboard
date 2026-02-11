"""SyncJob ORM model."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SyncJob(Base):
    """Background synchronisation job record."""

    __tablename__ = "sync_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_sync_jobs_status",
        ),
    )

    job_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id"),
        nullable=False,
    )
    repo_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("repositories.repo_id"),
        nullable=True,
    )
    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="'pending'",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    items_fetched: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    error_detail: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # --- Relationships ---
    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="sync_jobs",
    )
    repository: Mapped["Repository | None"] = relationship(  # noqa: F821
        back_populates="sync_jobs",
    )

    def __repr__(self) -> str:
        return (
            f"<SyncJob(job_id={self.job_id}, job_type={self.job_type!r}, "
            f"status={self.status!r})>"
        )
