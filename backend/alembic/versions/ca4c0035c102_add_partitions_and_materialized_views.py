"""add partitions and materialized views

Revision ID: ca4c0035c102
Revises: 824e73e089cc
Create Date: 2026-02-11 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ca4c0035c102"
down_revision: Union[str, None] = "824e73e089cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# パーティション作成ヘルパー
# ---------------------------------------------------------------------------

def _create_monthly_partitions(
    parent_table: str,
    partition_column: str,
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
) -> None:
    """月次パーティションを一括作成する。"""
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1

        partition_name = f"{parent_table}_{year}_{month:02d}"
        from_date = f"{year}-{month:02d}-01"
        to_date = f"{next_year}-{next_month:02d}-01"

        op.execute(
            f"CREATE TABLE IF NOT EXISTS {partition_name} "
            f"PARTITION OF {parent_table} "
            f"FOR VALUES FROM ('{from_date}') TO ('{to_date}')"
        )

        month = next_month
        year = next_year


def _drop_monthly_partitions(
    parent_table: str,
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
) -> None:
    """月次パーティションを一括削除する。"""
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1

        partition_name = f"{parent_table}_{year}_{month:02d}"
        op.execute(f"DROP TABLE IF EXISTS {partition_name}")

        month = next_month
        year = next_year


# ---------------------------------------------------------------------------
# パーティション範囲: 2024-01 ~ 2027-12
# ---------------------------------------------------------------------------

PARTITION_START_YEAR = 2024
PARTITION_START_MONTH = 1
PARTITION_END_YEAR = 2027
PARTITION_END_MONTH = 12


def upgrade() -> None:
    # ==================================================================
    # 1. パーティションテーブル作成
    # ==================================================================

    # --- commits ---
    _create_monthly_partitions(
        parent_table="commits",
        partition_column="committed_at",
        start_year=PARTITION_START_YEAR,
        start_month=PARTITION_START_MONTH,
        end_year=PARTITION_END_YEAR,
        end_month=PARTITION_END_MONTH,
    )

    # --- pull_requests ---
    _create_monthly_partitions(
        parent_table="pull_requests",
        partition_column="pr_created_at",
        start_year=PARTITION_START_YEAR,
        start_month=PARTITION_START_MONTH,
        end_year=PARTITION_END_YEAR,
        end_month=PARTITION_END_MONTH,
    )

    # --- gemini_analyses ---
    _create_monthly_partitions(
        parent_table="gemini_analyses",
        partition_column="analyzed_at",
        start_year=PARTITION_START_YEAR,
        start_month=PARTITION_START_MONTH,
        end_year=PARTITION_END_YEAR,
        end_month=PARTITION_END_MONTH,
    )

    # ==================================================================
    # 2. マテリアライズドビュー作成
    # ==================================================================

    # --- mv_daily_commit_stats ---
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_commit_stats AS
        SELECT
            DATE(c.committed_at) AS commit_date,
            c.repo_id,
            r.user_id,
            r.full_name,
            r.primary_language,
            COUNT(c.commit_id) AS commit_count,
            COALESCE(SUM(c.additions), 0) AS total_additions,
            COALESCE(SUM(c.deletions), 0) AS total_deletions,
            COALESCE(SUM(c.changed_files), 0) AS total_changed_files
        FROM commits c
        JOIN repositories r ON c.repo_id = r.repo_id
        GROUP BY
            DATE(c.committed_at),
            c.repo_id,
            r.user_id,
            r.full_name,
            r.primary_language
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_daily_commit_stats_unique "
        "ON mv_daily_commit_stats (commit_date, repo_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mv_daily_commit_stats_user "
        "ON mv_daily_commit_stats (user_id, commit_date DESC)"
    )

    # --- mv_weekly_tech_trends ---
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_weekly_tech_trends AS
        SELECT
            DATE_TRUNC('week', ga.analyzed_at)::DATE AS week_start,
            ga.repo_id,
            r.user_id,
            tag.value AS tech_tag,
            COUNT(ga.analysis_id) AS tag_count
        FROM gemini_analyses ga
        JOIN repositories r ON ga.repo_id = r.repo_id,
        LATERAL JSONB_ARRAY_ELEMENTS_TEXT(ga.tech_tags) AS tag(value)
        WHERE ga.tech_tags IS NOT NULL
          AND JSONB_ARRAY_LENGTH(ga.tech_tags) > 0
        GROUP BY
            DATE_TRUNC('week', ga.analyzed_at)::DATE,
            ga.repo_id,
            r.user_id,
            tag.value
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_weekly_tech_unique "
        "ON mv_weekly_tech_trends (week_start, repo_id, tech_tag)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mv_weekly_tech_user "
        "ON mv_weekly_tech_trends (user_id, week_start DESC)"
    )

    # --- mv_work_category_stats ---
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_work_category_stats AS
        SELECT
            DATE(ga.analyzed_at) AS analysis_date,
            ga.repo_id,
            r.user_id,
            ga.work_category,
            COUNT(ga.analysis_id) AS category_count
        FROM gemini_analyses ga
        JOIN repositories r ON ga.repo_id = r.repo_id
        WHERE ga.work_category IS NOT NULL
        GROUP BY
            DATE(ga.analyzed_at),
            ga.repo_id,
            r.user_id,
            ga.work_category
    """)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_work_category_unique "
        "ON mv_work_category_stats (analysis_date, repo_id, work_category)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_mv_work_category_user "
        "ON mv_work_category_stats (user_id, analysis_date DESC)"
    )


def downgrade() -> None:
    # マテリアライズドビュー削除
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_work_category_stats CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_weekly_tech_trends CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_commit_stats CASCADE")

    # パーティション削除
    _drop_monthly_partitions(
        "gemini_analyses",
        PARTITION_START_YEAR, PARTITION_START_MONTH,
        PARTITION_END_YEAR, PARTITION_END_MONTH,
    )
    _drop_monthly_partitions(
        "pull_requests",
        PARTITION_START_YEAR, PARTITION_START_MONTH,
        PARTITION_END_YEAR, PARTITION_END_MONTH,
    )
    _drop_monthly_partitions(
        "commits",
        PARTITION_START_YEAR, PARTITION_START_MONTH,
        PARTITION_END_YEAR, PARTITION_END_MONTH,
    )
