"""Tests for ``/api/v1/auth`` endpoints — register, login, me."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import TEST_USER_ID, TEST_USERNAME


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------


class TestRegister:
    """POST /api/v1/auth/register"""

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        async_client: AsyncClient,
        mock_session: AsyncMock,
        test_user: MagicMock,
    ) -> None:
        """Successful registration returns 201 with user + tokens."""
        # Make the duplicate-check query return no existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # After session.refresh(user), the user object should look valid.
        # We patch register_user to return our test_user directly.
        with patch(
            "app.api.v1.auth.register_user",
            new_callable=AsyncMock,
            return_value=test_user,
        ):
            resp = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "username": "newuser",
                    "password": "securepassword123",
                    "email": "new@example.com",
                },
            )

        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["user"]["github_login"] == TEST_USERNAME
        assert body["user"]["user_id"] == TEST_USER_ID

    @pytest.mark.asyncio
    async def test_register_duplicate_user(
        self,
        async_client: AsyncClient,
        mock_session: AsyncMock,
        test_user: MagicMock,
    ) -> None:
        """Registering an existing username returns 409."""
        from app.core.exceptions import AppException

        with patch(
            "app.api.v1.auth.register_user",
            new_callable=AsyncMock,
            side_effect=AppException(status_code=409, detail="User 'testuser' already exists"),
        ):
            resp = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "username": "testuser",
                    "password": "somepassword1",
                },
            )

        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_short_password(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Password shorter than 8 chars is rejected by schema validation (422)."""
        resp = await async_client.post(
            "/api/v1/auth/register",
            json={
                "username": "someone",
                "password": "short",
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    """POST /api/v1/auth/login"""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        async_client: AsyncClient,
        mock_session: AsyncMock,
        test_user: MagicMock,
    ) -> None:
        """Valid credentials return access + refresh tokens."""
        with patch(
            "app.api.v1.auth.authenticate_user",
            new_callable=AsyncMock,
            return_value=test_user,
        ):
            resp = await async_client.post(
                "/api/v1/auth/login",
                data={
                    "username": TEST_USERNAME,
                    "password": "correctpassword",
                },
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert "expires_in" in body

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(
        self,
        async_client: AsyncClient,
        mock_session: AsyncMock,
    ) -> None:
        """Wrong password returns 401."""
        from app.core.exceptions import AuthenticationError

        with patch(
            "app.api.v1.auth.authenticate_user",
            new_callable=AsyncMock,
            side_effect=AuthenticationError("Invalid username or password"),
        ):
            resp = await async_client.post(
                "/api/v1/auth/login",
                data={
                    "username": "baduser",
                    "password": "wrongpassword",
                },
            )

        assert resp.status_code == 401
        assert "Invalid" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me  (inferred from get_current_user dependency)
# ---------------------------------------------------------------------------
# Note: there is no explicit /me endpoint in the router we read, but the
# common pattern is tested via the get_current_user dependency used by
# other protected endpoints. We test the dependency indirectly via
# /api/v1/dashboard/stats.
# ---------------------------------------------------------------------------


class TestAuthRequired:
    """Verify that protected endpoints reject unauthenticated requests."""

    @pytest.mark.asyncio
    async def test_no_token_returns_401(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Calling a protected endpoint without a token yields 401."""
        resp = await async_client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(
        self,
        async_client: AsyncClient,
    ) -> None:
        """An invalid Bearer token yields 401."""
        resp = await async_client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_accepted(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_session: AsyncMock,
        test_user: MagicMock,
    ) -> None:
        """A valid token passes the auth check (the endpoint may still
        fail downstream, but it should NOT be a 401)."""
        # get_current_user will call session.execute to look up the user.
        # We make it return our test_user.
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_user
        mock_session.execute.return_value = mock_result

        # Patch DashboardService to avoid real DB queries.
        with patch(
            "app.api.v1.dashboard.DashboardService"
        ) as MockService:
            svc_instance = AsyncMock()
            svc_instance.get_dashboard_stats.return_value = {
                "total_commits": 0,
                "active_repos": 0,
                "current_streak": 0,
                "top_language": None,
                "commit_change_pct": None,
            }
            MockService.return_value = svc_instance

            resp = await async_client.get(
                "/api/v1/dashboard/stats",
                headers=auth_headers,
            )

        # We should NOT get 401.  The response might be 200 or 500
        # depending on serialisation, but definitely not 401.
        assert resp.status_code != 401
