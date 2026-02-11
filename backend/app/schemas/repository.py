"""リポジトリ関連のPydanticスキーマ。

リポジトリ一覧、検出、更新のAPI用スキーマを定義する。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class RepositoryResponse(BaseModel):
    """リポジトリレスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    repo_id: int
    github_repo_id: int
    full_name: str
    description: Optional[str] = None
    primary_language: Optional[str] = None
    is_private: bool = False
    is_active: bool = True
    last_synced_at: Optional[datetime] = None
    repo_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class RepositoryWithStatsResponse(RepositoryResponse):
    """統計情報付きリポジトリレスポンス。"""

    commit_count: int = 0
    pr_count: int = 0


class RepositoryListResponse(BaseModel):
    """リポジトリ一覧レスポンス。"""

    repositories: list[RepositoryWithStatsResponse]
    pagination: PaginationMeta


class DiscoverRequest(BaseModel):
    """リポジトリ検出リクエスト。"""

    include_private: bool = Field(
        default=True,
        description="プライベートリポジトリを含むか",
    )
    include_forks: bool = Field(
        default=False,
        description="フォークリポジトリを含むか",
    )


class DiscoveredRepository(BaseModel):
    """検出されたリポジトリ情報。"""

    github_repo_id: int
    full_name: str
    description: Optional[str] = None
    primary_language: Optional[str] = None
    is_private: bool = False
    is_fork: bool = False
    already_tracked: bool = False
    repo_id: Optional[int] = Field(
        default=None,
        description="既に追跡中の場合のリポジトリID",
    )
    pushed_at: Optional[str] = None
    stargazers_count: int = 0


class DiscoverResponse(BaseModel):
    """リポジトリ検出レスポンス。"""

    repositories: list[DiscoveredRepository]
    total: int


class RepositoryUpdateRequest(BaseModel):
    """リポジトリ更新リクエスト。"""

    is_active: bool = Field(
        description="同期対象フラグ",
    )
