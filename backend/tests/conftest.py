"""Shared test fixtures.

Provides an async HTTP client backed by the FastAPI app, a mock DB
session, and authentication helpers.  No real database connection is
made -- every test uses mocks.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Environment overrides — must happen BEFORE importing the app so that
# ``pydantic-settings`` picks up the test values instead of trying to
# connect to the real database.
# ---------------------------------------------------------------------------
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only-1234567890abcdef")
os.environ.setdefault("ENCRYPTION_KEY", "aa" * 32)  # 64 hex chars = 32 bytes
os.environ.setdefault("GEMINI_API_KEY", "fake-gemini-key")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test_db",
)

from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402
from app.database import get_session  # noqa: E402

# ---------------------------------------------------------------------------
# Mock database session
# ---------------------------------------------------------------------------


def _make_mock_session() -> AsyncMock:
    """Return an ``AsyncMock`` that behaves like an ``AsyncSession``."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    # .execute() returns a mock Result whose helpers can be customised per-test
    session.execute = AsyncMock()
    return session


@pytest.fixture()
def mock_session() -> AsyncMock:
    """Bare mock session — useful when a test needs to configure
    ``session.execute`` return values itself."""
    return _make_mock_session()


# ---------------------------------------------------------------------------
# Async HTTP client with dependency overrides
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture()
async def async_client(mock_session: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """Yield an ``httpx.AsyncClient`` wired to the FastAPI app.

    ``get_session`` is overridden so that no real DB connection is used.
    """

    async def _override_get_session():  # type: ignore[no-untyped-def]
        yield mock_session

    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test user helpers
# ---------------------------------------------------------------------------

TEST_USER_ID = 42
TEST_USERNAME = "testuser"


@pytest.fixture()
def test_user() -> MagicMock:
    """A mock ``User`` ORM instance."""
    user = MagicMock()
    user.user_id = TEST_USER_ID
    user.github_login = TEST_USERNAME
    user.display_name = "Test User"
    user.avatar_url = None
    user.email = "test@example.com"
    user.password_hash = "fakehash"
    user.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    user.updated_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return user


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    """Return HTTP headers containing a valid Bearer token for
    ``TEST_USER_ID``."""
    token = create_access_token(user_id=TEST_USER_ID)
    return {"Authorization": f"Bearer {token}"}
