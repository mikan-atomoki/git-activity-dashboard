"""PullRequest ORM model (range-partitioned by pr_created_at)."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Integer, String, TIMESTAMP, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PullRequest(Base):
    """GitHub pull request record.

    The underlying ``pull_requests`` table is range-partitioned on
    ``pr_created_at`` (monthly).  Partition child tables must be created
    via custom Alembic migrations.
    """

    __tablename__ = "pull_requests"
    __table_args__ = (
        {
            "postgresql_partition_by": "RANGE (pr_created_at)",
        },
    )

    pr_id: Mapped[int] = mapped_column(
        BigInteger,
        autoincrement=True,
    )
    repo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("repositories.repo_id"),
        nullable=False,
    )
    github_pr_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    github_pr_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="'open'",
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
    pr_created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    pr_closed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    merged_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
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
        "primary_key": [pr_id, pr_created_at],
    }

    # --- Relationships ---
    repository: Mapped["Repository"] = relationship(  # noqa: F821
        back_populates="pull_requests",
    )

    def __repr__(self) -> str:
        return (
            f"<PullRequest(pr_id={self.pr_id}, "
            f"number={self.github_pr_number})>"
        )
