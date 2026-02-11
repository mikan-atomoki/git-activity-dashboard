"""ダッシュボードエンドポイント。

コミット推移、言語比率、リポジトリ比率、ヒートマップ、
技術トレンド、カテゴリ比率、統計カードのAPIを提供する。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models import User
from app.schemas.dashboard import (
    CategoryBreakdownResponse,
    CommitActivityQuery,
    CommitActivityResponse,
    DashboardStatsResponse,
    HourlyHeatmapResponse,
    LanguageBreakdownResponse,
    RepoBreakdownResponse,
    RepoTechStacksResponse,
    TechTrendsResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter()


# ---------------------------------------------------------------------------
# 統計カード
# ---------------------------------------------------------------------------


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="ダッシュボード統計カード",
)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardStatsResponse:
    """ダッシュボード統計カード用データを取得する。

    全コミット数、アクティブリポジトリ数、連続コミット日数、
    最も使用している言語、前月比を返す。

    Args:
        current_user: 認証済みユーザー。
        session: データベースセッション。

    Returns:
        統計カードレスポンス。
    """
    service = DashboardService(session)
    return await service.get_dashboard_stats(user_id=current_user.user_id)


# ---------------------------------------------------------------------------
# コミット推移
# ---------------------------------------------------------------------------


@router.get(
    "/commit-activity",
    response_model=CommitActivityResponse,
    summary="コミット推移データ",
)
async def get_commit_activity(
    period: str = Query(
        default="daily",
        regex="^(daily|weekly|monthly)$",
        description="集計単位",
    ),
    start_date: date | None = Query(default=None, description="開始日"),
    end_date: date | None = Query(default=None, description="終了日"),
    repo_ids: list[int] | None = Query(
        default=None,
        description="フィルタ対象リポジトリIDリスト",
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CommitActivityResponse:
    """コミット推移データを取得する。

    期間単位（daily/weekly/monthly）に応じた集計結果を返す。

    Args:
        period: 集計単位。
        start_date: 開始日（未指定時は90日前）。
        end_date: 終了日（未指定時は今日）。
        repo_ids: フィルタ対象リポジトリIDリスト。
        current_user: 認証済みユーザー。
        session: データベースセッション。

    Returns:
        コミット推移レスポンス。
    """
    query = CommitActivityQuery(
        period=period,  # type: ignore[arg-type]
        start_date=start_date,
        end_date=end_date,
        repo_ids=repo_ids,
    )
    service = DashboardService(session)
    return await service.get_commit_activity(
        user_id=current_user.user_id,
        query=query,
    )


# ---------------------------------------------------------------------------
# 言語比率
# ---------------------------------------------------------------------------


@router.get(
    "/language-breakdown",
    response_model=LanguageBreakdownResponse,
    summary="言語比率",
)
async def get_language_breakdown(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LanguageBreakdownResponse:
    """アクティブリポジトリの言語比率を取得する。

    Args:
        current_user: 認証済みユーザー。
        session: データベースセッション。

    Returns:
        言語比率レスポンス。
    """
    service = DashboardService(session)
    return await service.get_language_breakdown(user_id=current_user.user_id)


# ---------------------------------------------------------------------------
# リポジトリ別コミット比率
# ---------------------------------------------------------------------------


@router.get(
    "/repository-breakdown",
    response_model=RepoBreakdownResponse,
    summary="リポジトリ別コミット比率",
)
async def get_repository_breakdown(
    start_date: date | None = Query(default=None, description="開始日"),
    end_date: date | None = Query(default=None, description="終了日"),
    limit: int = Query(default=10, ge=1, le=50, description="取得件数上限"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RepoBreakdownResponse:
    """リポジトリ別コミット比率を取得する。

    Args:
        start_date: 開始日。
        end_date: 終了日。
        limit: 返却件数上限。
        current_user: 認証済みユーザー。
        session: データベースセッション。

    Returns:
        リポジトリ別コミット比率レスポンス。
    """
    service = DashboardService(session)
    return await service.get_repo_breakdown(
        user_id=current_user.user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# 時間帯ヒートマップ
# ---------------------------------------------------------------------------


@router.get(
    "/hourly-heatmap",
    response_model=HourlyHeatmapResponse,
    summary="時間帯ヒートマップ",
)
async def get_hourly_heatmap(
    start_date: date | None = Query(default=None, description="開始日"),
    end_date: date | None = Query(default=None, description="終了日"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> HourlyHeatmapResponse:
    """時間帯ヒートマップ用データを取得する。

    7x24の完全グリッド（0埋め）を返す。

    Args:
        start_date: 開始日。
        end_date: 終了日。
        current_user: 認証済みユーザー。
        session: データベースセッション。

    Returns:
        ヒートマップレスポンス。
    """
    service = DashboardService(session)
    return await service.get_hourly_heatmap(
        user_id=current_user.user_id,
        start_date=start_date,
        end_date=end_date,
    )


# ---------------------------------------------------------------------------
# 技術トレンド
# ---------------------------------------------------------------------------


@router.get(
    "/tech-trends",
    response_model=TechTrendsResponse,
    summary="技術トレンド",
)
async def get_tech_trends(
    start_date: date | None = Query(default=None, description="開始日"),
    end_date: date | None = Query(default=None, description="終了日"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TechTrendsResponse:
    """技術トレンドデータを取得する。

    GeminiAnalysisの技術タグを週単位で集計する。

    Args:
        start_date: 開始日。
        end_date: 終了日。
        current_user: 認証済みユーザー。
        session: データベースセッション。

    Returns:
        技術トレンドレスポンス。
    """
    service = DashboardService(session)
    return await service.get_tech_trends(
        user_id=current_user.user_id,
        start_date=start_date,
        end_date=end_date,
    )


# ---------------------------------------------------------------------------
# 作業カテゴリ比率
# ---------------------------------------------------------------------------


@router.get(
    "/category-breakdown",
    response_model=CategoryBreakdownResponse,
    summary="作業カテゴリ比率",
)
async def get_category_breakdown(
    start_date: date | None = Query(default=None, description="開始日"),
    end_date: date | None = Query(default=None, description="終了日"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CategoryBreakdownResponse:
    """作業カテゴリ比率を取得する。

    GeminiAnalysisのwork_categoryをGROUP BYで集計する。

    Args:
        start_date: 開始日。
        end_date: 終了日。
        current_user: 認証済みユーザー。
        session: データベースセッション。

    Returns:
        カテゴリ比率レスポンス。
    """
    service = DashboardService(session)
    return await service.get_category_breakdown(
        user_id=current_user.user_id,
        start_date=start_date,
        end_date=end_date,
    )


# ---------------------------------------------------------------------------
# リポジトリ技術スタック
# ---------------------------------------------------------------------------


@router.get(
    "/repo-tech-stacks",
    response_model=RepoTechStacksResponse,
    summary="リポジトリ技術スタック一覧",
)
async def get_repo_tech_stacks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RepoTechStacksResponse:
    """アクティブリポジトリの技術スタック分析結果を返す。

    repo_metadata の tech_analysis フィールドから読み取る。
    Sync 実行時に Gemini で分析した結果が格納される。

    Args:
        current_user: 認証済みユーザー。
        session: データベースセッション。

    Returns:
        リポジトリ技術スタック一覧レスポンス。
    """
    service = DashboardService(session)
    return await service.get_repo_tech_stacks(user_id=current_user.user_id)
