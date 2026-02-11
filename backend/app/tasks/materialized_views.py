"""マテリアライズドビューリフレッシュジョブ。

APSchedulerから定期呼び出しされ、データ集計用の
マテリアライズドビューを更新する。
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.database import async_session_factory

logger = logging.getLogger(__name__)

# リフレッシュ対象のマテリアライズドビュー名リスト
MATERIALIZED_VIEWS: list[str] = [
    "mv_daily_summary",
    "mv_weekly_summary",
    "mv_monthly_summary",
    "mv_technology_stats",
]


async def refresh_materialized_views_job() -> None:
    """定期的にマテリアライズドビューをリフレッシュする。

    ビューが存在しない場合はスキップする（初期セットアップ前の安全策）。
    CONCURRENTLY オプションにより、リフレッシュ中もビューの読み取りが可能。
    ただし CONCURRENTLY にはUNIQUE INDEXが必要なため、存在しない場合は
    通常のREFRESHにフォールバックする。
    """
    logger.info("Materialized views refresh job started")
    refreshed_count = 0
    skipped_count = 0

    try:
        async with async_session_factory() as session:
            for view_name in MATERIALIZED_VIEWS:
                try:
                    # ビューの存在確認
                    check_stmt = text(
                        "SELECT EXISTS ("
                        "  SELECT 1 FROM pg_matviews"
                        "  WHERE matviewname = :view_name"
                        ")"
                    )
                    result = await session.execute(
                        check_stmt,
                        {"view_name": view_name},
                    )
                    exists = result.scalar()

                    if not exists:
                        logger.debug(
                            "Materialized view '%s' does not exist, skipping.",
                            view_name,
                        )
                        skipped_count += 1
                        continue

                    # CONCURRENTLY でリフレッシュを試行
                    try:
                        refresh_stmt = text(
                            f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"
                        )
                        await session.execute(refresh_stmt)
                    except Exception:
                        # CONCURRENTLY が失敗する場合（UNIQUE INDEXがない等）は
                        # 通常のREFRESHにフォールバック
                        logger.debug(
                            "CONCURRENTLY refresh failed for '%s', "
                            "falling back to regular refresh.",
                            view_name,
                        )
                        await session.rollback()
                        refresh_stmt = text(
                            f"REFRESH MATERIALIZED VIEW {view_name}"
                        )
                        await session.execute(refresh_stmt)

                    await session.commit()
                    refreshed_count += 1
                    logger.info(
                        "Materialized view '%s' refreshed successfully.",
                        view_name,
                    )

                except Exception:
                    logger.exception(
                        "Failed to refresh materialized view '%s'",
                        view_name,
                    )
                    await session.rollback()
                    continue

    except Exception:
        logger.exception(
            "Materialized views refresh job failed with unexpected error",
        )

    logger.info(
        "Materialized views refresh job finished: refreshed=%d, skipped=%d",
        refreshed_count,
        skipped_count,
    )
