"""サマリーエンドポイント。

週次・月次のAI生成サマリーを返却するAPIを提供する。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models import User
from app.schemas.summary import MonthlySummaryResponse, WeeklySummaryResponse
from app.services.summary_service import SummaryService

router = APIRouter()


# ---------------------------------------------------------------------------
# 週次サマリー
# ---------------------------------------------------------------------------


@router.get(
    "/weekly",
    response_model=WeeklySummaryResponse,
    summary="週次サマリー取得",
)
async def get_weekly_summaries(
    week_start: date | None = Query(
        default=None,
        description="基準週の開始日（月曜日）。未指定時は直近の月曜日",
    ),
    count: int = Query(
        default=1,
        ge=1,
        le=12,
        description="取得する週数",
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WeeklySummaryResponse:
    """週次サマリーを取得する。

    DB保存済みのGeminiAnalysisデータから週単位で集計したサマリーを返す。
    データがない場合は空のサマリーを返す。

    Args:
        week_start: 基準週の開始日。
        count: 取得する週数。
        current_user: 認証済みユーザー。
        session: データベースセッション。

    Returns:
        週次サマリーレスポンス。
    """
    service = SummaryService(session)
    return await service.get_weekly_summaries(
        user_id=current_user.user_id,
        week_start=week_start,
        count=count,
    )


# ---------------------------------------------------------------------------
# 月次サマリー
# ---------------------------------------------------------------------------


@router.get(
    "/monthly",
    response_model=MonthlySummaryResponse,
    summary="月次サマリー取得",
)
async def get_monthly_summaries(
    year_month: str | None = Query(
        default=None,
        regex=r"^\d{4}-\d{2}$",
        description="基準年月（YYYY-MM形式）。未指定時は当月",
    ),
    count: int = Query(
        default=1,
        ge=1,
        le=12,
        description="取得する月数",
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MonthlySummaryResponse:
    """月次サマリーを取得する。

    DB保存済みのGeminiAnalysisデータから月単位で集計したサマリーを返す。
    データがない場合は空のサマリーを返す。

    Args:
        year_month: 基準年月（YYYY-MM形式）。
        count: 取得する月数。
        current_user: 認証済みユーザー。
        session: データベースセッション。

    Returns:
        月次サマリーレスポンス。
    """
    service = SummaryService(session)
    return await service.get_monthly_summaries(
        user_id=current_user.user_id,
        year_month=year_month,
        count=count,
    )
