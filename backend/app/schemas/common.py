"""共通Pydanticスキーマ。

ページネーション等、複数エンドポイントで再利用するスキーマを定義する。
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field, computed_field


class PaginationMeta(BaseModel):
    """ページネーションメタ情報。"""

    page: int = Field(..., ge=1, description="現在のページ番号")
    per_page: int = Field(..., ge=1, le=100, description="1ページあたりの件数")
    total: int = Field(..., ge=0, description="総件数")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_pages(self) -> int:
        """総ページ数を算出する。"""
        if self.total == 0:
            return 0
        return math.ceil(self.total / self.per_page)
