"""同期エンドポイント。

同期トリガー、ステータス確認、同期履歴のAPIを提供する。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user, get_session
from app.core.exceptions import NotFoundError
from app.models import Repository, SyncJob, User
from app.schemas.common import PaginationMeta
from app.schemas.sync import (
    SyncHistoryResponse,
    SyncLogItem,
    SyncStatusResponse,
    SyncTriggerRequest,
    SyncTriggerResponse,
)
from app.tasks.github_sync import manual_sync_job

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/trigger",
    response_model=SyncTriggerResponse,
    status_code=202,
    summary="同期トリガー",
)
async def trigger_sync(
    request: SyncTriggerRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SyncTriggerResponse:
    """同期ジョブをバックグラウンドで開始する。

    Args:
        request: 同期トリガーリクエスト。
        background_tasks: FastAPIバックグラウンドタスク。
        session: データベースセッション。
        current_user: 認証済みユーザー。

    Returns:
        同期ジョブの情報を含む202レスポンス。
    """
    # 対象リポジトリIDの確定
    if request.repo_ids:
        # 指定されたrepo_idsがユーザーのものか確認
        stmt = select(Repository.repo_id).where(
            Repository.user_id == current_user.user_id,
            Repository.repo_id.in_(request.repo_ids),
        )
        result = await session.execute(stmt)
        target_repo_ids = list(result.scalars().all())

        if not target_repo_ids:
            raise NotFoundError(detail="No matching repositories found")
    else:
        # 全アクティブリポジトリ
        stmt = select(Repository.repo_id).where(
            Repository.user_id == current_user.user_id,
            Repository.is_active.is_(True),
        )
        result = await session.execute(stmt)
        target_repo_ids = list(result.scalars().all())

    # SyncJobレコードを先行作成（job_idを返すため）
    sync_job = SyncJob(
        user_id=current_user.user_id,
        job_type="manual_sync",
        status="pending",
        items_fetched=0,
    )
    session.add(sync_job)
    await session.flush()

    # バックグラウンドタスクから参照できるよう明示的にcommit
    await session.commit()

    logger.info(
        "Sync trigger: job_id=%d, user=%s, repos=%s, full_sync=%s",
        sync_job.job_id,
        current_user.github_login,
        target_repo_ids,
        request.full_sync,
    )

    # バックグラウンドタスクとして同期を開始（既存job_idを渡す）
    background_tasks.add_task(
        manual_sync_job,
        user_id=current_user.user_id,
        repo_ids=request.repo_ids,
        full_sync=request.full_sync,
        sync_job_id=sync_job.job_id,
    )

    return SyncTriggerResponse(
        job_id=sync_job.job_id,
        status="pending",
        target_repos=target_repo_ids,
        message=f"Sync job started for {len(target_repo_ids)} repositories",
    )


@router.get(
    "/status/{job_id}",
    response_model=SyncStatusResponse,
    summary="同期ステータス確認",
)
async def get_sync_status(
    job_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SyncStatusResponse:
    """指定した同期ジョブのステータスを取得する。

    Args:
        job_id: 同期ジョブID。
        session: データベースセッション。
        current_user: 認証済みユーザー。

    Returns:
        同期ジョブのステータス情報。

    Raises:
        NotFoundError: ジョブが見つからない場合。
    """
    stmt = select(SyncJob).where(
        SyncJob.job_id == job_id,
        SyncJob.user_id == current_user.user_id,
    )
    result = await session.execute(stmt)
    sync_job = result.scalar_one_or_none()

    if sync_job is None:
        raise NotFoundError(detail=f"Sync job {job_id} not found")

    return SyncStatusResponse.model_validate(sync_job)


@router.get(
    "/history",
    response_model=SyncHistoryResponse,
    summary="同期履歴",
)
async def get_sync_history(
    page: int = Query(default=1, ge=1, description="ページ番号"),
    per_page: int = Query(default=20, ge=1, le=100, description="1ページあたりの件数"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SyncHistoryResponse:
    """同期ジョブの履歴を取得する。

    Args:
        page: ページ番号。
        per_page: 1ページあたりの件数。
        session: データベースセッション。
        current_user: 認証済みユーザー。

    Returns:
        同期履歴とページネーション情報。
    """
    # 総件数
    count_stmt = (
        select(func.count())
        .select_from(SyncJob)
        .where(SyncJob.user_id == current_user.user_id)
    )
    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one()

    # ジョブ一覧（リポジトリ情報付き）
    stmt = (
        select(SyncJob)
        .options(joinedload(SyncJob.repository))
        .where(SyncJob.user_id == current_user.user_id)
        .order_by(SyncJob.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(stmt)
    jobs = list(result.scalars().unique().all())

    logs = [
        SyncLogItem(
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            repo_id=job.repo_id,
            repo_full_name=job.repository.full_name if job.repository else None,
            started_at=job.started_at,
            completed_at=job.completed_at,
            items_fetched=job.items_fetched,
            error_detail=job.error_detail,
            created_at=job.created_at,
        )
        for job in jobs
    ]

    return SyncHistoryResponse(
        logs=logs,
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
        ),
    )
