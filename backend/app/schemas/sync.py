"""同期関連のPydanticスキーマ。

同期トリガー、ステータス確認、同期履歴のAPI用スキーマを定義する。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


class SyncTriggerRequest(BaseModel):
    """同期トリガーリクエスト。"""

    repo_ids: Optional[list[int]] = Field(
        default=None,
        description="同期対象のリポジトリIDリスト。Noneの場合は全アクティブリポジトリ",
    )
    full_sync: bool = Field(
        default=False,
        description="Trueの場合、全履歴を再同期する",
    )


class SyncTriggerResponse(BaseModel):
    """同期トリガーレスポンス。"""

    job_id: int
    status: str
    target_repos: list[int] = Field(
        description="同期対象のリポジトリIDリスト",
    )
    message: str = Field(
        default="Sync job started",
        description="ステータスメッセージ",
    )


class SyncStatusResponse(BaseModel):
    """同期ステータスレスポンス。"""

    model_config = ConfigDict(from_attributes=True)

    job_id: int
    status: str
    job_type: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    items_fetched: int = 0
    error_detail: Optional[dict[str, Any]] = None
    created_at: datetime


class SyncLogItem(BaseModel):
    """同期ログアイテム。"""

    model_config = ConfigDict(from_attributes=True)

    job_id: int
    job_type: str
    status: str
    repo_id: Optional[int] = None
    repo_full_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    items_fetched: int = 0
    error_detail: Optional[dict[str, Any]] = None
    created_at: datetime


class SyncHistoryResponse(BaseModel):
    """同期履歴レスポンス。"""

    logs: list[SyncLogItem]
    pagination: PaginationMeta
