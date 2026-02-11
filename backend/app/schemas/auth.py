"""認証関連のPydanticスキーマ。

ユーザー登録、ログイン、トークンレスポンスに使用するスキーマを定義する。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRegisterRequest(BaseModel):
    """ユーザー登録リクエスト。"""

    username: str = Field(
        ...,
        min_length=1,
        max_length=39,
        description="GitHubログイン名",
    )
    email: str | None = Field(
        default=None,
        description="メールアドレス（任意）",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="パスワード（8文字以上）",
    )


class UserResponse(BaseModel):
    """ユーザー情報レスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    github_login: str
    display_name: str | None = None
    avatar_url: str | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    """トークンレスポンス。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        description="アクセストークンの有効期間（秒）",
    )


class AuthResponse(BaseModel):
    """認証レスポンス（登録時に使用）。"""

    user: UserResponse
    access_token: str
    refresh_token: str


class RefreshTokenRequest(BaseModel):
    """リフレッシュトークンリクエスト。"""

    refresh_token: str = Field(
        ...,
        description="リフレッシュトークン",
    )
