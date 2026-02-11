"""GitHubバックグラウンド同期タスク。

APSchedulerから呼ばれる定期同期ジョブと、
手動トリガー用のタスク関数を提供する。
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from sqlalchemy import select as sa_select

from app.database import async_session_factory
from app.models import Repository, SyncJob, User
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)


async def github_sync_job() -> None:
    """APSchedulerから呼ばれる定期同期ジョブ。

    全ユーザーの全アクティブリポジトリを同期する。
    GitHubトークンが設定されていないユーザーはスキップする。
    """
    logger.info("Starting scheduled GitHub sync job")

    async with async_session_factory() as session:
        try:
            # GitHubトークンが設定されている全ユーザーを取得
            stmt = select(User).where(User.access_token.isnot(None))
            result = await session.execute(stmt)
            users = list(result.scalars().all())

            if not users:
                logger.info("No users with GitHub tokens configured. Skipping sync.")
                return

            for user in users:
                # そのユーザーにアクティブなリポジトリがあるか確認
                repo_stmt = select(Repository.repo_id).where(
                    Repository.user_id == user.user_id,
                    Repository.is_active.is_(True),
                )
                repo_result = await session.execute(repo_stmt)
                active_repos = list(repo_result.scalars().all())

                if not active_repos:
                    logger.debug(
                        "User %s has no active repositories. Skipping.",
                        user.github_login,
                    )
                    continue

                logger.info(
                    "Syncing %d repositories for user %s",
                    len(active_repos),
                    user.github_login,
                )

                sync_service = SyncService(session=session)
                try:
                    sync_job = await sync_service.sync_all(
                        user=user,
                        full_sync=False,
                    )
                    logger.info(
                        "Sync job %d completed for user %s: status=%s, items=%d",
                        sync_job.job_id,
                        user.github_login,
                        sync_job.status,
                        sync_job.items_fetched,
                    )
                except Exception:
                    logger.exception(
                        "Failed to sync repositories for user %s",
                        user.github_login,
                    )
                    continue

            await session.commit()
            logger.info("Scheduled GitHub sync job completed")

        except Exception:
            await session.rollback()
            logger.exception("Scheduled GitHub sync job failed")
            raise


async def manual_sync_job(
    user_id: int,
    repo_ids: list[int] | None = None,
    full_sync: bool = False,
    sync_job_id: int | None = None,
) -> None:
    """手動同期トリガー用タスク。

    BackgroundTasksから呼ばれ、指定ユーザーの指定リポジトリを同期する。

    Args:
        user_id: 同期対象のユーザーID。
        repo_ids: 同期対象のリポジトリIDリスト。Noneの場合は全アクティブリポジトリ。
        full_sync: Trueの場合、全履歴を再同期する。
        sync_job_id: triggerで作成済みのSyncJob ID。指定時はこのジョブを更新する。
    """
    logger.info(
        "Starting manual sync job for user_id=%d, repo_ids=%s, full_sync=%s, job_id=%s",
        user_id,
        repo_ids,
        full_sync,
        sync_job_id,
    )

    async with async_session_factory() as session:
        try:
            # ユーザーを取得
            stmt = select(User).where(User.user_id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                logger.error("User not found: user_id=%d", user_id)
                return

            # 既存のSyncJobを取得（triggerで作成済みの場合）
            existing_job: SyncJob | None = None
            if sync_job_id is not None:
                job_stmt = sa_select(SyncJob).where(SyncJob.job_id == sync_job_id)
                job_result = await session.execute(job_stmt)
                existing_job = job_result.scalar_one_or_none()

            sync_service = SyncService(session=session)
            sync_job = await sync_service.sync_all(
                user=user,
                repo_ids=repo_ids,
                full_sync=full_sync,
                existing_job=existing_job,
            )

            await session.commit()

            logger.info(
                "Manual sync job %d completed: status=%s, items=%d",
                sync_job.job_id,
                sync_job.status,
                sync_job.items_fetched,
            )

        except Exception:
            await session.rollback()
            logger.exception(
                "Manual sync job failed for user_id=%d",
                user_id,
            )
            raise
