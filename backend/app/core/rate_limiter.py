"""外部APIレート制限管理モジュール。

GitHub APIのヘッダーベースレート制限と、
Gemini APIのTokenBucketベースレート制限を管理する。
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional


class TokenBucket:
    """トークンバケットアルゴリズムによるレート制限。

    指定された速度でトークンが補充され、バースト上限まで蓄積される。

    Attributes:
        rate: 1秒あたりの許可リクエスト数。
        burst: バースト上限（最大蓄積トークン数）。
    """

    def __init__(self, rate: float, burst: int) -> None:
        """TokenBucketを初期化する。

        Args:
            rate: 1秒あたりの許可リクエスト数。
            burst: バースト上限。
        """
        self.rate = rate
        self.burst = burst
        self._tokens: float = float(burst)
        self._last_refill: float = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        """経過時間に基づきトークンを補充する。"""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_refill = now

    async def acquire(self) -> None:
        """トークンを1つ取得する。利用可能になるまで非同期で待機する。"""
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                # 次のトークンが利用可能になるまでの待機時間を計算
                wait_time = (1.0 - self._tokens) / self.rate
            await asyncio.sleep(wait_time)


class ExternalAPIRateLimiter:
    """外部APIレート制限を一元管理するクラス。

    GitHub: X-RateLimit-Remaining / X-RateLimit-Reset ヘッダーベース。
    Gemini: TokenBucket (15 RPM)。
    """

    def __init__(self) -> None:
        # GitHub レート制限状態
        self._github_remaining: Optional[int] = None
        self._github_reset: Optional[float] = None
        self._github_lock = asyncio.Lock()

        # Gemini レート制限 (15 RPM = 0.25 RPS)
        self._gemini_bucket = TokenBucket(rate=15.0 / 60.0, burst=15)

    async def acquire_github(self) -> None:
        """GitHub APIリクエスト前に呼び出し、レート制限を遵守する。

        X-RateLimit-Remaining が0の場合、リセット時刻まで非同期で待機する。
        ヘッダー情報が未設定の場合は即座に通過する。
        """
        async with self._github_lock:
            if self._github_remaining is not None and self._github_remaining <= 0:
                if self._github_reset is not None:
                    now = time.time()
                    wait_time = self._github_reset - now
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)
                    # リセット後に制限状態をクリア
                    self._github_remaining = None
                    self._github_reset = None

    def update_github_limits(self, headers: dict) -> None:
        """GitHub APIレスポンスヘッダーからレート制限情報を更新する。

        Args:
            headers: HTTPレスポンスヘッダー辞書。
                期待するキー:
                - X-RateLimit-Remaining: 残りリクエスト数
                - X-RateLimit-Reset: リセット時刻（UNIXタイムスタンプ）
        """
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")

        if remaining is not None:
            self._github_remaining = int(remaining)
        if reset is not None:
            self._github_reset = float(reset)

    async def acquire_gemini(self) -> None:
        """Gemini APIリクエスト前に呼び出し、レート制限を遵守する。

        TokenBucketアルゴリズムにより15 RPMを超えないよう制御する。
        """
        await self._gemini_bucket.acquire()


# ---------------------------------------------------------------------------
# シングルトン
# ---------------------------------------------------------------------------

_rate_limiter: Optional[ExternalAPIRateLimiter] = None


def get_rate_limiter() -> ExternalAPIRateLimiter:
    """ExternalAPIRateLimiterのシングルトンインスタンスを取得する。

    Returns:
        ExternalAPIRateLimiterインスタンス。
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = ExternalAPIRateLimiter()
    return _rate_limiter
