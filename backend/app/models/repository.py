"""Repository ORM model."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, TIMESTAMP, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Repository(Base):
    """GitHub repository tracked by a user."""

    __tablename__ = "repositories"

    repo_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id"),
        nullable=False,
    )
    github_repo_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    primary_language: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    is_private: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )
    repo_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # --- Relationships ---
    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="repositories",
    )
    commits: Mapped[list["Commit"]] = relationship(  # noqa: F821
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    pull_requests: Mapped[list["PullRequest"]] = relationship(  # noqa: F821
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    gemini_analyses: Mapped[list["GeminiAnalysis"]] = relationship(  # noqa: F821
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    sync_jobs: Mapped[list["SyncJob"]] = relationship(  # noqa: F821
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Repository(repo_id={self.repo_id}, full_name={self.full_name!r})>"
