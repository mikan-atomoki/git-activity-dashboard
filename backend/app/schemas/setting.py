"""設定関連のPydanticスキーマ。

ユーザー設定の取得・更新、GitHubトークン検証のAPI用スキーマを定義する。
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    """設定情報レスポンス。"""

    github_token_configured: bool = Field(
        description="GitHubトークンが設定済みか",
    )
    github_username: Optional[str] = Field(
        default=None,
        description="GitHubユーザー名",
    )
    sync_interval_hours: int = Field(
        description="同期間隔（時間）",
    )
    gemini_analysis_enabled: bool = Field(
        default=False,
        description="Gemini分析が有効か",
    )
    timezone: str = Field(
        description="タイムゾーン設定",
    )
    tracked_repos_count: int = Field(
        default=0,
        description="追跡中のリポジトリ数",
    )


class SettingsUpdateRequest(BaseModel):
    """設定更新リクエスト。"""

    github_token: Optional[str] = Field(
        default=None,
        description="GitHub Personal Access Token（暗号化して保存）",
    )
    sync_interval_hours: Optional[int] = Field(
        default=None,
        ge=1,
        le=168,
        description="同期間隔（時間、1〜168）",
    )
    gemini_analysis_enabled: Optional[bool] = Field(
        default=None,
        description="Gemini分析の有効/無効",
    )
    timezone: Optional[str] = Field(
        default=None,
        description="タイムゾーン設定（例: Asia/Tokyo）",
    )


class ValidateGitHubTokenRequest(BaseModel):
    """GitHubトークン検証リクエスト。"""

    token: str = Field(
        ...,
        min_length=1,
        description="検証するGitHub Personal Access Token",
    )


class ValidateGitHubTokenResponse(BaseModel):
    """GitHubトークン検証レスポンス。"""

    valid: bool
    github_login: Optional[str] = None
    github_user_id: Optional[int] = None
    scopes: Optional[list[str]] = None
    message: str = Field(
        description="検証結果メッセージ",
    )
