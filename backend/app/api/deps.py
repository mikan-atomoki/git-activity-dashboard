"""FastAPI依存性注入モジュール。

OAuth2スキーム、現在のユーザー取得を提供する。
データベースセッションは ``app.database.get_session`` を再利用する。
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.security import verify_token
from app.database import get_session  # noqa: F401 – re-export for convenience
from app.models import User

# ---------------------------------------------------------------------------
# OAuth2 スキーム
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ---------------------------------------------------------------------------
# 現在のユーザー取得
# ---------------------------------------------------------------------------

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """アクセストークンから現在のユーザーを取得する。

    Args:
        token: OAuth2アクセストークン。
        session: データベースセッション。

    Returns:
        認証済みUserオブジェクト。

    Raises:
        AuthenticationError: トークンが無効、またはユーザーが存在しない場合。
    """
    try:
        payload = verify_token(token, token_type="access")
    except JWTError:
        raise AuthenticationError("Invalid or expired access token")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Invalid token payload")

    stmt = select(User).where(User.user_id == int(user_id))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("User not found")

    return user
