"""設定エンドポイント。

ユーザー設定の取得・更新、GitHubトークン検証のAPIを提供する。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.config import settings as app_settings
from app.core.exceptions import ExternalAPIError
from app.core.security import decrypt_token, encrypt_token
from app.external.github_client import GitHubClient
from app.models import Repository, User
from app.services.sync_service import SyncService
from app.schemas.setting import (
    SettingsResponse,
    SettingsUpdateRequest,
    ValidateGitHubTokenRequest,
    ValidateGitHubTokenResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=SettingsResponse,
    summary="設定取得",
)
async def get_settings(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SettingsResponse:
    """現在のユーザー設定を取得する。

    Args:
        session: データベースセッション。
        current_user: 認証済みユーザー。

    Returns:
        ユーザー設定情報。
    """
    # 追跡中リポジトリ数を取得
    stmt = (
        select(func.count())
        .select_from(Repository)
        .where(
            Repository.user_id == current_user.user_id,
            Repository.is_active.is_(True),
        )
    )
    result = await session.execute(stmt)
    tracked_count = result.scalar_one()

    # profile_dataからユーザー設定を取得
    profile = current_user.profile_data or {}

    return SettingsResponse(
        github_token_configured=current_user.access_token is not None,
        github_username=current_user.github_login,
        sync_interval_hours=profile.get(
            "sync_interval_hours",
            app_settings.SYNC_INTERVAL_HOURS,
        ),
        gemini_analysis_enabled=profile.get("gemini_analysis_enabled", True),
        timezone=profile.get("timezone", app_settings.DEFAULT_TIMEZONE),
        tracked_repos_count=tracked_count,
    )


@router.put(
    "",
    response_model=SettingsResponse,
    summary="設定更新",
)
async def update_settings(
    request: SettingsUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SettingsResponse:
    """ユーザー設定を更新する。

    GitHubトークンは暗号化して保存される。
    その他の設定はprofile_data JSONBフィールドに保存される。

    Args:
        request: 設定更新リクエスト。
        session: データベースセッション。
        current_user: 認証済みユーザー。

    Returns:
        更新後のユーザー設定情報。
    """
    # GitHubトークンの更新
    if request.github_token is not None:
        if request.github_token == "":
            # 空文字列の場合はトークンを削除
            current_user.access_token = None
            logger.info(
                "GitHub token removed for user %s",
                current_user.github_login,
            )
        else:
            # トークンを検証してから保存
            client = GitHubClient(token=request.github_token)
            try:
                github_user = await client.get_authenticated_user()
                current_user.access_token = encrypt_token(request.github_token)
                current_user.github_user_id = github_user.get("id")
                current_user.avatar_url = github_user.get("avatar_url")
                current_user.display_name = github_user.get("name") or github_user.get("login")
                logger.info(
                    "GitHub token updated for user %s (github_login=%s)",
                    current_user.github_login,
                    github_user.get("login"),
                )
            except ExternalAPIError as e:
                logger.warning(
                    "GitHub token validation failed for user %s: %s",
                    current_user.github_login,
                    e.detail,
                )
                raise ExternalAPIError(
                    detail="Invalid GitHub token. Please check your token and try again."
                )
            finally:
                await client.close()

            # トークン保存後、全リポジトリを自動検出・登録
            await _auto_register_repos(session, current_user)

    # profile_dataの更新
    profile = dict(current_user.profile_data or {})

    if request.sync_interval_hours is not None:
        profile["sync_interval_hours"] = request.sync_interval_hours

    if request.gemini_analysis_enabled is not None:
        profile["gemini_analysis_enabled"] = request.gemini_analysis_enabled

    if request.timezone is not None:
        profile["timezone"] = request.timezone

    current_user.profile_data = profile
    session.add(current_user)
    await session.commit()

    # 更新後の設定を返す
    return await get_settings(session=session, current_user=current_user)


@router.post(
    "/validate-github-token",
    response_model=ValidateGitHubTokenResponse,
    summary="GitHubトークン検証",
)
async def validate_github_token(
    request: ValidateGitHubTokenRequest,
) -> ValidateGitHubTokenResponse:
    """GitHubトークンを検証する。

    GitHub API の /user エンドポイントを叩いてトークンの有効性を確認する。

    Args:
        request: トークン検証リクエスト。

    Returns:
        検証結果。
    """
    client = GitHubClient(token=request.token)
    try:
        github_user = await client.get_authenticated_user()
        scopes = await client.get_token_scopes()

        return ValidateGitHubTokenResponse(
            valid=True,
            github_login=github_user.get("login"),
            github_user_id=github_user.get("id"),
            scopes=scopes or None,
            message=f"Token is valid. Authenticated as {github_user.get('login')}",
        )
    except ExternalAPIError as e:
        logger.info("GitHub token validation failed: %s", e.detail)
        return ValidateGitHubTokenResponse(
            valid=False,
            message=f"Token validation failed: {e.detail}",
        )
    except Exception as e:
        logger.exception("Unexpected error during GitHub token validation")
        return ValidateGitHubTokenResponse(
            valid=False,
            message=f"Unexpected error: {str(e)}",
        )
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# リポジトリ自動登録ヘルパー
# ---------------------------------------------------------------------------

async def _auto_register_repos(
    session: AsyncSession,
    user: User,
) -> None:
    """GitHubの全リポジトリを自動検出してDBに登録（is_active=True）する。"""
    sync_svc = SyncService(session)
    try:
        discovered = await sync_svc.discover_repositories(
            user, include_private=True, include_forks=False,
        )
    except Exception:
        logger.exception("Auto-discover failed for user %s", user.github_login)
        return

    registered = 0
    for repo_info in discovered:
        if repo_info["already_tracked"]:
            continue

        new_repo = Repository(
            user_id=user.user_id,
            github_repo_id=repo_info["github_repo_id"],
            full_name=repo_info["full_name"],
            description=repo_info.get("description"),
            primary_language=repo_info.get("primary_language"),
            is_private=repo_info.get("is_private", False),
            is_active=True,
        )
        session.add(new_repo)
        registered += 1

    if registered:
        await session.flush()
        logger.info(
            "Auto-registered %d repositories for user %s",
            registered,
            user.github_login,
        )
