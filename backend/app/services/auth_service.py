"""認証サービスモジュール。

ユーザー登録、認証、トークン生成のビジネスロジックを提供する。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AuthenticationError, AppException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas.auth import TokenResponse, UserRegisterRequest


async def register_user(
    session: AsyncSession,
    request: UserRegisterRequest,
) -> User:
    """新規ユーザーを登録する。

    Args:
        session: データベースセッション。
        request: ユーザー登録リクエスト。

    Returns:
        作成されたUserオブジェクト。

    Raises:
        AppException: ユーザー名が既に存在する場合 (409 Conflict)。
    """
    # 既存ユーザーチェック
    stmt = select(User).where(User.github_login == request.username)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise AppException(
            status_code=409,
            detail=f"User '{request.username}' already exists",
        )

    # ユーザー作成
    hashed = hash_password(request.password)
    user = User(
        github_login=request.username,
        email=request.email,
        password_hash=hashed,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str,
) -> User:
    """ユーザー名とパスワードで認証する。

    Args:
        session: データベースセッション。
        username: GitHubログイン名。
        password: 平文パスワード。

    Returns:
        認証済みUserオブジェクト。

    Raises:
        AuthenticationError: ユーザーが存在しない、またはパスワードが不正の場合。
    """
    stmt = select(User).where(User.github_login == username)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("Invalid username or password")

    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid username or password")

    return user


def create_tokens(user_id: int) -> TokenResponse:
    """ユーザーIDからアクセストークンとリフレッシュトークンを生成する。

    Args:
        user_id: ユーザーID。

    Returns:
        TokenResponseオブジェクト。
    """
    access_token = create_access_token(user_id=user_id)
    refresh_token = create_refresh_token(user_id=user_id)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
    )
