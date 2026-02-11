"""HourlyActivity ORM model."""

from datetime import date

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HourlyActivity(Base):
    """Pre-aggregated hourly activity counters per user.

    Used for heatmap / time-of-day visualisations.
    """

    __tablename__ = "hourly_activity"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "activity_date",
            "hour_of_day",
            name="uq_hourly_activity_user_date_hour",
        ),
        CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6",
            name="ck_hourly_activity_day_of_week",
        ),
        CheckConstraint(
            "hour_of_day >= 0 AND hour_of_day <= 23",
            name="ck_hourly_activity_hour_of_day",
        ),
    )

    activity_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id"),
        nullable=False,
    )
    activity_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    day_of_week: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )
    hour_of_day: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )
    commit_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    pr_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
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

    # --- Relationships ---
    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="hourly_activities",
    )

    def __repr__(self) -> str:
        return (
            f"<HourlyActivity(activity_id={self.activity_id}, "
            f"user_id={self.user_id}, date={self.activity_date}, "
            f"hour={self.hour_of_day})>"
        )
