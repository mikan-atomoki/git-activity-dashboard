"""Tests for ``/api/v1/dashboard`` endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.dashboard import (
    CategoryBreakdownResponse,
    CommitActivityResponse,
    DashboardStatsResponse,
    HeatmapCell,
    HourlyHeatmapResponse,
    LanguageBreakdownResponse,
    RepoBreakdownResponse,
    RepoTechStacksResponse,
    TechTrendsResponse,
)
from tests.conftest import TEST_USER_ID


# ---------------------------------------------------------------------------
# Helper: set up get_current_user to succeed
# ---------------------------------------------------------------------------


def _setup_auth(mock_session: AsyncMock, test_user: MagicMock) -> None:
    """Configure mock_session so that ``get_current_user`` resolves to
    ``test_user``."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = test_user
    mock_session.execute.return_value = mock_result


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/stats
# ---------------------------------------------------------------------------


class TestDashboardStats:
    """GET /api/v1/dashboard/stats"""

    @pytest.mark.asyncio
    async def test_stats_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_session: AsyncMock,
        test_user: MagicMock,
    ) -> None:
        _setup_auth(mock_session, test_user)

        fake_stats = DashboardStatsResponse(
            total_commits=150,
            active_repos=5,
            current_streak=7,
            top_language="Python",
            commit_change_pct=12.5,
        )

        with patch("app.api.v1.dashboard.DashboardService") as MockSvc:
            instance = AsyncMock()
            instance.get_dashboard_stats.return_value = fake_stats
            MockSvc.return_value = instance

            resp = await async_client.get(
                "/api/v1/dashboard/stats",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_commits"] == 150
        assert body["active_repos"] == 5
        assert body["current_streak"] == 7
        assert body["top_language"] == "Python"
        assert body["commit_change_pct"] == 12.5

    @pytest.mark.asyncio
    async def test_stats_no_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/commit-activity
# ---------------------------------------------------------------------------


class TestCommitActivity:
    """GET /api/v1/dashboard/commit-activity"""

    @pytest.mark.asyncio
    async def test_commit_activity_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_session: AsyncMock,
        test_user: MagicMock,
    ) -> None:
        _setup_auth(mock_session, test_user)

        fake = CommitActivityResponse(
            period="daily",
            data=[],
            total_commits=0,
        )

        with patch("app.api.v1.dashboard.DashboardService") as MockSvc:
            instance = AsyncMock()
            instance.get_commit_activity.return_value = fake
            MockSvc.return_value = instance

            resp = await async_client.get(
                "/api/v1/dashboard/commit-activity",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["period"] == "daily"
        assert body["total_commits"] == 0

    @pytest.mark.asyncio
    async def test_commit_activity_no_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/api/v1/dashboard/commit-activity")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/language-breakdown
# ---------------------------------------------------------------------------


class TestLanguageBreakdown:
    """GET /api/v1/dashboard/language-breakdown"""

    @pytest.mark.asyncio
    async def test_language_breakdown_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_session: AsyncMock,
        test_user: MagicMock,
    ) -> None:
        _setup_auth(mock_session, test_user)

        fake = LanguageBreakdownResponse(data=[])

        with patch("app.api.v1.dashboard.DashboardService") as MockSvc:
            instance = AsyncMock()
            instance.get_language_breakdown.return_value = fake
            MockSvc.return_value = instance

            resp = await async_client.get(
                "/api/v1/dashboard/language-breakdown",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @pytest.mark.asyncio
    async def test_language_breakdown_no_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/api/v1/dashboard/language-breakdown")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/repository-breakdown
# ---------------------------------------------------------------------------


class TestRepoBreakdown:
    """GET /api/v1/dashboard/repository-breakdown"""

    @pytest.mark.asyncio
    async def test_repo_breakdown_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_session: AsyncMock,
        test_user: MagicMock,
    ) -> None:
        _setup_auth(mock_session, test_user)

        fake = RepoBreakdownResponse(data=[], total_commits=0)

        with patch("app.api.v1.dashboard.DashboardService") as MockSvc:
            instance = AsyncMock()
            instance.get_repo_breakdown.return_value = fake
            MockSvc.return_value = instance

            resp = await async_client.get(
                "/api/v1/dashboard/repository-breakdown",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["total_commits"] == 0

    @pytest.mark.asyncio
    async def test_repo_breakdown_no_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/api/v1/dashboard/repository-breakdown")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/hourly-heatmap
# ---------------------------------------------------------------------------


class TestHourlyHeatmap:
    """GET /api/v1/dashboard/hourly-heatmap"""

    @pytest.mark.asyncio
    async def test_hourly_heatmap_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_session: AsyncMock,
        test_user: MagicMock,
    ) -> None:
        _setup_auth(mock_session, test_user)

        fake = HourlyHeatmapResponse(data=[], max_count=0)

        with patch("app.api.v1.dashboard.DashboardService") as MockSvc:
            instance = AsyncMock()
            instance.get_hourly_heatmap.return_value = fake
            MockSvc.return_value = instance

            resp = await async_client.get(
                "/api/v1/dashboard/hourly-heatmap",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["max_count"] == 0

    @pytest.mark.asyncio
    async def test_hourly_heatmap_no_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/api/v1/dashboard/hourly-heatmap")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/tech-trends
# ---------------------------------------------------------------------------


class TestTechTrends:
    """GET /api/v1/dashboard/tech-trends"""

    @pytest.mark.asyncio
    async def test_tech_trends_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_session: AsyncMock,
        test_user: MagicMock,
    ) -> None:
        _setup_auth(mock_session, test_user)

        fake = TechTrendsResponse(data=[])

        with patch("app.api.v1.dashboard.DashboardService") as MockSvc:
            instance = AsyncMock()
            instance.get_tech_trends.return_value = fake
            MockSvc.return_value = instance

            resp = await async_client.get(
                "/api/v1/dashboard/tech-trends",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @pytest.mark.asyncio
    async def test_tech_trends_no_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/api/v1/dashboard/tech-trends")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/category-breakdown
# ---------------------------------------------------------------------------


class TestCategoryBreakdown:
    """GET /api/v1/dashboard/category-breakdown"""

    @pytest.mark.asyncio
    async def test_category_breakdown_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_session: AsyncMock,
        test_user: MagicMock,
    ) -> None:
        _setup_auth(mock_session, test_user)

        fake = CategoryBreakdownResponse(data=[])

        with patch("app.api.v1.dashboard.DashboardService") as MockSvc:
            instance = AsyncMock()
            instance.get_category_breakdown.return_value = fake
            MockSvc.return_value = instance

            resp = await async_client.get(
                "/api/v1/dashboard/category-breakdown",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @pytest.mark.asyncio
    async def test_category_breakdown_no_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/api/v1/dashboard/category-breakdown")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/repo-tech-stacks
# ---------------------------------------------------------------------------


class TestRepoTechStacks:
    """GET /api/v1/dashboard/repo-tech-stacks"""

    @pytest.mark.asyncio
    async def test_repo_tech_stacks_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
        mock_session: AsyncMock,
        test_user: MagicMock,
    ) -> None:
        _setup_auth(mock_session, test_user)

        fake = RepoTechStacksResponse(data=[])

        with patch("app.api.v1.dashboard.DashboardService") as MockSvc:
            instance = AsyncMock()
            instance.get_repo_tech_stacks.return_value = fake
            MockSvc.return_value = instance

            resp = await async_client.get(
                "/api/v1/dashboard/repo-tech-stacks",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @pytest.mark.asyncio
    async def test_repo_tech_stacks_no_auth(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/api/v1/dashboard/repo-tech-stacks")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Health check (no auth required)
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """GET /health"""

    @pytest.mark.asyncio
    async def test_health(self, async_client: AsyncClient) -> None:
        resp = await async_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
