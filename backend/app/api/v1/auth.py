"""認証エンドポイント。

ユーザー登録、ログイン、トークンリフレッシュのAPIを提供する。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.auth import (
    AuthResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserRegisterRequest,
)
from app.services.auth_service import (
    authenticate_user,
    create_tokens,
    register_user,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=201,
    summary="ユーザー登録",
)
async def register(
    request: UserRegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    """新規ユーザーを登録し、アクセストークンとリフレッシュトークンを発行する。

    Args:
        request: ユーザー登録リクエスト。
        session: データベースセッション。

    Returns:
        ユーザー情報とトークンを含むレスポンス。
    """
    user = await register_user(session=session, request=request)
    tokens = create_tokens(user_id=user.user_id)

    return AuthResponse(
        user=user,  # type: ignore[arg-type]
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="ログイン",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """OAuth2パスワードフローでログインし、トークンを発行する。

    Args:
        form_data: OAuth2パスワードフォームデータ。
        session: データベースセッション。

    Returns:
        アクセストークンとリフレッシュトークンを含むレスポンス。
    """
    user = await authenticate_user(
        session=session,
        username=form_data.username,
        password=form_data.password,
    )
    return create_tokens(user_id=user.user_id)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="トークンリフレッシュ",
)
async def refresh(
    request: RefreshTokenRequest,
) -> TokenResponse:
    """リフレッシュトークンを検証し、新しいトークンペアを発行する。

    Args:
        request: リフレッシュトークンリクエスト。

    Returns:
        新しいアクセストークンとリフレッシュトークンを含むレスポンス。
    """
    from jose import JWTError

    from app.core.exceptions import AuthenticationError
    from app.core.security import verify_token

    try:
        payload = verify_token(request.refresh_token, token_type="refresh")
    except JWTError:
        raise AuthenticationError("Invalid or expired refresh token")

    user_id = int(payload["sub"])
    return create_tokens(user_id=user_id)
