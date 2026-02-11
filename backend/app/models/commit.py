"""Commit ORM model (range-partitioned by committed_at)."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Integer, String, TIMESTAMP, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Commit(Base):
    """Git commit record.

    The underlying ``commits`` table is range-partitioned on
    ``committed_at`` (monthly).  Partition child tables must be created
    via custom Alembic migrations.
    """

    __tablename__ = "commits"
    __table_args__ = (
        {
            "postgresql_partition_by": "RANGE (committed_at)",
        },
    )

    commit_id: Mapped[int] = mapped_column(
        BigInteger,
        autoincrement=True,
    )
    repo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("repositories.repo_id"),
        nullable=False,
    )
    github_commit_sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    committed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    additions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    deletions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    changed_files: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Composite primary key for partitioning
    __mapper_args__ = {
        "primary_key": [commit_id, committed_at],
    }

    # --- Relationships ---
    repository: Mapped["Repository"] = relationship(  # noqa: F821
        back_populates="commits",
    )

    def __repr__(self) -> str:
        return (
            f"<Commit(commit_id={self.commit_id}, "
            f"sha={self.github_commit_sha!r})>"
        )
