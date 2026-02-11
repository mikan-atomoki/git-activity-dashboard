"""リポジトリ管理エンドポイント。

リポジトリ一覧取得、GitHub検出、同期対象の切り替えのAPIを提供する。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.core.exceptions import NotFoundError
from app.models import Commit, PullRequest, Repository, User
from app.schemas.common import PaginationMeta
from app.schemas.repository import (
    DiscoverRequest,
    DiscoverResponse,
    DiscoveredRepository,
    RepositoryListResponse,
    RepositoryResponse,
    RepositoryUpdateRequest,
    RepositoryWithStatsResponse,
)
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=RepositoryListResponse,
    summary="リポジトリ一覧",
)
async def list_repositories(
    page: int = Query(default=1, ge=1, description="ページ番号"),
    per_page: int = Query(default=20, ge=1, le=100, description="1ページあたりの件数"),
    active_only: bool = Query(default=True, description="アクティブリポジトリのみ"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> RepositoryListResponse:
    """ユーザーのリポジトリ一覧をコミット数・PR数付きで取得する。

    Args:
        page: ページ番号。
        per_page: 1ページあたりの件数。
        active_only: Trueの場合、アクティブなリポジトリのみ返す。
        session: データベースセッション。
        current_user: 認証済みユーザー。

    Returns:
        リポジトリ一覧とページネーション情報。
    """
    # 基本フィルタ
    base_filter = [Repository.user_id == current_user.user_id]
    if active_only:
        base_filter.append(Repository.is_active.is_(True))

    # 総件数
    count_stmt = (
        select(func.count())
        .select_from(Repository)
        .where(*base_filter)
    )
    count_result = await session.execute(count_stmt)
    total = count_result.scalar_one()

    # コミット数サブクエリ
    commit_count_subq = (
        select(
            Commit.repo_id,
            func.count().label("commit_count"),
        )
        .group_by(Commit.repo_id)
        .subquery()
    )

    # PR数サブクエリ
    pr_count_subq = (
        select(
            PullRequest.repo_id,
            func.count().label("pr_count"),
        )
        .group_by(PullRequest.repo_id)
        .subquery()
    )

    # メインクエリ
    stmt = (
        select(
            Repository,
            func.coalesce(commit_count_subq.c.commit_count, 0).label("commit_count"),
            func.coalesce(pr_count_subq.c.pr_count, 0).label("pr_count"),
        )
        .outerjoin(
            commit_count_subq,
            Repository.repo_id == commit_count_subq.c.repo_id,
        )
        .outerjoin(
            pr_count_subq,
            Repository.repo_id == pr_count_subq.c.repo_id,
        )
        .where(*base_filter)
        .order_by(Repository.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(stmt)
    rows = result.all()

    repositories = [
        RepositoryWithStatsResponse(
            repo_id=repo.repo_id,
            github_repo_id=repo.github_repo_id,
            full_name=repo.full_name,
            description=repo.description,
            primary_language=repo.primary_language,
            is_private=repo.is_private,
            is_active=repo.is_active,
            last_synced_at=repo.last_synced_at,
            repo_metadata=repo.repo_metadata,
            created_at=repo.created_at,
            updated_at=repo.updated_at,
            commit_count=commit_count,
            pr_count=pr_count,
        )
        for repo, commit_count, pr_count in rows
    ]

    return RepositoryListResponse(
        repositories=repositories,
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
        ),
    )


@router.post(
    "/discover",
    response_model=DiscoverResponse,
    summary="リポジトリ検出",
)
async def discover_repositories(
    request: DiscoverRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DiscoverResponse:
    """GitHubからリポジトリを検索し、追跡情報を付与して返す。

    Args:
        request: 検出リクエスト。
        session: データベースセッション。
        current_user: 認証済みユーザー。

    Returns:
        検出されたリポジトリの一覧。
    """
    sync_service = SyncService(session=session)
    discovered = await sync_service.discover_repositories(
        user=current_user,
        include_private=request.include_private,
        include_forks=request.include_forks,
    )

    repos = [
        DiscoveredRepository(**repo_data) for repo_data in discovered
    ]

    return DiscoverResponse(
        repositories=repos,
        total=len(repos),
    )


@router.patch(
    "/{repo_id}",
    response_model=RepositoryResponse,
    summary="リポジトリ更新",
)
async def update_repository(
    repo_id: int,
    request: RepositoryUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> RepositoryResponse:
    """リポジトリの同期対象フラグを更新する。

    Args:
        repo_id: リポジトリID。
        request: 更新リクエスト。
        session: データベースセッション。
        current_user: 認証済みユーザー。

    Returns:
        更新されたリポジトリ情報。

    Raises:
        NotFoundError: リポジトリが見つからない場合。
    """
    stmt = select(Repository).where(
        Repository.repo_id == repo_id,
        Repository.user_id == current_user.user_id,
    )
    result = await session.execute(stmt)
    repo = result.scalar_one_or_none()

    if repo is None:
        raise NotFoundError(detail=f"Repository {repo_id} not found")

    repo.is_active = request.is_active
    session.add(repo)
    await session.flush()

    logger.info(
        "Repository %s (repo_id=%d) is_active set to %s by user %s",
        repo.full_name,
        repo.repo_id,
        request.is_active,
        current_user.github_login,
    )

    return RepositoryResponse.model_validate(repo)
