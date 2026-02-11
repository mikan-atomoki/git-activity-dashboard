"""カスタム例外クラスおよびFastAPI例外ハンドラ登録。

アプリケーション全体で使用するドメイン固有の例外階層と、
FastAPIアプリケーションへのハンドラ登録関数を提供する。
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# 基底例外
# ---------------------------------------------------------------------------

class AppException(Exception):
    """アプリケーション基底例外。

    Attributes:
        status_code: HTTPステータスコード。
        detail: エラー詳細メッセージ。
    """

    def __init__(
        self,
        status_code: int = 500,
        detail: str = "Internal server error",
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


# ---------------------------------------------------------------------------
# 認証・認可
# ---------------------------------------------------------------------------

class AuthenticationError(AppException):
    """認証エラー (401 Unauthorized)。"""

    def __init__(self, detail: str = "Authentication failed") -> None:
        super().__init__(status_code=401, detail=detail)


class AuthorizationError(AppException):
    """認可エラー (403 Forbidden)。"""

    def __init__(self, detail: str = "Permission denied") -> None:
        super().__init__(status_code=403, detail=detail)


# ---------------------------------------------------------------------------
# リソース
# ---------------------------------------------------------------------------

class NotFoundError(AppException):
    """リソース未検出エラー (404 Not Found)。"""

    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(status_code=404, detail=detail)


# ---------------------------------------------------------------------------
# 外部API
# ---------------------------------------------------------------------------

class ExternalAPIError(AppException):
    """外部APIエラー (502 Bad Gateway)。"""

    def __init__(self, detail: str = "External API error") -> None:
        super().__init__(status_code=502, detail=detail)


class GitHubRateLimitError(ExternalAPIError):
    """GitHub APIレート制限エラー。"""

    def __init__(self, detail: str = "GitHub API rate limit exceeded") -> None:
        super().__init__(detail=detail)


class GeminiRateLimitError(ExternalAPIError):
    """Gemini APIレート制限エラー。"""

    def __init__(self, detail: str = "Gemini API rate limit exceeded") -> None:
        super().__init__(detail=detail)


class GeminiParseError(ExternalAPIError):
    """Gemini APIレスポンスパースエラー。"""

    def __init__(self, detail: str = "Failed to parse Gemini API response") -> None:
        super().__init__(detail=detail)


# ---------------------------------------------------------------------------
# FastAPI例外ハンドラ登録
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """FastAPIアプリケーションにカスタム例外ハンドラを登録する。

    Args:
        app: FastAPIアプリケーションインスタンス。
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ) -> JSONResponse:
        """AppException系例外をJSON形式でレスポンスする。"""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """未処理例外をキャッチし500レスポンスを返す。"""
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
