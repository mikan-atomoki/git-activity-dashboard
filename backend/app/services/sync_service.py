"""同期サービス。

GitHubからリポジトリ、コミット、PRを取得してDBに同期する
ビジネスロジックを提供する。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ExternalAPIError,
    GeminiRateLimitError,
    GitHubRateLimitError,
    NotFoundError,
)
from app.core.security import decrypt_token
from app.external.gemini_client import GeminiClient
from app.external.github_client import GitHubClient
from app.models import Commit, GeminiAnalysis, PullRequest, Repository, SyncJob, User
from app.tasks.gemini_analysis import analyze_single_commit

logger = logging.getLogger(__name__)


class SyncService:
    """GitHub同期サービス。

    リポジトリの検出、コミット・PRの同期、SyncJobの管理を行う。
    """

    def __init__(self, session: AsyncSession) -> None:
        """SyncServiceを初期化する。

        Args:
            session: 非同期データベースセッション。
        """
        self.session = session

    async def get_github_client(self, user: User) -> GitHubClient:
        """ユーザーのGitHubトークンを復号してクライアントを生成する。

        Args:
            user: Userモデルインスタンス。

        Returns:
            認証済みGitHubClientインスタンス。

        Raises:
            ExternalAPIError: トークンが未設定の場合。
        """
        if not user.access_token:
            raise ExternalAPIError(
                detail="GitHub token is not configured. Please set your token in settings."
            )
        try:
            token = decrypt_token(user.access_token)
        except Exception as e:
            logger.error("Failed to decrypt GitHub token for user %s: %s", user.user_id, e)
            raise ExternalAPIError(
                detail="Failed to decrypt GitHub token. Please re-configure your token."
            )
        return GitHubClient(token=token)

    async def discover_repositories(
        self,
        user: User,
        include_private: bool = True,
        include_forks: bool = False,
    ) -> list[dict[str, Any]]:
        """GitHubからリポジトリ一覧を取得し、既存の追跡情報を付与して返す。

        Args:
            user: Userモデルインスタンス。
            include_private: プライベートリポジトリを含むか。
            include_forks: フォークリポジトリを含むか。

        Returns:
            リポジトリ情報辞書のリスト（already_tracked, repo_id 付き）。
        """
        client = await self.get_github_client(user)
        try:
            github_repos = await client.get_user_repos(
                include_private=include_private,
                include_forks=include_forks,
            )
        finally:
            await client.close()

        # 既存の追跡情報を取得
        stmt = select(Repository.github_repo_id, Repository.repo_id).where(
            Repository.user_id == user.user_id,
        )
        result = await self.session.execute(stmt)
        tracked_map: dict[int, int] = {
            row.github_repo_id: row.repo_id for row in result
        }

        # GitHubレスポンスに追跡情報を付与
        discovered: list[dict[str, Any]] = []
        for repo in github_repos:
            github_repo_id = repo["id"]
            discovered.append(
                {
                    "github_repo_id": github_repo_id,
                    "full_name": repo["full_name"],
                    "description": repo.get("description"),
                    "primary_language": repo.get("language"),
                    "is_private": repo.get("private", False),
                    "is_fork": repo.get("fork", False),
                    "already_tracked": github_repo_id in tracked_map,
                    "repo_id": tracked_map.get(github_repo_id),
                    "pushed_at": repo.get("pushed_at"),
                    "stargazers_count": repo.get("stargazers_count", 0),
                }
            )

        return discovered

    async def sync_repository(
        self,
        client: GitHubClient,
        user: User,
        repo: Repository,
        full_sync: bool = False,
    ) -> int:
        """1リポジトリの同期を実行する。

        1. since = repo.last_synced_at (full_syncならNone)
        2. コミット一覧取得
        3. コミット詳細をバッチ取得
        4. PR一覧取得
        5. 言語情報取得
        6. upsert_commits, upsert_pull_requests
        7. repo.last_synced_at 更新

        Args:
            client: GitHubClientインスタンス。
            user: Userモデルインスタンス。
            repo: Repositoryモデルインスタンス。
            full_sync: Trueの場合、全履歴を再同期する。

        Returns:
            取得したコミット数。
        """
        since = None if full_sync else repo.last_synced_at
        total_commits = 0

        logger.info(
            "Syncing repository %s (repo_id=%d, since=%s, full_sync=%s)",
            repo.full_name,
            repo.repo_id,
            since,
            full_sync,
        )

        # 1. コミット一覧取得
        try:
            commits_list = await client.get_commits(
                repo_full_name=repo.full_name,
                since=since,
                author=user.github_login,
            )
        except ExternalAPIError as e:
            logger.warning(
                "Failed to fetch commits for %s: %s",
                repo.full_name,
                e.detail,
            )
            commits_list = []

        # 2. コミット詳細をバッチ取得
        if commits_list:
            shas = [c["sha"] for c in commits_list]
            commit_details = await client.get_commit_details_batch(
                repo_full_name=repo.full_name,
                shas=shas,
                concurrency=5,
            )

            # 3. コミットのupsert
            upserted = await self._upsert_commits(repo.repo_id, commit_details)
            total_commits = upserted
            logger.info(
                "Upserted %d commits for %s",
                upserted,
                repo.full_name,
            )

        # 4. PR一覧取得
        try:
            prs_list = await client.get_pull_requests(
                repo_full_name=repo.full_name,
                state="all",
                since=since,
            )
            if prs_list:
                pr_count = await self._upsert_pull_requests(repo.repo_id, prs_list)
                logger.info(
                    "Upserted %d pull requests for %s",
                    pr_count,
                    repo.full_name,
                )
        except ExternalAPIError as e:
            logger.warning(
                "Failed to fetch PRs for %s: %s",
                repo.full_name,
                e.detail,
            )

        # 5. 言語情報取得
        try:
            languages = await client.get_languages(repo.full_name)
            if languages:
                # 最もバイト数の多い言語をprimary_languageに設定
                primary_lang = max(languages, key=languages.get)  # type: ignore[arg-type]
                repo.primary_language = primary_lang
                repo.repo_metadata = {
                    **repo.repo_metadata,
                    "languages": languages,
                }
        except ExternalAPIError as e:
            logger.warning(
                "Failed to fetch languages for %s: %s",
                repo.full_name,
                e.detail,
            )

        # 6. Gemini分析（新規コミットのみ）
        if commits_list:
            analyzed = await self._analyze_new_commits(repo, commit_details)
            logger.info(
                "Analyzed %d commits with Gemini for %s",
                analyzed,
                repo.full_name,
            )

        # 7. last_synced_at更新
        repo.last_synced_at = datetime.now(timezone.utc)
        self.session.add(repo)
        await self.session.flush()

        return total_commits

    async def sync_all(
        self,
        user: User,
        repo_ids: list[int] | None = None,
        full_sync: bool = False,
    ) -> SyncJob:
        """全リポジトリの同期を実行する。

        1. SyncJobレコード作成 (status=running)
        2. 対象リポジトリをループ、sync_repositoryを呼ぶ
        3. エラーハンドリング（GitHubRateLimitErrorで中断）
        4. SyncJob完了更新

        Args:
            user: Userモデルインスタンス。
            repo_ids: 同期対象のリポジトリIDリスト。Noneの場合は全アクティブリポジトリ。
            full_sync: Trueの場合、全履歴を再同期する。

        Returns:
            完了したSyncJobインスタンス。
        """
        # 同期前に新規リポジトリを自動検出・登録
        if not repo_ids:
            await self._auto_discover_new_repos(user)

        # 対象リポジトリを取得
        stmt = select(Repository).where(
            Repository.user_id == user.user_id,
            Repository.is_active.is_(True),
        )
        if repo_ids:
            stmt = stmt.where(Repository.repo_id.in_(repo_ids))

        result = await self.session.execute(stmt)
        repos = list(result.scalars().all())

        if not repos:
            logger.info("No active repositories to sync for user %s", user.user_id)

        # SyncJobレコード作成
        sync_job = SyncJob(
            user_id=user.user_id,
            job_type="manual_sync" if repo_ids else "scheduled_sync",
            status="running",
            started_at=datetime.now(timezone.utc),
            items_fetched=0,
        )
        self.session.add(sync_job)
        await self.session.flush()

        logger.info(
            "Starting sync job %d for user %d (%d repositories)",
            sync_job.job_id,
            user.user_id,
            len(repos),
        )

        total_items = 0
        error_detail: dict[str, Any] | None = None

        client = await self.get_github_client(user)
        try:
            for repo in repos:
                try:
                    count = await self.sync_repository(
                        client=client,
                        user=user,
                        repo=repo,
                        full_sync=full_sync,
                    )
                    total_items += count
                except GitHubRateLimitError as e:
                    logger.error(
                        "GitHub rate limit hit during sync job %d: %s",
                        sync_job.job_id,
                        e.detail,
                    )
                    error_detail = {
                        "type": "rate_limit",
                        "message": e.detail,
                        "repo_full_name": repo.full_name,
                    }
                    break
                except ExternalAPIError as e:
                    logger.error(
                        "External API error syncing %s in job %d: %s",
                        repo.full_name,
                        sync_job.job_id,
                        e.detail,
                    )
                    error_detail = {
                        "type": "api_error",
                        "message": e.detail,
                        "repo_full_name": repo.full_name,
                    }
                    # 個別リポジトリのエラーでは続行
                    continue
                except Exception as e:
                    logger.exception(
                        "Unexpected error syncing %s in job %d",
                        repo.full_name,
                        sync_job.job_id,
                    )
                    error_detail = {
                        "type": "unexpected_error",
                        "message": str(e),
                        "repo_full_name": repo.full_name,
                    }
                    continue
        finally:
            await client.close()

        # SyncJob完了更新
        sync_job.status = "failed" if error_detail and error_detail.get("type") == "rate_limit" else "completed"
        sync_job.completed_at = datetime.now(timezone.utc)
        sync_job.items_fetched = total_items
        sync_job.error_detail = error_detail
        self.session.add(sync_job)
        await self.session.flush()

        logger.info(
            "Sync job %d %s: %d items fetched",
            sync_job.job_id,
            sync_job.status,
            total_items,
        )

        return sync_job

    # ------------------------------------------------------------------
    # Gemini分析
    # ------------------------------------------------------------------

    async def _analyze_new_commits(
        self,
        repo: Repository,
        commit_details: list[dict[str, Any]],
    ) -> int:
        """同期直後の新規コミットをGeminiで分析する。

        既に分析済みのコミットはスキップ。レート制限到達時は
        残りを諦めて続行する（同期自体は止めない）。

        Args:
            repo: リポジトリインスタンス。
            commit_details: GitHub APIから取得したコミット詳細のリスト。

        Returns:
            分析成功したコミット数。
        """
        # 分析済みコミットIDを取得
        shas = [c.get("sha", "") for c in commit_details if c.get("sha")]
        stmt = select(Commit).where(
            Commit.repo_id == repo.repo_id,
            Commit.github_commit_sha.in_(shas),
        )
        result = await self.session.execute(stmt)
        db_commits = {c.github_commit_sha: c for c in result.scalars().all()}

        # 既に分析済みのsource_idを取得
        existing_analyses = set()
        if db_commits:
            commit_ids = [c.commit_id for c in db_commits.values()]
            stmt_ga = select(GeminiAnalysis.source_id).where(
                GeminiAnalysis.source_type == "commit",
                GeminiAnalysis.source_id.in_(commit_ids),
            )
            result_ga = await self.session.execute(stmt_ga)
            existing_analyses = {row[0] for row in result_ga.all()}

        gemini = GeminiClient()
        analyzed = 0

        for sha, commit in db_commits.items():
            if commit.commit_id in existing_analyses:
                continue

            try:
                analysis = await analyze_single_commit(
                    self.session, gemini, commit, repo.full_name,
                )
                if analysis is not None:
                    self.session.add(analysis)
                    await self.session.flush()
                    analyzed += 1
            except GeminiRateLimitError:
                logger.warning(
                    "Gemini rate limit hit during sync analysis for %s. "
                    "Analyzed %d commits before stopping.",
                    repo.full_name,
                    analyzed,
                )
                break
            except Exception:
                logger.exception(
                    "Gemini analysis failed for commit %s in %s",
                    sha[:8],
                    repo.full_name,
                )
                continue

        return analyzed

    # ------------------------------------------------------------------
    # リポジトリ自動検出
    # ------------------------------------------------------------------

    async def _auto_discover_new_repos(self, user: User) -> int:
        """同期前に新規リポジトリを自動検出してDBに登録する。

        Args:
            user: Userモデルインスタンス。

        Returns:
            新規登録したリポジトリ数。
        """
        try:
            discovered = await self.discover_repositories(
                user, include_private=True, include_forks=False,
            )
        except Exception:
            logger.exception(
                "Auto-discover failed for user %s, skipping",
                user.github_login,
            )
            return 0

        registered = 0
        for repo_info in discovered:
            if repo_info["already_tracked"]:
                continue

            new_repo = Repository(
                user_id=user.user_id,
                github_repo_id=repo_info["github_repo_id"],
                full_name=repo_info["full_name"],
                description=repo_info.get("description"),
                primary_language=repo_info.get("primary_language"),
                is_private=repo_info.get("is_private", False),
                is_active=True,
            )
            self.session.add(new_repo)
            registered += 1

        if registered:
            await self.session.flush()
            logger.info(
                "Auto-discovered %d new repositories for user %s",
                registered,
                user.github_login,
            )

        return registered

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    async def _upsert_commits(
        self,
        repo_id: int,
        commits: list[dict[str, Any]],
    ) -> int:
        """コミットのbulk upsertを実行する。

        PostgreSQL ON CONFLICT DO UPDATE を使用して、
        既存のコミットは更新、新規コミットは挿入する。

        Args:
            repo_id: リポジトリID。
            commits: GitHub APIから取得したコミット詳細辞書のリスト。

        Returns:
            処理したコミット数。
        """
        if not commits:
            return 0

        upserted_count = 0
        for commit_data in commits:
            sha = commit_data.get("sha", "")
            commit_info = commit_data.get("commit", {})
            stats = commit_data.get("stats", {})
            files = commit_data.get("files", [])

            # コミット日時の取得
            committed_at_str = (
                commit_info.get("committer", {}).get("date")
                or commit_info.get("author", {}).get("date")
            )
            if not committed_at_str:
                logger.warning("Skipping commit %s: no date found", sha[:8])
                continue

            committed_at = datetime.fromisoformat(
                committed_at_str.replace("Z", "+00:00")
            )

            # 既存のコミットを検索
            stmt = select(Commit).where(
                Commit.repo_id == repo_id,
                Commit.github_commit_sha == sha,
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing is not None:
                # 既存のコミットを更新
                existing.additions = stats.get("additions", 0)
                existing.deletions = stats.get("deletions", 0)
                existing.changed_files = len(files)
                existing.raw_data = {
                    "stats": stats,
                    "files": [
                        {
                            "filename": f.get("filename"),
                            "status": f.get("status"),
                            "additions": f.get("additions", 0),
                            "deletions": f.get("deletions", 0),
                            "patch": f.get("patch", "")[:500],
                        }
                        for f in files[:50]
                    ],
                }
                self.session.add(existing)
            else:
                # 新規コミットを挿入
                new_commit = Commit(
                    repo_id=repo_id,
                    github_commit_sha=sha,
                    message=commit_info.get("message", "")[:2000],
                    committed_at=committed_at,
                    additions=stats.get("additions", 0),
                    deletions=stats.get("deletions", 0),
                    changed_files=len(files),
                    raw_data={
                        "stats": stats,
                        "files": [
                            {
                                "filename": f.get("filename"),
                                "status": f.get("status"),
                                "additions": f.get("additions", 0),
                                "deletions": f.get("deletions", 0),
                                "patch": f.get("patch", "")[:500],
                            }
                            for f in files[:50]
                        ],
                    },
                )
                self.session.add(new_commit)

            upserted_count += 1

        await self.session.flush()
        return upserted_count

    async def _upsert_pull_requests(
        self,
        repo_id: int,
        prs: list[dict[str, Any]],
    ) -> int:
        """PRのbulk upsertを実行する。

        Args:
            repo_id: リポジトリID。
            prs: GitHub APIから取得したPR辞書のリスト。

        Returns:
            処理したPR数。
        """
        if not prs:
            return 0

        upserted_count = 0
        for pr_data in prs:
            github_pr_id = pr_data.get("id")
            github_pr_number = pr_data.get("number")
            if not github_pr_id or not github_pr_number:
                continue

            pr_created_at_str = pr_data.get("created_at")
            if not pr_created_at_str:
                continue

            pr_created_at = datetime.fromisoformat(
                pr_created_at_str.replace("Z", "+00:00")
            )

            pr_closed_at = None
            if pr_data.get("closed_at"):
                pr_closed_at = datetime.fromisoformat(
                    pr_data["closed_at"].replace("Z", "+00:00")
                )

            merged_at = None
            if pr_data.get("merged_at"):
                merged_at = datetime.fromisoformat(
                    pr_data["merged_at"].replace("Z", "+00:00")
                )

            # 既存のPRを検索
            stmt = select(PullRequest).where(
                PullRequest.repo_id == repo_id,
                PullRequest.github_pr_id == github_pr_id,
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing is not None:
                # 既存のPRを更新
                existing.title = pr_data.get("title")
                existing.state = pr_data.get("state", "open")
                existing.additions = pr_data.get("additions", 0)
                existing.deletions = pr_data.get("deletions", 0)
                existing.changed_files = pr_data.get("changed_files", 0)
                existing.pr_closed_at = pr_closed_at
                existing.merged_at = merged_at
                existing.raw_data = {
                    "labels": [l.get("name") for l in pr_data.get("labels", [])],
                    "user": pr_data.get("user", {}).get("login"),
                    "head_ref": pr_data.get("head", {}).get("ref"),
                    "base_ref": pr_data.get("base", {}).get("ref"),
                }
                self.session.add(existing)
            else:
                # 新規PRを挿入
                new_pr = PullRequest(
                    repo_id=repo_id,
                    github_pr_id=github_pr_id,
                    github_pr_number=github_pr_number,
                    title=pr_data.get("title"),
                    state=pr_data.get("state", "open"),
                    additions=pr_data.get("additions", 0),
                    deletions=pr_data.get("deletions", 0),
                    changed_files=pr_data.get("changed_files", 0),
                    pr_created_at=pr_created_at,
                    pr_closed_at=pr_closed_at,
                    merged_at=merged_at,
                    raw_data={
                        "labels": [l.get("name") for l in pr_data.get("labels", [])],
                        "user": pr_data.get("user", {}).get("login"),
                        "head_ref": pr_data.get("head", {}).get("ref"),
                        "base_ref": pr_data.get("base", {}).get("ref"),
                    },
                )
                self.session.add(new_pr)

            upserted_count += 1

        await self.session.flush()
        return upserted_count
