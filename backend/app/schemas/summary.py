"""サマリー関連のPydanticスキーマ。

週次・月次のAI生成サマリーを返却するためのスキーマを定義する。
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 週次サマリー
# ---------------------------------------------------------------------------

class WeeklySummary(BaseModel):
    """1週間分のサマリー。"""

    week_start: date
    week_end: date
    total_commits: int
    total_prs_merged: int
    highlight: str = Field(..., description="ハイライト（1文）")
    key_achievements: list[str] = Field(default_factory=list)
    technologies_used: list[str] = Field(default_factory=list)
    generated_at: datetime | None = None


class WeeklySummaryResponse(BaseModel):
    """週次サマリーレスポンス。"""

    summaries: list[WeeklySummary]


# ---------------------------------------------------------------------------
# 月次サマリー
# ---------------------------------------------------------------------------

class MonthlySummary(BaseModel):
    """1か月分のサマリー。"""

    year: int
    month: int
    total_commits: int
    active_repos: list[str] = Field(default_factory=list)
    narrative: str = Field(..., description="月次ナラティブ")
    growth_areas: list[str] = Field(default_factory=list)
    generated_at: datetime | None = None


class MonthlySummaryResponse(BaseModel):
    """月次サマリーレスポンス。"""

    summaries: list[MonthlySummary]
