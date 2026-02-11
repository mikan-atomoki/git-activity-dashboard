"""FastAPIアプリケーションのエントリポイント。

アプリケーションのライフサイクル管理、ミドルウェア設定、
ルーティング、例外ハンドラ登録を行う。
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.core.exceptions import register_exception_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """アプリケーションのライフサイクルを管理する。

    起動時にバックグラウンドタスクスケジューラを開始し、
    シャットダウン時に停止する。

    Args:
        app: FastAPIアプリケーションインスタンス。
    """
    # --- 起動処理 ---
    logger.info("Application startup")

    from app.tasks.scheduler import scheduler, setup_jobs

    setup_jobs()
    scheduler.start()
    logger.info("APScheduler started")

    yield

    # --- シャットダウン処理 ---
    logger.info("Application shutdown")

    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")


app = FastAPI(
    title="Git Activity Dashboard API",
    description="GitHub活動データの収集・分析・可視化を行うダッシュボードAPI",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# ミドルウェア
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 例外ハンドラ
# ---------------------------------------------------------------------------
register_exception_handlers(app)

# ---------------------------------------------------------------------------
# ルーティング
# ---------------------------------------------------------------------------
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """ヘルスチェックエンドポイント。"""
    return {"status": "ok"}
