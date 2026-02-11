"""ダッシュボード関連のPydanticスキーマ。

コミット推移、言語比率、リポジトリ比率、ヒートマップ、
技術トレンド、カテゴリ比率、統計カード用のスキーマを定義する。
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# クエリパラメータ
# ---------------------------------------------------------------------------

class CommitActivityQuery(BaseModel):
    """コミット推移データ取得用クエリ。"""

    period: Literal["daily", "weekly", "monthly"] = Field(
        default="daily",
        description="集計単位",
    )
    start_date: date | None = Field(
        default=None,
        description="開始日（未指定時は90日前）",
    )
    end_date: date | None = Field(
        default=None,
        description="終了日（未指定時は今日）",
    )
    repo_ids: list[int] | None = Field(
        default=None,
        description="フィルタ対象リポジトリIDリスト",
    )


# ---------------------------------------------------------------------------
# コミット推移
# ---------------------------------------------------------------------------

class CommitActivityPoint(BaseModel):
    """コミット推移の1データポイント。"""

    date: date
    count: int
    additions: int
    deletions: int


class CommitActivityResponse(BaseModel):
    """コミット推移レスポンス。"""

    period: str
    data: list[CommitActivityPoint]
    total_commits: int


# ---------------------------------------------------------------------------
# 言語比率
# ---------------------------------------------------------------------------

class LanguageRatio(BaseModel):
    """言語別比率。"""

    language: str
    percentage: float
    color: str


class LanguageBreakdownResponse(BaseModel):
    """言語比率レスポンス。"""

    data: list[LanguageRatio]


# ---------------------------------------------------------------------------
# リポジトリ別コミット比率
# ---------------------------------------------------------------------------

class RepoRatio(BaseModel):
    """リポジトリ別コミット比率。"""

    repo_id: int
    repo_name: str
    commit_count: int
    percentage: float
    primary_language: str | None


class RepoBreakdownResponse(BaseModel):
    """リポジトリ別コミット比率レスポンス。"""

    data: list[RepoRatio]
    total_commits: int


# ---------------------------------------------------------------------------
# 時間帯ヒートマップ
# ---------------------------------------------------------------------------

class HeatmapCell(BaseModel):
    """ヒートマップの1セル（曜日 x 時間帯）。"""

    day_of_week: int = Field(..., ge=0, le=6, description="曜日（0=月曜〜6=日曜）")
    hour: int = Field(..., ge=0, le=23, description="時間帯（0〜23）")
    count: int


class HourlyHeatmapResponse(BaseModel):
    """時間帯ヒートマップレスポンス。"""

    data: list[HeatmapCell]
    max_count: int


# ---------------------------------------------------------------------------
# 技術トレンド
# ---------------------------------------------------------------------------

class TechTrendItem(BaseModel):
    """技術トレンドの1データポイント。"""

    period_start: date
    tag: str
    count: int


class TechTrendsResponse(BaseModel):
    """技術トレンドレスポンス。"""

    data: list[TechTrendItem]


# ---------------------------------------------------------------------------
# 作業カテゴリ比率
# ---------------------------------------------------------------------------

class CategoryItem(BaseModel):
    """作業カテゴリ別集計。"""

    category: str
    count: int
    percentage: float


class CategoryBreakdownResponse(BaseModel):
    """作業カテゴリ比率レスポンス。"""

    data: list[CategoryItem]


# ---------------------------------------------------------------------------
# ダッシュボード統計カード
# ---------------------------------------------------------------------------

class DashboardStatsResponse(BaseModel):
    """ダッシュボード統計カード用レスポンス。"""

    total_commits: int = Field(..., description="全コミット数")
    active_repos: int = Field(..., description="アクティブリポジトリ数")
    current_streak: int = Field(..., description="連続コミット日数")
    top_language: str | None = Field(default=None, description="最も使用している言語")
    commit_change_pct: float | None = Field(
        default=None,
        description="前月比（パーセント）",
    )
