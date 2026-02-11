"""APSchedulerの設定と管理。

定期実行タスクのスケジュール登録を行う。
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def setup_jobs() -> None:
    """スケジューラにジョブを登録する。

    - github_sync_job: SYNC_INTERVAL_HOURS ごとに実行（デフォルト6時間）
    - gemini_analysis_job: 毎日AM3:00 JST
    - refresh_materialized_views_job: 毎時0分
    """
    from app.tasks.github_sync import github_sync_job

    # GitHub同期ジョブ: 設定された間隔で定期実行
    scheduler.add_job(
        github_sync_job,
        trigger=IntervalTrigger(hours=settings.SYNC_INTERVAL_HOURS),
        id="github_sync_job",
        name="GitHub Repository Sync",
        replace_existing=True,
        max_instances=1,
    )
    logger.info(
        "Registered github_sync_job: every %d hours",
        settings.SYNC_INTERVAL_HOURS,
    )

    # Gemini diff分析ジョブ: 毎日AM3:00 JST
    from app.tasks.gemini_analysis import gemini_analysis_job

    scheduler.add_job(
        gemini_analysis_job,
        trigger=CronTrigger(hour=3, minute=0, timezone=settings.DEFAULT_TIMEZONE),
        id="gemini_analysis_job",
        name="Gemini Commit Analysis",
        replace_existing=True,
        max_instances=1,
    )
    logger.info("Registered gemini_analysis_job: daily at 03:00 JST")

    # マテリアライズドビューリフレッシュ: 毎時0分
    from app.tasks.materialized_views import refresh_materialized_views_job

    scheduler.add_job(
        refresh_materialized_views_job,
        trigger=CronTrigger(minute=0, timezone=settings.DEFAULT_TIMEZONE),
        id="refresh_materialized_views_job",
        name="Refresh Materialized Views",
        replace_existing=True,
        max_instances=1,
    )
    logger.info("Registered refresh_materialized_views_job: hourly at :00")

    logger.info("All scheduled jobs registered")
