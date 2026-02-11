"""ダッシュボードデータ取得サービス。

各種ダッシュボードウィジェット向けの集計クエリを提供する。
SQLAlchemy 2.0 の select / func を使用した非同期クエリ。
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import BigInteger, Date, Integer, String, column, func, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HourlyActivity, Repository

# ---------------------------------------------------------------------------
# マテリアライズドビュー参照
# ---------------------------------------------------------------------------

mv_daily_commit_stats = table(
    "mv_daily_commit_stats",
    column("commit_date", Date),
    column("repo_id", BigInteger),
    column("user_id", BigInteger),
    column("full_name", String),
    column("primary_language", String),
    column("commit_count", Integer),
    column("total_additions", Integer),
    column("total_deletions", Integer),
    column("total_changed_files", Integer),
)

mv_weekly_tech_trends = table(
    "mv_weekly_tech_trends",
    column("week_start", Date),
    column("repo_id", BigInteger),
    column("user_id", BigInteger),
    column("tech_tag", String),
    column("tag_count", Integer),
)

mv_work_category_stats = table(
    "mv_work_category_stats",
    column("analysis_date", Date),
    column("repo_id", BigInteger),
    column("user_id", BigInteger),
    column("work_category", String),
    column("category_count", Integer),
)
from app.schemas.dashboard import (
    CategoryBreakdownResponse,
    CategoryItem,
    CommitActivityPoint,
    CommitActivityQuery,
    CommitActivityResponse,
    DashboardStatsResponse,
    HeatmapCell,
    HourlyHeatmapResponse,
    LanguageBreakdownResponse,
    LanguageRatio,
    RepoBreakdownResponse,
    RepoRatio,
    RepoTechAnalysis,
    RepoTechStackItem,
    RepoTechStacksResponse,
    TechTrendItem,
    TechTrendsResponse,
)

# ---------------------------------------------------------------------------
# GitHub言語カラーマッピング（主要言語）
# ---------------------------------------------------------------------------
LANGUAGE_COLORS: dict[str, str] = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Java": "#b07219",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#178600",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Scala": "#c22d40",
    "Dart": "#00B4AB",
    "Shell": "#89e051",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Vue": "#41b883",
    "Svelte": "#ff3e00",
    "Lua": "#000080",
    "R": "#198CE7",
    "Elixir": "#6e4a7e",
    "Haskell": "#5e5086",
    "Clojure": "#db5855",
    "Zig": "#ec915c",
    "Nim": "#ffc200",
    "OCaml": "#3be133",
    "Jupyter Notebook": "#DA5B0B",
}

DEFAULT_COLOR = "#8b8b8b"


class DashboardService:
    """ダッシュボード集計クエリを実行するサービスクラス。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # コミット推移
    # ------------------------------------------------------------------

    async def get_commit_activity(
        self,
        user_id: int,
        query: CommitActivityQuery,
    ) -> CommitActivityResponse:
        """コミット推移データを取得する。

        ``period`` に応じて ``date_trunc`` で丸めたうえで集計する。
        ``start_date`` 未指定時は90日前から。

        Args:
            user_id: 対象ユーザーID。
            query: クエリパラメータ。

        Returns:
            集計済みコミット推移レスポンス。
        """
        today = date.today()
        start = query.start_date or (today - timedelta(days=90))
        end = query.end_date or today

        # period ごとの date_trunc 引数
        trunc_map = {"daily": "day", "weekly": "week", "monthly": "month"}
        trunc_unit = trunc_map[query.period]

        mv = mv_daily_commit_stats
        period_col = func.date_trunc(trunc_unit, mv.c.commit_date).label(
            "period_date",
        )

        stmt = (
            select(
                period_col,
                func.sum(mv.c.commit_count).label("cnt"),
                func.coalesce(func.sum(mv.c.total_additions), 0).label("adds"),
                func.coalesce(func.sum(mv.c.total_deletions), 0).label("dels"),
            )
            .where(
                mv.c.user_id == user_id,
                mv.c.commit_date >= start,
                mv.c.commit_date <= end,
            )
        )

        if query.repo_ids:
            stmt = stmt.where(mv.c.repo_id.in_(query.repo_ids))

        stmt = stmt.group_by(period_col).order_by(period_col)

        result = await self.session.execute(stmt)
        rows = result.all()

        data: list[CommitActivityPoint] = []
        total = 0
        for row in rows:
            period_date = row.period_date
            if period_date is not None:
                d = period_date.date() if hasattr(period_date, "date") else period_date
            else:
                continue
            count = int(row.cnt)
            total += count
            data.append(
                CommitActivityPoint(
                    date=d,
                    count=count,
                    additions=int(row.adds),
                    deletions=int(row.dels),
                ),
            )

        return CommitActivityResponse(
            period=query.period,
            data=data,
            total_commits=total,
        )

    # ------------------------------------------------------------------
    # 言語比率
    # ------------------------------------------------------------------

    async def get_language_breakdown(
        self,
        user_id: int,
    ) -> LanguageBreakdownResponse:
        """アクティブリポジトリの言語比率を取得する。

        ``repositories.primary_language`` を GROUP BY して集計する。

        Args:
            user_id: 対象ユーザーID。

        Returns:
            言語比率レスポンス。
        """
        stmt = (
            select(
                Repository.primary_language,
                func.count().label("cnt"),
            )
            .where(
                Repository.user_id == user_id,
                Repository.is_active.is_(True),
                Repository.primary_language.isnot(None),
            )
            .group_by(Repository.primary_language)
            .order_by(func.count().desc())
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        total = sum(row.cnt for row in rows)
        data: list[LanguageRatio] = []
        for row in rows:
            lang = row.primary_language or "Unknown"
            pct = round((row.cnt / total) * 100, 1) if total > 0 else 0.0
            data.append(
                LanguageRatio(
                    language=lang,
                    percentage=pct,
                    color=LANGUAGE_COLORS.get(lang, DEFAULT_COLOR),
                ),
            )

        return LanguageBreakdownResponse(data=data)

    # ------------------------------------------------------------------
    # リポジトリ別コミット比率
    # ------------------------------------------------------------------

    async def get_repo_breakdown(
        self,
        user_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 10,
    ) -> RepoBreakdownResponse:
        """リポジトリ別コミット比率を取得する。

        ``commits`` JOIN ``repositories`` で GROUP BY ``repo_id``。

        Args:
            user_id: 対象ユーザーID。
            start_date: 開始日。
            end_date: 終了日。
            limit: 返却件数上限。

        Returns:
            リポジトリ別コミット比率レスポンス。
        """
        today = date.today()
        start = start_date or (today - timedelta(days=90))
        end = end_date or today

        mv = mv_daily_commit_stats
        stmt = (
            select(
                mv.c.repo_id,
                mv.c.full_name,
                mv.c.primary_language,
                func.sum(mv.c.commit_count).label("commit_count"),
            )
            .where(
                mv.c.user_id == user_id,
                mv.c.commit_date >= start,
                mv.c.commit_date <= end,
            )
            .group_by(mv.c.repo_id, mv.c.full_name, mv.c.primary_language)
            .order_by(func.sum(mv.c.commit_count).desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        total = sum(row.commit_count for row in rows)
        data: list[RepoRatio] = []
        for row in rows:
            pct = round((row.commit_count / total) * 100, 1) if total > 0 else 0.0
            data.append(
                RepoRatio(
                    repo_id=row.repo_id,
                    repo_name=row.full_name,
                    commit_count=row.commit_count,
                    percentage=pct,
                    primary_language=row.primary_language,
                ),
            )

        return RepoBreakdownResponse(data=data, total_commits=total)

    # ------------------------------------------------------------------
    # 時間帯ヒートマップ
    # ------------------------------------------------------------------

    async def get_hourly_heatmap(
        self,
        user_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> HourlyHeatmapResponse:
        """時間帯ヒートマップ用データを取得する。

        ``hourly_activity`` テーブルから ``day_of_week``, ``hour_of_day`` で
        GROUP BY し、0埋めで 7x24 の完全グリッドを返す。

        Args:
            user_id: 対象ユーザーID。
            start_date: 開始日。
            end_date: 終了日。

        Returns:
            7x24 セルのヒートマップレスポンス。
        """
        today = date.today()
        start = start_date or (today - timedelta(days=90))
        end = end_date or today

        stmt = (
            select(
                HourlyActivity.day_of_week,
                HourlyActivity.hour_of_day,
                func.coalesce(
                    func.sum(HourlyActivity.commit_count + HourlyActivity.pr_count),
                    0,
                ).label("total_count"),
            )
            .where(
                HourlyActivity.user_id == user_id,
                HourlyActivity.activity_date >= start,
                HourlyActivity.activity_date <= end,
            )
            .group_by(
                HourlyActivity.day_of_week,
                HourlyActivity.hour_of_day,
            )
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        # 結果をマップに格納
        count_map: dict[tuple[int, int], int] = {}
        for row in rows:
            count_map[(row.day_of_week, row.hour_of_day)] = int(row.total_count)

        # 7x24 の完全グリッドを生成（0埋め）
        data: list[HeatmapCell] = []
        max_count = 0
        for dow in range(7):
            for hour in range(24):
                count = count_map.get((dow, hour), 0)
                if count > max_count:
                    max_count = count
                data.append(
                    HeatmapCell(day_of_week=dow, hour=hour, count=count),
                )

        return HourlyHeatmapResponse(data=data, max_count=max_count)

    # ------------------------------------------------------------------
    # 技術トレンド
    # ------------------------------------------------------------------

    async def get_tech_trends(
        self,
        user_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TechTrendsResponse:
        """技術トレンドデータを取得する。

        ``gemini_analyses.tech_tags`` (JSONB配列) を
        ``jsonb_array_elements_text`` で展開し、週単位で GROUP BY する。

        Args:
            user_id: 対象ユーザーID。
            start_date: 開始日。
            end_date: 終了日。

        Returns:
            技術トレンドレスポンス。
        """
        today = date.today()
        start = start_date or (today - timedelta(days=90))
        end = end_date or today

        mv = mv_weekly_tech_trends
        stmt = (
            select(
                mv.c.week_start.label("period_start"),
                mv.c.tech_tag.label("tag"),
                func.sum(mv.c.tag_count).label("cnt"),
            )
            .where(
                mv.c.user_id == user_id,
                mv.c.week_start >= start,
                mv.c.week_start <= end,
            )
            .group_by(mv.c.week_start, mv.c.tech_tag)
            .order_by(mv.c.week_start, func.sum(mv.c.tag_count).desc())
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        data: list[TechTrendItem] = []
        for row in rows:
            period_start = row.period_start
            if period_start is not None:
                d = (
                    period_start.date()
                    if hasattr(period_start, "date")
                    else period_start
                )
            else:
                continue
            data.append(
                TechTrendItem(
                    period_start=d,
                    tag=row.tag,
                    count=int(row.cnt),
                ),
            )

        return TechTrendsResponse(data=data)

    # ------------------------------------------------------------------
    # 作業カテゴリ比率
    # ------------------------------------------------------------------

    async def get_category_breakdown(
        self,
        user_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> CategoryBreakdownResponse:
        """作業カテゴリ比率を取得する。

        ``gemini_analyses.work_category`` で GROUP BY する。

        Args:
            user_id: 対象ユーザーID。
            start_date: 開始日。
            end_date: 終了日。

        Returns:
            カテゴリ比率レスポンス。
        """
        today = date.today()
        start = start_date or (today - timedelta(days=90))
        end = end_date or today

        mv = mv_work_category_stats
        stmt = (
            select(
                mv.c.work_category,
                func.sum(mv.c.category_count).label("cnt"),
            )
            .where(
                mv.c.user_id == user_id,
                mv.c.analysis_date >= start,
                mv.c.analysis_date <= end,
            )
            .group_by(mv.c.work_category)
            .order_by(func.sum(mv.c.category_count).desc())
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        total = sum(row.cnt for row in rows)
        data: list[CategoryItem] = []
        for row in rows:
            pct = round((row.cnt / total) * 100, 1) if total > 0 else 0.0
            data.append(
                CategoryItem(
                    category=row.work_category,
                    count=int(row.cnt),
                    percentage=pct,
                ),
            )

        return CategoryBreakdownResponse(data=data)

    # ------------------------------------------------------------------
    # ダッシュボード統計カード
    # ------------------------------------------------------------------

    async def get_dashboard_stats(
        self,
        user_id: int,
    ) -> DashboardStatsResponse:
        """ダッシュボード統計カード用データを取得する。

        - total_commits: 全コミット数
        - active_repos: アクティブリポジトリ数
        - current_streak: 連続コミット日数（今日から逆算）
        - top_language: 最も使用している言語
        - commit_change_pct: 前月比

        Args:
            user_id: 対象ユーザーID。

        Returns:
            統計カードレスポンス。
        """
        mv = mv_daily_commit_stats

        # --- total_commits ---
        total_stmt = select(
            func.coalesce(func.sum(mv.c.commit_count), 0),
        ).where(mv.c.user_id == user_id)
        total_result = await self.session.execute(total_stmt)
        total_commits = total_result.scalar_one() or 0

        # --- active_repos ---
        active_stmt = (
            select(func.count())
            .where(
                Repository.user_id == user_id,
                Repository.is_active.is_(True),
            )
        )
        active_result = await self.session.execute(active_stmt)
        active_repos = active_result.scalar_one() or 0

        # --- top_language ---
        lang_stmt = (
            select(Repository.primary_language)
            .where(
                Repository.user_id == user_id,
                Repository.is_active.is_(True),
                Repository.primary_language.isnot(None),
            )
            .group_by(Repository.primary_language)
            .order_by(func.count().desc())
            .limit(1)
        )
        lang_result = await self.session.execute(lang_stmt)
        top_language = lang_result.scalar_one_or_none()

        # --- commit_change_pct (前月比) ---
        today = date.today()
        current_month_start = today.replace(day=1)
        prev_month_end = current_month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)

        current_month_stmt = select(
            func.coalesce(func.sum(mv.c.commit_count), 0),
        ).where(
            mv.c.user_id == user_id,
            mv.c.commit_date >= current_month_start,
            mv.c.commit_date <= today,
        )
        current_result = await self.session.execute(current_month_stmt)
        current_month_commits = current_result.scalar_one() or 0

        prev_month_stmt = select(
            func.coalesce(func.sum(mv.c.commit_count), 0),
        ).where(
            mv.c.user_id == user_id,
            mv.c.commit_date >= prev_month_start,
            mv.c.commit_date < current_month_start,
        )
        prev_result = await self.session.execute(prev_month_stmt)
        prev_month_commits = prev_result.scalar_one() or 0

        commit_change_pct: float | None = None
        if prev_month_commits > 0:
            commit_change_pct = round(
                ((current_month_commits - prev_month_commits) / prev_month_commits)
                * 100,
                1,
            )

        # --- current_streak ---
        streak = await self._calculate_streak(user_id)

        return DashboardStatsResponse(
            total_commits=total_commits,
            active_repos=active_repos,
            current_streak=streak,
            top_language=top_language,
            commit_change_pct=commit_change_pct,
        )

    # ------------------------------------------------------------------
    # 連続コミット日数
    # ------------------------------------------------------------------

    async def _calculate_streak(self, user_id: int) -> int:
        """連続コミット日数を計算する。

        今日から過去に遡り、コミットが存在する日付の連続性をチェックする。
        今日にコミットがなければ昨日を起点とする。

        Args:
            user_id: 対象ユーザーID。

        Returns:
            連続コミット日数。
        """
        # コミットが存在するユニークな日付を降順で取得（直近120日分）
        today = date.today()
        cutoff = today - timedelta(days=120)

        mv = mv_daily_commit_stats
        stmt = (
            select(mv.c.commit_date)
            .where(
                mv.c.user_id == user_id,
                mv.c.commit_date >= cutoff,
            )
            .group_by(mv.c.commit_date)
            .order_by(mv.c.commit_date.desc())
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        if not rows:
            return 0

        commit_dates: set[date] = set()
        for row in rows:
            d = row.commit_date
            if d is not None:
                if hasattr(d, "date"):
                    d = d.date()
                commit_dates.add(d)

        if not commit_dates:
            return 0

        # 今日にコミットがあればtoday起点、なければ昨日起点
        check_date = today
        if check_date not in commit_dates:
            check_date = today - timedelta(days=1)
            if check_date not in commit_dates:
                return 0

        streak = 0
        while check_date in commit_dates:
            streak += 1
            check_date -= timedelta(days=1)

        return streak

    # ------------------------------------------------------------------
    # リポジトリ技術スタック
    # ------------------------------------------------------------------

    async def get_repo_tech_stacks(
        self,
        user_id: int,
    ) -> RepoTechStacksResponse:
        """アクティブリポジトリの技術スタック分析結果を取得する。

        repo_metadata JSONB カラムから tech_analysis を読み取る。

        Args:
            user_id: 対象ユーザーID。

        Returns:
            リポジトリ技術スタック一覧レスポンス。
        """
        stmt = (
            select(Repository)
            .where(
                Repository.user_id == user_id,
                Repository.is_active.is_(True),
            )
            .order_by(Repository.full_name)
        )

        result = await self.session.execute(stmt)
        repos = result.scalars().all()

        data: list[RepoTechStackItem] = []
        for repo in repos:
            tech_raw = (repo.repo_metadata or {}).get("tech_analysis")
            tech_analysis: RepoTechAnalysis | None = None
            if tech_raw and isinstance(tech_raw, dict):
                tech_analysis = RepoTechAnalysis(
                    domain=tech_raw.get("domain", "general"),
                    domain_detail=tech_raw.get("domain_detail", ""),
                    frameworks=tech_raw.get("frameworks", []),
                    tools=tech_raw.get("tools", []),
                    infrastructure=tech_raw.get("infrastructure", []),
                    project_type=tech_raw.get("project_type", ""),
                    analyzed_at=tech_raw.get("analyzed_at"),
                )

            data.append(
                RepoTechStackItem(
                    repo_id=repo.repo_id,
                    full_name=repo.full_name,
                    description=repo.description,
                    primary_language=repo.primary_language,
                    tech_analysis=tech_analysis,
                ),
            )

        return RepoTechStacksResponse(data=data)
