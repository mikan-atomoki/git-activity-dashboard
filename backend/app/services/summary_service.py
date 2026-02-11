"""サマリーデータ取得・生成サービス。

週次・月次のAI生成サマリーをDBから取得する既存機能に加え、
GeminiClientを使用して新規サマリーを生成しgemini_analysesテーブルに
source_type='weekly_summary' / 'monthly_summary' として保存する機能を提供する。
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.external.gemini_client import GeminiClient
from app.models import Commit, GeminiAnalysis, PullRequest, Repository
from app.schemas.summary import (
    MonthlySummary,
    MonthlySummaryResponse,
    WeeklySummary,
    WeeklySummaryResponse,
)

logger = logging.getLogger(__name__)


class SummaryService:
    """サマリー集計クエリおよびAI生成を実行するサービスクラス。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # 週次サマリー（DB集計ベース取得）
    # ------------------------------------------------------------------

    async def get_weekly_summaries(
        self,
        user_id: int,
        week_start: date | None = None,
        count: int = 1,
    ) -> WeeklySummaryResponse:
        """週次サマリーを取得する。

        まずGeminiで生成済みのサマリー（source_type='weekly_summary'）があれば
        それを使用し、なければDB集計ベースでサマリーを構築する。

        ``week_start`` 未指定時は直近の月曜日を基準とする。

        Args:
            user_id: 対象ユーザーID。
            week_start: 基準となる週の開始日（月曜日）。
            count: 取得する週数。

        Returns:
            週次サマリーレスポンス。
        """
        today = date.today()
        if week_start is None:
            # 直近の月曜日
            week_start = today - timedelta(days=today.weekday())

        repo_subq = select(Repository.repo_id).where(
            Repository.user_id == user_id,
        )

        summaries: list[WeeklySummary] = []
        for i in range(count):
            ws = week_start - timedelta(weeks=i)
            we = ws + timedelta(days=6)

            # Gemini生成済みサマリーがあるか確認
            gemini_summary = await self._get_generated_weekly_summary(
                user_id, ws, we,
            )

            if gemini_summary is not None:
                summaries.append(gemini_summary)
                continue

            # DB集計ベースのサマリー構築
            summary = await self._build_weekly_summary_from_db(
                user_id, repo_subq, ws, we,
            )
            summaries.append(summary)

        return WeeklySummaryResponse(summaries=summaries)

    # ------------------------------------------------------------------
    # 月次サマリー（DB集計ベース取得）
    # ------------------------------------------------------------------

    async def get_monthly_summaries(
        self,
        user_id: int,
        year_month: str | None = None,
        count: int = 1,
    ) -> MonthlySummaryResponse:
        """月次サマリーを取得する。

        まずGeminiで生成済みのサマリー（source_type='monthly_summary'）があれば
        それを使用し、なければDB集計ベースでサマリーを構築する。

        ``year_month`` は "YYYY-MM" 形式。未指定時は当月を基準とする。

        Args:
            user_id: 対象ユーザーID。
            year_month: 基準年月（YYYY-MM形式）。
            count: 取得する月数。

        Returns:
            月次サマリーレスポンス。
        """
        today = date.today()
        if year_month:
            parts = year_month.split("-")
            base_year = int(parts[0])
            base_month = int(parts[1])
        else:
            base_year = today.year
            base_month = today.month

        repo_subq = select(Repository.repo_id).where(
            Repository.user_id == user_id,
        )

        summaries: list[MonthlySummary] = []
        for i in range(count):
            # i ヶ月前を計算
            month = base_month - i
            year = base_year
            while month <= 0:
                month += 12
                year -= 1

            # Gemini生成済みサマリーがあるか確認
            gemini_summary = await self._get_generated_monthly_summary(
                user_id, year, month,
            )

            if gemini_summary is not None:
                summaries.append(gemini_summary)
                continue

            # DB集計ベースのサマリー構築
            summary = await self._build_monthly_summary_from_db(
                user_id, repo_subq, year, month,
            )
            summaries.append(summary)

        return MonthlySummaryResponse(summaries=summaries)

    # ------------------------------------------------------------------
    # 週次サマリー生成（Gemini API使用）
    # ------------------------------------------------------------------

    async def generate_weekly_summary(
        self,
        user_id: int,
        week_start: date,
    ) -> dict[str, Any]:
        """指定週のサマリーをGemini APIで生成する。

        1. 該当週のコミット・PR・分析結果を取得
        2. GeminiClient.generate_weekly_summary() を呼ぶ
        3. 結果をgemini_analysesテーブルにsource_type='weekly_summary'で保存

        Args:
            user_id: ユーザーID。
            week_start: 週の開始日（月曜日）。

        Returns:
            生成されたサマリー辞書。
        """
        week_end = week_start + timedelta(days=6)
        week_start_dt = datetime.combine(
            week_start, datetime.min.time(), tzinfo=timezone.utc,
        )
        week_end_dt = datetime.combine(
            week_end, datetime.max.time(), tzinfo=timezone.utc,
        )

        # ユーザーのリポジトリIDを取得
        repo_ids = await self._get_user_repo_ids(user_id)
        if not repo_ids:
            logger.warning("No repositories found for user_id=%d", user_id)
            return {"error": "No repositories found"}

        # 該当週のコミット取得
        commits_data = await self._fetch_commits_for_period(
            repo_ids, week_start_dt, week_end_dt,
        )

        # 該当週のPR取得
        prs_data = await self._fetch_prs_for_period(
            repo_ids, week_start_dt, week_end_dt,
        )

        # 該当週の分析結果取得
        analyses_data = await self._fetch_analyses_for_period(
            repo_ids, week_start_dt, week_end_dt,
        )

        # Gemini APIで週次サマリー生成
        gemini = GeminiClient()
        result = await gemini.generate_weekly_summary(
            commits_data=commits_data,
            prs_data=prs_data,
            analyses_data=analyses_data,
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
        )

        # DB保存 (gemini_analysesテーブルにsource_type='weekly_summary'で保存)
        now = datetime.now(timezone.utc)
        analysis = GeminiAnalysis(
            source_type="weekly_summary",
            source_id=user_id,
            repo_id=repo_ids[0],
            tech_tags=result.technologies_used,
            work_category="summary",
            summary=result.highlight,
            complexity_score=None,
            raw_response={
                "type": "weekly_summary",
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "highlight": result.highlight,
                "key_achievements": result.key_achievements,
                "technologies_used": result.technologies_used,
                "suggestions": result.suggestions,
                "focus_areas": result.focus_areas,
                "commits_count": len(commits_data),
                "prs_count": len(prs_data),
            },
            analyzed_at=now,
        )
        self.session.add(analysis)
        await self.session.flush()

        logger.info(
            "Weekly summary generated for user_id=%d, week=%s~%s",
            user_id,
            week_start.isoformat(),
            week_end.isoformat(),
        )

        return self._format_generated_summary(analysis)

    # ------------------------------------------------------------------
    # 月次サマリー生成（Gemini API使用）
    # ------------------------------------------------------------------

    async def generate_monthly_summary(
        self,
        user_id: int,
        year: int,
        month: int,
    ) -> dict[str, Any]:
        """指定月のサマリーをGemini APIで生成する。

        月内の週次サマリーを集約して月次振り返りを生成する。

        Args:
            user_id: ユーザーID。
            year: 対象年。
            month: 対象月。

        Returns:
            生成されたサマリー辞書。
        """
        repo_ids = await self._get_user_repo_ids(user_id)
        if not repo_ids:
            logger.warning("No repositories found for user_id=%d", user_id)
            return {"error": "No repositories found"}

        # 月の範囲
        month_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            month_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        # 月内の週次サマリーを取得
        weekly_stmt = (
            select(GeminiAnalysis)
            .where(
                and_(
                    GeminiAnalysis.source_type == "weekly_summary",
                    GeminiAnalysis.repo_id.in_(repo_ids),
                    GeminiAnalysis.analyzed_at >= month_start,
                    GeminiAnalysis.analyzed_at < month_end,
                )
            )
            .order_by(GeminiAnalysis.analyzed_at.asc())
        )
        result = await self.session.execute(weekly_stmt)
        weekly_analyses = result.scalars().all()

        weekly_summaries = [
            a.raw_response for a in weekly_analyses if a.raw_response
        ]

        # 月間統計を集計
        month_stats = await self._compute_month_stats(
            repo_ids, month_start, month_end,
        )

        # Gemini APIで月次サマリー生成
        gemini = GeminiClient()
        monthly_result = await gemini.generate_monthly_summary(
            weekly_summaries=weekly_summaries,
            month_stats=month_stats,
        )

        # DB保存
        now = datetime.now(timezone.utc)
        analysis = GeminiAnalysis(
            source_type="monthly_summary",
            source_id=user_id,
            repo_id=repo_ids[0],
            tech_tags=[],
            work_category="summary",
            summary=monthly_result.narrative,
            complexity_score=None,
            raw_response={
                "type": "monthly_summary",
                "year": year,
                "month": month,
                "narrative": monthly_result.narrative,
                "growth_areas": monthly_result.growth_areas,
                "monthly_highlights": monthly_result.monthly_highlights,
                "month_stats": month_stats,
            },
            analyzed_at=now,
        )
        self.session.add(analysis)
        await self.session.flush()

        logger.info(
            "Monthly summary generated for user_id=%d, %04d-%02d",
            user_id,
            year,
            month,
        )

        return self._format_generated_summary(analysis)

    # ------------------------------------------------------------------
    # Internal: Gemini生成済みサマリー取得
    # ------------------------------------------------------------------

    async def _get_generated_weekly_summary(
        self,
        user_id: int,
        ws: date,
        we: date,
    ) -> WeeklySummary | None:
        """Gemini生成済みの週次サマリーを取得する。

        Args:
            user_id: ユーザーID。
            ws: 週の開始日。
            we: 週の終了日。

        Returns:
            存在すればWeeklySummary、なければNone。
        """
        repo_ids = await self._get_user_repo_ids(user_id)
        if not repo_ids:
            return None

        stmt = (
            select(GeminiAnalysis)
            .where(
                and_(
                    GeminiAnalysis.source_type == "weekly_summary",
                    GeminiAnalysis.source_id == user_id,
                    GeminiAnalysis.repo_id.in_(repo_ids),
                )
            )
            .order_by(GeminiAnalysis.analyzed_at.desc())
            .limit(10)
        )
        result = await self.session.execute(stmt)
        analyses = result.scalars().all()

        for analysis in analyses:
            raw = analysis.raw_response or {}
            raw_week_start = raw.get("week_start", "")
            if raw_week_start == ws.isoformat():
                return WeeklySummary(
                    week_start=ws,
                    week_end=we,
                    total_commits=raw.get("commits_count", 0),
                    total_prs_merged=raw.get("prs_count", 0),
                    highlight=raw.get("highlight", analysis.summary),
                    key_achievements=raw.get("key_achievements", []),
                    technologies_used=raw.get("technologies_used", []),
                    generated_at=analysis.analyzed_at,
                )

        return None

    async def _get_generated_monthly_summary(
        self,
        user_id: int,
        year: int,
        month: int,
    ) -> MonthlySummary | None:
        """Gemini生成済みの月次サマリーを取得する。

        Args:
            user_id: ユーザーID。
            year: 対象年。
            month: 対象月。

        Returns:
            存在すればMonthlySummary、なければNone。
        """
        repo_ids = await self._get_user_repo_ids(user_id)
        if not repo_ids:
            return None

        stmt = (
            select(GeminiAnalysis)
            .where(
                and_(
                    GeminiAnalysis.source_type == "monthly_summary",
                    GeminiAnalysis.source_id == user_id,
                    GeminiAnalysis.repo_id.in_(repo_ids),
                )
            )
            .order_by(GeminiAnalysis.analyzed_at.desc())
            .limit(10)
        )
        result = await self.session.execute(stmt)
        analyses = result.scalars().all()

        for analysis in analyses:
            raw = analysis.raw_response or {}
            if raw.get("year") == year and raw.get("month") == month:
                month_start = date(year, month, 1)
                # アクティブリポジトリ名取得
                active_repos_stmt = (
                    select(Repository.full_name)
                    .where(
                        and_(
                            Repository.repo_id.in_(repo_ids),
                            Repository.is_active.is_(True),
                        )
                    )
                )
                repos_result = await self.session.execute(active_repos_stmt)
                active_repos = [row.full_name for row in repos_result.all()]

                return MonthlySummary(
                    year=year,
                    month=month,
                    total_commits=raw.get("month_stats", {}).get(
                        "total_commits", 0,
                    ),
                    active_repos=active_repos,
                    narrative=raw.get("narrative", analysis.summary),
                    growth_areas=raw.get("growth_areas", []),
                    generated_at=analysis.analyzed_at,
                )

        return None

    # ------------------------------------------------------------------
    # Internal: DB集計ベースのサマリー構築
    # ------------------------------------------------------------------

    async def _build_weekly_summary_from_db(
        self,
        user_id: int,
        repo_subq: Any,
        ws: date,
        we: date,
    ) -> WeeklySummary:
        """DB集計からWeeklySummaryを構築する。

        Args:
            user_id: ユーザーID。
            repo_subq: リポジトリIDサブクエリ。
            ws: 週の開始日。
            we: 週の終了日。

        Returns:
            構築されたWeeklySummary。
        """
        # コミット数
        commit_stmt = (
            select(func.count())
            .where(
                Commit.repo_id.in_(repo_subq),
                Commit.committed_at >= ws,
                Commit.committed_at < we + timedelta(days=1),
            )
        )
        commit_result = await self.session.execute(commit_stmt)
        total_commits = commit_result.scalar_one() or 0

        # マージ済みPR数
        pr_stmt = (
            select(func.count())
            .where(
                PullRequest.repo_id.in_(repo_subq),
                PullRequest.merged_at.isnot(None),
                PullRequest.merged_at >= ws,
                PullRequest.merged_at < we + timedelta(days=1),
            )
        )
        pr_result = await self.session.execute(pr_stmt)
        total_prs_merged = pr_result.scalar_one() or 0

        # 技術タグ取得
        tech_stmt = (
            select(
                func.jsonb_array_elements_text(GeminiAnalysis.tech_tags).label(
                    "tag",
                ),
            )
            .where(
                GeminiAnalysis.repo_id.in_(repo_subq),
                GeminiAnalysis.source_type == "commit",
                GeminiAnalysis.analyzed_at >= ws,
                GeminiAnalysis.analyzed_at < we + timedelta(days=1),
            )
            .group_by("tag")
            .order_by(func.count().desc())
            .limit(10)
        )
        tech_result = await self.session.execute(tech_stmt)
        technologies_used = [row.tag for row in tech_result.all()]

        # サマリーテキスト (GeminiAnalysisから最新のものを取得)
        summary_stmt = (
            select(GeminiAnalysis.summary)
            .where(
                GeminiAnalysis.repo_id.in_(repo_subq),
                GeminiAnalysis.source_type == "commit",
                GeminiAnalysis.analyzed_at >= ws,
                GeminiAnalysis.analyzed_at < we + timedelta(days=1),
            )
            .order_by(GeminiAnalysis.analyzed_at.desc())
            .limit(3)
        )
        summary_result = await self.session.execute(summary_stmt)
        summary_rows = summary_result.all()
        key_achievements = [row.summary for row in summary_rows]

        # ハイライト生成
        if total_commits > 0:
            highlight = (
                f"{total_commits}件のコミットと"
                f"{total_prs_merged}件のPRマージを実施"
            )
        else:
            highlight = "この週のアクティビティはありません"

        # analyzed_at (最新の分析日時)
        latest_stmt = (
            select(func.max(GeminiAnalysis.analyzed_at))
            .where(
                GeminiAnalysis.repo_id.in_(repo_subq),
                GeminiAnalysis.analyzed_at >= ws,
                GeminiAnalysis.analyzed_at < we + timedelta(days=1),
            )
        )
        latest_result = await self.session.execute(latest_stmt)
        generated_at = latest_result.scalar_one_or_none()

        return WeeklySummary(
            week_start=ws,
            week_end=we,
            total_commits=total_commits,
            total_prs_merged=total_prs_merged,
            highlight=highlight,
            key_achievements=key_achievements,
            technologies_used=technologies_used,
            generated_at=generated_at,
        )

    async def _build_monthly_summary_from_db(
        self,
        user_id: int,
        repo_subq: Any,
        year: int,
        month: int,
    ) -> MonthlySummary:
        """DB集計からMonthlySummaryを構築する。

        Args:
            user_id: ユーザーID。
            repo_subq: リポジトリIDサブクエリ。
            year: 対象年。
            month: 対象月。

        Returns:
            構築されたMonthlySummary。
        """
        month_start = date(year, month, 1)
        if month == 12:
            month_end_exclusive = date(year + 1, 1, 1)
        else:
            month_end_exclusive = date(year, month + 1, 1)

        # コミット数
        commit_stmt = (
            select(func.count())
            .where(
                Commit.repo_id.in_(repo_subq),
                Commit.committed_at >= month_start,
                Commit.committed_at < month_end_exclusive,
            )
        )
        commit_result = await self.session.execute(commit_stmt)
        total_commits = commit_result.scalar_one() or 0

        # アクティブリポジトリ名
        active_repos_stmt = (
            select(Repository.full_name)
            .join(Commit, Commit.repo_id == Repository.repo_id)
            .where(
                Repository.user_id == user_id,
                Commit.committed_at >= month_start,
                Commit.committed_at < month_end_exclusive,
            )
            .group_by(Repository.full_name)
            .order_by(func.count().desc())
        )
        active_repos_result = await self.session.execute(active_repos_stmt)
        active_repos = [row.full_name for row in active_repos_result.all()]

        # 成長分野: work_category 上位
        growth_stmt = (
            select(GeminiAnalysis.work_category)
            .where(
                GeminiAnalysis.repo_id.in_(repo_subq),
                GeminiAnalysis.source_type == "commit",
                GeminiAnalysis.analyzed_at >= month_start,
                GeminiAnalysis.analyzed_at < month_end_exclusive,
            )
            .group_by(GeminiAnalysis.work_category)
            .order_by(func.count().desc())
            .limit(5)
        )
        growth_result = await self.session.execute(growth_stmt)
        growth_areas = [row.work_category for row in growth_result.all()]

        # ナラティブ生成
        if total_commits > 0:
            narrative = (
                f"{year}年{month}月は{total_commits}件のコミットを行い、"
                f"{len(active_repos)}個のリポジトリで活動しました。"
            )
        else:
            narrative = f"{year}年{month}月のアクティビティはありません。"

        # generated_at
        latest_stmt = (
            select(func.max(GeminiAnalysis.analyzed_at))
            .where(
                GeminiAnalysis.repo_id.in_(repo_subq),
                GeminiAnalysis.analyzed_at >= month_start,
                GeminiAnalysis.analyzed_at < month_end_exclusive,
            )
        )
        latest_result = await self.session.execute(latest_stmt)
        generated_at = latest_result.scalar_one_or_none()

        return MonthlySummary(
            year=year,
            month=month,
            total_commits=total_commits,
            active_repos=active_repos,
            narrative=narrative,
            growth_areas=growth_areas,
            generated_at=generated_at,
        )

    # ------------------------------------------------------------------
    # Internal: Gemini生成用データ取得
    # ------------------------------------------------------------------

    async def _get_user_repo_ids(self, user_id: int) -> list[int]:
        """ユーザーのアクティブなリポジトリIDリストを取得する。

        Args:
            user_id: ユーザーID。

        Returns:
            リポジトリIDのリスト。
        """
        stmt = (
            select(Repository.repo_id)
            .where(
                and_(
                    Repository.user_id == user_id,
                    Repository.is_active.is_(True),
                )
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _fetch_commits_for_period(
        self,
        repo_ids: list[int],
        period_start: datetime,
        period_end: datetime,
    ) -> list[dict[str, Any]]:
        """指定期間のコミットデータを取得する。

        Args:
            repo_ids: リポジトリIDリスト。
            period_start: 期間開始。
            period_end: 期間終了。

        Returns:
            コミット情報辞書のリスト。
        """
        stmt = (
            select(Commit, Repository.full_name)
            .join(Repository, Commit.repo_id == Repository.repo_id)
            .where(
                and_(
                    Commit.repo_id.in_(repo_ids),
                    Commit.committed_at >= period_start,
                    Commit.committed_at <= period_end,
                )
            )
            .order_by(Commit.committed_at.desc())
            .limit(100)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "message": commit.message or "",
                "repo_name": repo_name,
                "additions": commit.additions,
                "deletions": commit.deletions,
                "committed_at": commit.committed_at.isoformat(),
            }
            for commit, repo_name in rows
        ]

    async def _fetch_prs_for_period(
        self,
        repo_ids: list[int],
        period_start: datetime,
        period_end: datetime,
    ) -> list[dict[str, Any]]:
        """指定期間のPRデータを取得する。

        Args:
            repo_ids: リポジトリIDリスト。
            period_start: 期間開始。
            period_end: 期間終了。

        Returns:
            PR情報辞書のリスト。
        """
        stmt = (
            select(PullRequest, Repository.full_name)
            .join(Repository, PullRequest.repo_id == Repository.repo_id)
            .where(
                and_(
                    PullRequest.repo_id.in_(repo_ids),
                    PullRequest.pr_created_at >= period_start,
                    PullRequest.pr_created_at <= period_end,
                )
            )
            .order_by(PullRequest.pr_created_at.desc())
            .limit(50)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "title": pr.title or "",
                "repo_name": repo_name,
                "state": pr.state,
                "additions": pr.additions,
                "deletions": pr.deletions,
            }
            for pr, repo_name in rows
        ]

    async def _fetch_analyses_for_period(
        self,
        repo_ids: list[int],
        period_start: datetime,
        period_end: datetime,
    ) -> list[dict[str, Any]]:
        """指定期間のdiff分析結果を取得する。

        Args:
            repo_ids: リポジトリIDリスト。
            period_start: 期間開始。
            period_end: 期間終了。

        Returns:
            分析結果辞書のリスト。
        """
        stmt = (
            select(GeminiAnalysis)
            .where(
                and_(
                    GeminiAnalysis.source_type == "commit",
                    GeminiAnalysis.repo_id.in_(repo_ids),
                    GeminiAnalysis.analyzed_at >= period_start,
                    GeminiAnalysis.analyzed_at <= period_end,
                )
            )
            .order_by(GeminiAnalysis.analyzed_at.desc())
            .limit(100)
        )
        result = await self.session.execute(stmt)
        analyses = result.scalars().all()

        return [
            {
                "summary": a.summary,
                "work_category": a.work_category,
                "tech_tags": a.tech_tags,
                "complexity_score": float(a.complexity_score)
                if a.complexity_score is not None
                else None,
            }
            for a in analyses
        ]

    async def _compute_month_stats(
        self,
        repo_ids: list[int],
        month_start: datetime,
        month_end: datetime,
    ) -> dict[str, Any]:
        """月間統計情報を集計する。

        Args:
            repo_ids: リポジトリIDリスト。
            month_start: 月の開始日時。
            month_end: 月の終了日時。

        Returns:
            統計情報辞書。
        """
        # コミット数
        commit_count_stmt = (
            select(func.count())
            .select_from(Commit)
            .where(
                and_(
                    Commit.repo_id.in_(repo_ids),
                    Commit.committed_at >= month_start,
                    Commit.committed_at < month_end,
                )
            )
        )
        commit_count_result = await self.session.execute(commit_count_stmt)
        total_commits = commit_count_result.scalar() or 0

        # additions/deletions合計
        lines_stmt = (
            select(
                func.coalesce(func.sum(Commit.additions), 0),
                func.coalesce(func.sum(Commit.deletions), 0),
            )
            .where(
                and_(
                    Commit.repo_id.in_(repo_ids),
                    Commit.committed_at >= month_start,
                    Commit.committed_at < month_end,
                )
            )
        )
        lines_result = await self.session.execute(lines_stmt)
        lines_row = lines_result.one()
        total_additions = int(lines_row[0])
        total_deletions = int(lines_row[1])

        # PR数
        pr_count_stmt = (
            select(func.count())
            .select_from(PullRequest)
            .where(
                and_(
                    PullRequest.repo_id.in_(repo_ids),
                    PullRequest.pr_created_at >= month_start,
                    PullRequest.pr_created_at < month_end,
                )
            )
        )
        pr_count_result = await self.session.execute(pr_count_stmt)
        total_prs = pr_count_result.scalar() or 0

        # 分析済みコミット数
        analysis_count_stmt = (
            select(func.count())
            .select_from(GeminiAnalysis)
            .where(
                and_(
                    GeminiAnalysis.source_type == "commit",
                    GeminiAnalysis.repo_id.in_(repo_ids),
                    GeminiAnalysis.analyzed_at >= month_start,
                    GeminiAnalysis.analyzed_at < month_end,
                )
            )
        )
        analysis_count_result = await self.session.execute(analysis_count_stmt)
        total_analyses = analysis_count_result.scalar() or 0

        # work_category別集計
        category_stmt = (
            select(
                GeminiAnalysis.work_category,
                func.count().label("count"),
            )
            .where(
                and_(
                    GeminiAnalysis.source_type == "commit",
                    GeminiAnalysis.repo_id.in_(repo_ids),
                    GeminiAnalysis.analyzed_at >= month_start,
                    GeminiAnalysis.analyzed_at < month_end,
                )
            )
            .group_by(GeminiAnalysis.work_category)
        )
        category_result = await self.session.execute(category_stmt)
        category_breakdown = {
            row.work_category: row.count for row in category_result.all()
        }

        return {
            "total_commits": total_commits,
            "total_prs": total_prs,
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "total_analyses": total_analyses,
            "category_breakdown": category_breakdown,
        }

    # ------------------------------------------------------------------
    # Internal: フォーマット
    # ------------------------------------------------------------------

    @staticmethod
    def _format_generated_summary(analysis: GeminiAnalysis) -> dict[str, Any]:
        """Gemini生成サマリーを辞書形式にフォーマットする。

        Args:
            analysis: GeminiAnalysisオブジェクト。

        Returns:
            フォーマット済み辞書。
        """
        return {
            "analysis_id": analysis.analysis_id,
            "source_type": analysis.source_type,
            "summary": analysis.summary,
            "tech_tags": analysis.tech_tags,
            "work_category": analysis.work_category,
            "complexity_score": float(analysis.complexity_score)
            if analysis.complexity_score is not None
            else None,
            "raw_response": analysis.raw_response,
            "analyzed_at": analysis.analyzed_at.isoformat()
            if analysis.analyzed_at
            else None,
        }
