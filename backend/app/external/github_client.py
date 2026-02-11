"""GitHub REST API 非同期クライアント。

httpx.AsyncClient を使用し、レート制限管理、ETagキャッシュ、
自動ページネーション、バッチ取得を提供する。
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from typing import Any

import httpx

from app.core.exceptions import ExternalAPIError, GitHubRateLimitError
from app.core.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub REST API v3 非同期クライアント。

    Attributes:
        BASE_URL: GitHub API のベースURL。
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str) -> None:
        """GitHubClientを初期化する。

        Args:
            token: GitHub Personal Access Token。
        """
        self._token = token
        self._rate_limiter = get_rate_limiter()
        self._etag_cache: dict[str, tuple[str, Any]] = {}
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    # ------------------------------------------------------------------
    # Public API Methods
    # ------------------------------------------------------------------

    async def get_authenticated_user(self) -> dict[str, Any]:
        """認証済みユーザー情報を取得する。トークン検証にも使用。

        Returns:
            ユーザー情報辞書。

        Raises:
            ExternalAPIError: API呼び出しに失敗した場合。
        """
        response = await self._request("GET", "/user")
        return response.json()

    async def get_user_repos(
        self,
        include_private: bool = True,
        include_forks: bool = False,
    ) -> list[dict[str, Any]]:
        """認証ユーザーのリポジトリ一覧を取得する。

        Args:
            include_private: プライベートリポジトリを含むか。
            include_forks: フォークリポジトリを含むか。

        Returns:
            リポジトリ情報のリスト。
        """
        params: dict[str, str] = {
            "type": "owner",
            "sort": "pushed",
            "per_page": "100",
        }
        if not include_private:
            params["visibility"] = "public"

        repos = await self._paginate("/user/repos", params=params)

        if not include_forks:
            repos = [r for r in repos if not r.get("fork", False)]

        return repos

    async def get_commits(
        self,
        repo_full_name: str,
        since: datetime | None = None,
        author: str | None = None,
    ) -> list[dict[str, Any]]:
        """リポジトリのコミット一覧を取得する。

        Args:
            repo_full_name: "owner/repo" 形式のリポジトリ名。
            since: この日時以降のコミットを取得。
            author: 著者のGitHubログイン名でフィルタ。

        Returns:
            コミット情報のリスト。
        """
        params: dict[str, str] = {"per_page": "100"}
        if since is not None:
            params["since"] = since.isoformat()
        if author is not None:
            params["author"] = author

        return await self._paginate(
            f"/repos/{repo_full_name}/commits",
            params=params,
        )

    async def get_commit_detail(
        self,
        repo_full_name: str,
        sha: str,
    ) -> dict[str, Any]:
        """コミットの詳細情報（additions, deletions, files含む）を取得する。

        Args:
            repo_full_name: "owner/repo" 形式のリポジトリ名。
            sha: コミットSHA。

        Returns:
            コミット詳細辞書。
        """
        response = await self._request(
            "GET",
            f"/repos/{repo_full_name}/commits/{sha}",
        )
        return response.json()

    async def get_commit_diff(
        self,
        repo_full_name: str,
        sha: str,
    ) -> str:
        """コミットの生diffテキストを取得する（Gemini分析用）。

        Args:
            repo_full_name: "owner/repo" 形式のリポジトリ名。
            sha: コミットSHA。

        Returns:
            生diffテキスト。
        """
        response = await self._request(
            "GET",
            f"/repos/{repo_full_name}/commits/{sha}",
            headers={"Accept": "application/vnd.github.diff"},
        )
        return response.text

    async def get_commit_details_batch(
        self,
        repo_full_name: str,
        shas: list[str],
        concurrency: int = 5,
    ) -> list[dict[str, Any]]:
        """複数コミットの詳細情報をセマフォで並列取得する。

        Args:
            repo_full_name: "owner/repo" 形式のリポジトリ名。
            shas: コミットSHAのリスト。
            concurrency: 同時並行数上限。

        Returns:
            コミット詳細辞書のリスト（取得に成功したもの）。
        """
        semaphore = asyncio.Semaphore(concurrency)
        results: list[dict[str, Any]] = []

        async def _fetch(sha: str) -> dict[str, Any] | None:
            async with semaphore:
                try:
                    return await self.get_commit_detail(repo_full_name, sha)
                except ExternalAPIError as e:
                    logger.warning(
                        "Failed to fetch commit detail %s/%s: %s",
                        repo_full_name,
                        sha[:8],
                        e.detail,
                    )
                    return None

        tasks = [_fetch(sha) for sha in shas]
        fetched = await asyncio.gather(*tasks)
        for item in fetched:
            if item is not None:
                results.append(item)

        return results

    async def get_pull_requests(
        self,
        repo_full_name: str,
        state: str = "all",
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """リポジトリのPR一覧を取得する。

        Args:
            repo_full_name: "owner/repo" 形式のリポジトリ名。
            state: PRの状態 ("open", "closed", "all")。
            since: この日時以降に更新されたPRでフィルタ（クライアント側）。

        Returns:
            PR情報のリスト。
        """
        params: dict[str, str] = {
            "state": state,
            "sort": "updated",
            "direction": "desc",
            "per_page": "100",
        }

        prs = await self._paginate(
            f"/repos/{repo_full_name}/pulls",
            params=params,
        )

        # GitHub pulls API は since パラメータを持たないため、クライアント側でフィルタ
        if since is not None:
            since_iso = since.isoformat()
            prs = [
                pr
                for pr in prs
                if pr.get("updated_at", "") >= since_iso
            ]

        return prs

    async def get_languages(
        self,
        repo_full_name: str,
    ) -> dict[str, int]:
        """リポジトリの言語構成を取得する。

        Args:
            repo_full_name: "owner/repo" 形式のリポジトリ名。

        Returns:
            言語名をキー、バイト数を値とする辞書。
        """
        response = await self._request(
            "GET",
            f"/repos/{repo_full_name}/languages",
        )
        return response.json()

    async def get_file_content(
        self,
        repo_full_name: str,
        path: str,
    ) -> str | None:
        """リポジトリ内のファイル内容を取得する。

        GitHub Contents API を使用してファイルを取得し、base64デコードして返す。
        ファイルが存在しない場合は None を返す。

        Args:
            repo_full_name: "owner/repo" 形式のリポジトリ名。
            path: ファイルパス（例: "package.json"）。

        Returns:
            ファイル内容の文字列。404の場合はNone。
        """
        import base64

        try:
            response = await self._request(
                "GET",
                f"/repos/{repo_full_name}/contents/{path}",
            )
        except ExternalAPIError as e:
            if "not found" in e.detail.lower():
                return None
            raise

        data = response.json()
        content_b64 = data.get("content")
        if not content_b64:
            return None

        return base64.b64decode(content_b64).decode("utf-8", errors="replace")

    async def get_rate_limit(self) -> dict[str, Any]:
        """現在のレート制限情報を取得する。

        Returns:
            レート制限情報辞書。
        """
        response = await self._request("GET", "/rate_limit")
        return response.json()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """共通HTTPリクエストメソッド。

        レート制限の取得、ETagキャッシュ、レスポンスヘッダーからの
        レート制限情報更新、エラーハンドリングを行う。

        Args:
            method: HTTPメソッド。
            url: リクエストURL（相対パスまたは絶対URL）。
            **kwargs: httpx.AsyncClient.request に渡す追加引数。

        Returns:
            HTTPレスポンス。

        Raises:
            GitHubRateLimitError: レート制限超過時。
            ExternalAPIError: その他のAPIエラー時。
        """
        # レート制限を待機
        await self._rate_limiter.acquire_github()

        # ETagキャッシュの適用（GETリクエストのみ）
        cache_key = f"{method}:{url}"
        headers = dict(kwargs.pop("headers", {}) or {})
        if method.upper() == "GET" and cache_key in self._etag_cache:
            etag, _ = self._etag_cache[cache_key]
            headers["If-None-Match"] = etag
        kwargs["headers"] = headers

        try:
            response = await self._client.request(method, url, **kwargs)
        except httpx.HTTPError as e:
            logger.error("GitHub API request failed: %s %s - %s", method, url, str(e))
            raise ExternalAPIError(detail=f"GitHub API request failed: {e}")

        # レスポンスヘッダーからレート制限情報を更新
        self._rate_limiter.update_github_limits(dict(response.headers))

        # 304 Not Modified - キャッシュからデータを返す
        if response.status_code == 304 and cache_key in self._etag_cache:
            logger.debug("ETag cache hit for %s", url)
            _, cached_response = self._etag_cache[cache_key]
            return cached_response

        # ETagをキャッシュに保存
        etag_value = response.headers.get("ETag")
        if etag_value and method.upper() == "GET":
            self._etag_cache[cache_key] = (etag_value, response)

        # エラーハンドリング
        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining is not None and int(remaining) == 0:
                reset_at = response.headers.get("X-RateLimit-Reset", "unknown")
                raise GitHubRateLimitError(
                    detail=f"GitHub API rate limit exceeded. Resets at: {reset_at}"
                )
            raise ExternalAPIError(
                detail=f"GitHub API forbidden: {response.text[:200]}"
            )

        if response.status_code == 404:
            raise ExternalAPIError(
                detail=f"GitHub resource not found: {url}"
            )

        if response.status_code >= 400:
            raise ExternalAPIError(
                detail=(
                    f"GitHub API error {response.status_code}: "
                    f"{response.text[:200]}"
                )
            )

        return response

    async def _paginate(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Linkヘッダーベースの自動ページネーション。

        Args:
            url: 初回リクエストURL。
            params: クエリパラメータ。

        Returns:
            全ページ分のデータを結合したリスト。
        """
        all_items: list[dict[str, Any]] = []
        next_url: str | None = url

        while next_url is not None:
            if next_url == url:
                # 初回リクエスト: パラメータを渡す
                response = await self._request("GET", next_url, params=params)
            else:
                # ページネーション後続: URLにパラメータが含まれている
                response = await self._request("GET", next_url)

            data = response.json()
            if isinstance(data, list):
                all_items.extend(data)
            else:
                # 一部APIはオブジェクト形式で返す
                logger.warning(
                    "Unexpected non-list response during pagination: %s",
                    type(data),
                )
                break

            # 次のページURLを取得
            link_header = response.headers.get("Link", "")
            next_url = self._extract_next_url(link_header)

        return all_items

    @staticmethod
    def _extract_next_url(link_header: str) -> str | None:
        """Linkヘッダーから rel="next" のURLを抽出する。

        Args:
            link_header: HTTPレスポンスのLinkヘッダー値。

        Returns:
            次ページのURL。存在しない場合はNone。
        """
        if not link_header:
            return None

        # Link: <https://api.github.com/...?page=2>; rel="next", <...>; rel="last"
        pattern = r'<([^>]+)>;\s*rel="next"'
        match = re.search(pattern, link_header)
        return match.group(1) if match else None

    async def close(self) -> None:
        """HTTPクライアントセッションを閉じる。"""
        await self._client.aclose()
        logger.debug("GitHubClient session closed")

    async def __aenter__(self) -> GitHubClient:
        """async with 構文のサポート。"""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """async with 構文のサポート。"""
        await self.close()
