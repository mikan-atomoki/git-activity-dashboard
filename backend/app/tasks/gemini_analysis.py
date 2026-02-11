"""Gemini diff分析バッチジョブ。

APSchedulerから定期呼び出しされ、未分析のコミットに対して
Gemini APIでdiff分析を実行し、結果をgemini_analysesテーブルに保存する。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.external.gemini_client import DiffAnalysisResult, GeminiClient
from app.core.exceptions import GeminiRateLimitError
from app.models import Commit, GeminiAnalysis, Repository

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# メインジョブ
# ---------------------------------------------------------------------------


async def gemini_analysis_job() -> None:
    """APSchedulerから呼ばれる定期分析ジョブ。

    処理フロー:
    1. async_session_factoryでセッション取得
    2. gemini_analysesに未登録のコミットを取得（additions+deletions降順、上限50件）
    3. 各コミットに対してGeminiで分析を実行しDB保存
    4. GeminiRateLimitError時はバッチを中断
    """
    logger.info("Gemini analysis job started")
    analyzed_count = 0
    skipped_count = 0
    error_count = 0

    try:
        async with async_session_factory() as session:
            # 未分析コミットを取得
            unanalyzed_commits = await _fetch_unanalyzed_commits(session, limit=50)

            if not unanalyzed_commits:
                logger.info("No unanalyzed commits found. Job finished.")
                return

            logger.info(
                "Found %d unanalyzed commits to process.",
                len(unanalyzed_commits),
            )

            gemini = GeminiClient()

            for commit, repo_full_name in unanalyzed_commits:
                try:
                    analysis = await analyze_single_commit(
                        session, gemini, commit, repo_full_name,
                    )
                    if analysis is not None:
                        session.add(analysis)
                        await session.commit()
                        analyzed_count += 1
                        logger.info(
                            "Analyzed commit %s (repo=%s, category=%s)",
                            commit.github_commit_sha[:8],
                            repo_full_name,
                            analysis.work_category,
                        )
                    else:
                        skipped_count += 1
                        logger.debug(
                            "Skipped commit %s (no diff available)",
                            commit.github_commit_sha[:8],
                        )

                    # レート制限対策: 各分析間で1秒待機
                    await asyncio.sleep(1.0)

                except GeminiRateLimitError:
                    logger.warning(
                        "Gemini rate limit hit. Aborting batch after %d analyses.",
                        analyzed_count,
                    )
                    break

                except Exception:
                    error_count += 1
                    logger.exception(
                        "Failed to analyze commit %s (repo=%s)",
                        commit.github_commit_sha[:8],
                        repo_full_name,
                    )
                    # 個別コミットのエラーではバッチを中断しない
                    continue

    except Exception:
        logger.exception("Gemini analysis job failed with unexpected error")

    logger.info(
        "Gemini analysis job finished: analyzed=%d, skipped=%d, errors=%d",
        analyzed_count,
        skipped_count,
        error_count,
    )


# ---------------------------------------------------------------------------
# 未分析コミット取得
# ---------------------------------------------------------------------------


async def _fetch_unanalyzed_commits(
    session: AsyncSession,
    limit: int = 50,
) -> list[tuple[Commit, str]]:
    """gemini_analysesに未登録のコミットを取得する。

    additions + deletions が大きい順（変更規模が大きいコミットを優先）。

    Args:
        session: データベースセッション。
        limit: 取得上限件数。

    Returns:
        (Commit, repo_full_name) のタプルリスト。
    """
    # サブクエリ: 既に分析済みのcommit_idを取得
    analyzed_subq = (
        select(GeminiAnalysis.source_id)
        .where(GeminiAnalysis.source_type == "commit")
        .correlate(Commit)
        .scalar_subquery()
    )

    stmt = (
        select(Commit, Repository.full_name)
        .join(Repository, Commit.repo_id == Repository.repo_id)
        .where(
            Commit.commit_id.notin_(analyzed_subq),
        )
        .order_by((Commit.additions + Commit.deletions).desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


# ---------------------------------------------------------------------------
# 単一コミット分析
# ---------------------------------------------------------------------------


async def analyze_single_commit(
    session: AsyncSession,
    gemini: GeminiClient,
    commit: Commit,
    repo_full_name: str,
) -> GeminiAnalysis | None:
    """1コミットを分析してGeminiAnalysisレコードを返す。

    raw_dataからdiffを取得する。diffが存在しない場合は
    コミットメッセージのみで簡易分析を行う。
    GitHub APIは叩かない。

    Args:
        session: データベースセッション。
        gemini: GeminiClientインスタンス。
        commit: 分析対象のCommitオブジェクト。
        repo_full_name: リポジトリのフルネーム (owner/repo)。

    Returns:
        作成されたGeminiAnalysisオブジェクト。diff取得不可の場合はNone。

    Raises:
        GeminiRateLimitError: レート制限超過時。
    """
    # raw_dataからdiffテキストを取得
    diff_text = _extract_diff_from_raw_data(commit.raw_data)

    if not diff_text:
        # diffがない場合、filesフィールドからパッチ情報を構築
        diff_text = _build_diff_from_files(commit.raw_data)

    if not diff_text:
        # それでもdiffが取得できない場合はスキップ
        logger.debug(
            "No diff data available for commit %s, skipping.",
            commit.github_commit_sha[:8],
        )
        return None

    # diffをトランケート
    diff_text = truncate_diff(diff_text, max_chars=30000)

    commit_message = commit.message or ""

    # Gemini API呼び出し
    result: DiffAnalysisResult = await gemini.analyze_diff(
        diff=diff_text,
        commit_message=commit_message,
        repo_name=repo_full_name,
    )

    # GeminiAnalysisレコードを作成
    now = datetime.now(timezone.utc)
    analysis = GeminiAnalysis(
        source_type="commit",
        source_id=commit.commit_id,
        repo_id=commit.repo_id,
        tech_tags=result.technologies_detected,
        work_category=result.work_category,
        summary=result.summary,
        complexity_score=Decimal(str(round(result.complexity_score, 1))),
        raw_response=result.model_dump(),
        analyzed_at=now,
    )

    return analysis


# ---------------------------------------------------------------------------
# diff抽出ヘルパー
# ---------------------------------------------------------------------------


def _extract_diff_from_raw_data(raw_data: dict[str, Any]) -> str:
    """raw_dataからdiffテキストを抽出する。

    GitHub APIのコミット詳細レスポンスにはfilesフィールドにpatch情報が含まれる。
    また、diff専用フィールドが保存されている場合はそちらを使用する。

    Args:
        raw_data: コミットのraw_data (JSONB)。

    Returns:
        diffテキスト。取得できない場合は空文字列。
    """
    # 直接diffフィールドが保存されている場合
    if "diff" in raw_data and isinstance(raw_data["diff"], str):
        return raw_data["diff"]

    return ""


def _build_diff_from_files(raw_data: dict[str, Any]) -> str:
    """raw_dataのfilesフィールドからdiffテキストを構築する。

    GitHub APIのコミット詳細レスポンスには files[].patch にファイル単位の
    パッチが含まれる。

    Args:
        raw_data: コミットのraw_data (JSONB)。

    Returns:
        構築されたdiffテキスト。取得できない場合は空文字列。
    """
    files = raw_data.get("files", [])
    if not files or not isinstance(files, list):
        return ""

    diff_parts: list[str] = []
    for file_info in files:
        if not isinstance(file_info, dict):
            continue
        filename = file_info.get("filename", "unknown")
        patch = file_info.get("patch", "")
        status = file_info.get("status", "modified")

        if patch:
            diff_parts.append(f"--- a/{filename}")
            diff_parts.append(f"+++ b/{filename}")
            diff_parts.append(f"Status: {status}")
            diff_parts.append(patch)
            diff_parts.append("")

    return "\n".join(diff_parts)


# ---------------------------------------------------------------------------
# diffトランケート
# ---------------------------------------------------------------------------


def truncate_diff(diff_text: str, max_chars: int = 30000) -> str:
    """Geminiの入力上限を考慮してdiffをトランケートする。

    ファイル単位で切り詰め、最後に "[truncated]" を付加する。
    diffが既にmax_chars以下の場合はそのまま返す。

    Args:
        diff_text: 元のdiffテキスト。
        max_chars: 最大文字数。

    Returns:
        トランケート済みdiffテキスト。
    """
    if len(diff_text) <= max_chars:
        return diff_text

    # ファイル境界("diff --git" または "--- a/")で分割
    import re
    file_pattern = re.compile(r"(?=^diff --git |^--- a/)", re.MULTILINE)
    file_sections = file_pattern.split(diff_text)

    truncated_parts: list[str] = []
    current_length = 0
    truncation_marker = "\n\n[truncated: remaining files omitted due to size limit]"
    reserved = len(truncation_marker)

    for section in file_sections:
        if not section.strip():
            continue
        section_length = len(section)
        if current_length + section_length + reserved > max_chars:
            break
        truncated_parts.append(section)
        current_length += section_length

    # 何もファイルセクションがない場合は文字数で切る
    if not truncated_parts:
        return diff_text[: max_chars - reserved] + truncation_marker

    result = "".join(truncated_parts)
    if len(result) < len(diff_text):
        result += truncation_marker

    return result
