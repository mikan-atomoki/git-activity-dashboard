"""API v1 ルーター集約モジュール。

各ドメインのルーターを統合し、プレフィックスとタグを設定する。
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.summary import router as summary_router

from app.api.v1.repositories import router as repositories_router
from app.api.v1.settings import router as settings_router
from app.api.v1.sync import router as sync_router

router = APIRouter()

router.include_router(
    auth_router,
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["dashboard"],
)

router.include_router(
    summary_router,
    prefix="/summaries",
    tags=["summaries"],
)

router.include_router(
    repositories_router,
    prefix="/repositories",
    tags=["repositories"],
)

router.include_router(
    settings_router,
    prefix="/settings",
    tags=["settings"],
)

router.include_router(
    sync_router,
    prefix="/sync",
    tags=["sync"],
)
