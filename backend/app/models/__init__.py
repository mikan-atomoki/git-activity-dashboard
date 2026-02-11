"""ORM models package.

Importing this module ensures every model is registered with the
SQLAlchemy ``Base.metadata`` so that Alembic autogenerate can detect
all tables.
"""

from app.models.commit import Commit
from app.models.gemini_analysis import GeminiAnalysis
from app.models.hourly_activity import HourlyActivity
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.sync_job import SyncJob
from app.models.user import User

__all__ = [
    "Commit",
    "GeminiAnalysis",
    "HourlyActivity",
    "PullRequest",
    "Repository",
    "SyncJob",
    "User",
]
