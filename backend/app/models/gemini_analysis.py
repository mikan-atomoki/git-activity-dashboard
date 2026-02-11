"""GeminiAnalysis ORM model (range-partitioned by analyzed_at)."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Numeric, String, TIMESTAMP, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GeminiAnalysis(Base):
    """AI-generated analysis of a commit or pull request.

    The underlying ``gemini_analyses`` table is range-partitioned on
    ``analyzed_at`` (monthly).  Partition child tables must be created
    via custom Alembic migrations.
    """

    __tablename__ = "gemini_analyses"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('commit', 'pull_request', 'weekly_summary', 'monthly_summary')",
            name="ck_gemini_analyses_source_type",
        ),
        {
            "postgresql_partition_by": "RANGE (analyzed_at)",
        },
    )

    analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        autoincrement=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    source_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    repo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("repositories.repo_id"),
        nullable=False,
    )
    tech_tags: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="'[]'",
    )
    work_category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    complexity_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 1),
        nullable=True,
    )
    raw_response: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    analyzed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Composite primary key for partitioning
    __mapper_args__ = {
        "primary_key": [analysis_id, analyzed_at],
    }

    # --- Relationships ---
    repository: Mapped["Repository"] = relationship(  # noqa: F821
        back_populates="gemini_analyses",
    )

    def __repr__(self) -> str:
        return (
            f"<GeminiAnalysis(analysis_id={self.analysis_id}, "
            f"source_type={self.source_type!r}, source_id={self.source_id})>"
        )
