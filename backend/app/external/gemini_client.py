"""Gemini API 非同期クライアント。

google-generativeai ライブラリを使用し、コミットdiff分析、
週次/月次サマリー生成機能を提供する。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import google.generativeai as genai
from pydantic import BaseModel, Field

from app.config import settings
from app.core.exceptions import GeminiParseError, GeminiRateLimitError
from app.core.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# レスポンスモデル
# ---------------------------------------------------------------------------

class DiffAnalysisResult(BaseModel):
    """コミットdiff分析結果。"""

    summary: str = ""
    work_category: str = "other"
    technologies_detected: list[str] = Field(default_factory=list)
    complexity_score: float = 1.0
    quality_notes: list[str] = Field(default_factory=list)

    @classmethod
    def fallback(cls, raw: dict[str, Any]) -> DiffAnalysisResult:
        """パース失敗時のフォールバック。

        部分的にパースできたフィールドを採用し、取得できなかった
        フィールドはデフォルト値で埋める。

        Args:
            raw: 部分的にパースされた辞書。

        Returns:
            デフォルト値で補完されたDiffAnalysisResult。
        """
        return cls(
            summary=raw.get("summary", "分析結果を取得できませんでした"),
            work_category=raw.get("work_category", "other"),
            technologies_detected=raw.get("technologies_detected", []),
            complexity_score=float(raw.get("complexity_score", 1.0)),
            quality_notes=raw.get("quality_notes", []),
        )


class WeeklySummaryResult(BaseModel):
    """週次サマリー結果。"""

    highlight: str = ""
    key_achievements: list[str] = Field(default_factory=list)
    technologies_used: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    focus_areas: list[str] = Field(default_factory=list)

    @classmethod
    def fallback(cls, raw: dict[str, Any]) -> WeeklySummaryResult:
        """パース失敗時のフォールバック。"""
        return cls(
            highlight=raw.get("highlight", "サマリーを生成できませんでした"),
            key_achievements=raw.get("key_achievements", []),
            technologies_used=raw.get("technologies_used", []),
            suggestions=raw.get("suggestions", []),
            focus_areas=raw.get("focus_areas", []),
        )


class MonthlySummaryResult(BaseModel):
    """月次サマリー結果。"""

    narrative: str = ""
    growth_areas: list[str] = Field(default_factory=list)
    monthly_highlights: list[str] = Field(default_factory=list)

    @classmethod
    def fallback(cls, raw: dict[str, Any]) -> MonthlySummaryResult:
        """パース失敗時のフォールバック。"""
        return cls(
            narrative=raw.get("narrative", "月次サマリーを生成できませんでした"),
            growth_areas=raw.get("growth_areas", []),
            monthly_highlights=raw.get("monthly_highlights", []),
        )


class RepoTechStackResult(BaseModel):
    """リポジトリ技術スタック分析結果。"""

    domain: str = "general"
    domain_detail: str = ""
    frameworks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    infrastructure: list[str] = Field(default_factory=list)
    project_type: str = ""

    @classmethod
    def fallback(cls, raw: dict[str, Any]) -> RepoTechStackResult:
        """パース失敗時のフォールバック。"""
        return cls(
            domain=raw.get("domain", "general"),
            domain_detail=raw.get("domain_detail", ""),
            frameworks=raw.get("frameworks", []),
            tools=raw.get("tools", []),
            infrastructure=raw.get("infrastructure", []),
            project_type=raw.get("project_type", ""),
        )


# ---------------------------------------------------------------------------
# Gemini クライアント
# ---------------------------------------------------------------------------

class GeminiClient:
    """Gemini API クライアント。

    レート制限管理、JSON応答パース、フォールバック処理を備える。
    """

    def __init__(self) -> None:
        """GeminiClientを初期化する。"""
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
        self._rate_limiter = get_rate_limiter()

    # ------------------------------------------------------------------
    # diff分析
    # ------------------------------------------------------------------

    async def analyze_diff(
        self,
        diff: str,
        commit_message: str,
        repo_name: str,
    ) -> DiffAnalysisResult:
        """コミットdiffをGeminiで分析する。

        Args:
            diff: コミットのdiffテキスト。
            commit_message: コミットメッセージ。
            repo_name: リポジトリのフルネーム (owner/repo)。

        Returns:
            DiffAnalysisResult。

        Raises:
            GeminiRateLimitError: レート制限超過時。
            GeminiParseError: レスポンスのパースに完全に失敗した場合。
        """
        prompt = self._build_diff_analysis_prompt(diff, commit_message, repo_name)
        raw_response = await self._generate(prompt)
        parsed = self._parse_json_response(raw_response)

        if parsed is None:
            logger.warning(
                "Gemini diff analysis JSON parse failed for repo=%s, "
                "returning fallback result. raw=%s",
                repo_name,
                raw_response[:500],
            )
            return DiffAnalysisResult.fallback({})

        return DiffAnalysisResult.fallback(parsed)

    # ------------------------------------------------------------------
    # 週次サマリー
    # ------------------------------------------------------------------

    async def generate_weekly_summary(
        self,
        commits_data: list[dict[str, Any]],
        prs_data: list[dict[str, Any]],
        analyses_data: list[dict[str, Any]],
        week_start: str,
        week_end: str,
    ) -> WeeklySummaryResult:
        """週次サマリーを生成する。

        Args:
            commits_data: 1週間分のコミット情報リスト。
            prs_data: 1週間分のPR情報リスト。
            analyses_data: 1週間分のdiff分析結果リスト。
            week_start: 週の開始日 (YYYY-MM-DD)。
            week_end: 週の終了日 (YYYY-MM-DD)。

        Returns:
            WeeklySummaryResult。

        Raises:
            GeminiRateLimitError: レート制限超過時。
        """
        prompt = self._build_weekly_summary_prompt(
            commits_data, prs_data, analyses_data, week_start, week_end,
        )
        raw_response = await self._generate(prompt)
        parsed = self._parse_json_response(raw_response)

        if parsed is None:
            logger.warning(
                "Gemini weekly summary JSON parse failed for %s~%s, "
                "returning fallback result.",
                week_start,
                week_end,
            )
            return WeeklySummaryResult.fallback({})

        return WeeklySummaryResult.fallback(parsed)

    # ------------------------------------------------------------------
    # 月次サマリー
    # ------------------------------------------------------------------

    async def generate_monthly_summary(
        self,
        weekly_summaries: list[dict[str, Any]],
        month_stats: dict[str, Any],
    ) -> MonthlySummaryResult:
        """月次サマリーを生成する。

        Args:
            weekly_summaries: 月内の週次サマリーリスト。
            month_stats: 月間統計情報 (総コミット数、PR数など)。

        Returns:
            MonthlySummaryResult。

        Raises:
            GeminiRateLimitError: レート制限超過時。
        """
        prompt = self._build_monthly_summary_prompt(weekly_summaries, month_stats)
        raw_response = await self._generate(prompt)
        parsed = self._parse_json_response(raw_response)

        if parsed is None:
            logger.warning(
                "Gemini monthly summary JSON parse failed, "
                "returning fallback result.",
            )
            return MonthlySummaryResult.fallback({})

        return MonthlySummaryResult.fallback(parsed)

    # ------------------------------------------------------------------
    # リポジトリ技術スタック分析
    # ------------------------------------------------------------------

    async def analyze_repo_tech_stack(
        self,
        dependency_files: dict[str, str],
        repo_description: str | None,
        primary_language: str | None,
    ) -> RepoTechStackResult:
        """依存ファイルからリポジトリの技術スタックを分析する。

        Args:
            dependency_files: ファイル名→内容の辞書。
            repo_description: リポジトリの説明文。
            primary_language: 主要プログラミング言語。

        Returns:
            RepoTechStackResult。
        """
        # 各ファイルを5000文字に切り詰め
        truncated: dict[str, str] = {
            k: v[:5000] for k, v in dependency_files.items()
        }

        prompt = self._build_repo_tech_stack_prompt(
            truncated, repo_description, primary_language,
        )
        raw_response = await self._generate(prompt)
        parsed = self._parse_json_response(raw_response)

        if parsed is None:
            logger.warning(
                "Gemini repo tech stack analysis JSON parse failed, "
                "returning fallback result.",
            )
            return RepoTechStackResult.fallback({})

        return RepoTechStackResult.fallback(parsed)

    # ------------------------------------------------------------------
    # Internal: API呼び出し
    # ------------------------------------------------------------------

    async def _generate(self, prompt: str) -> str:
        """Gemini APIにプロンプトを送信しテキストレスポンスを得る。

        レート制限を遵守してからAPIを呼び出す。

        Args:
            prompt: 送信するプロンプト文字列。

        Returns:
            Geminiのテキストレスポンス。

        Raises:
            GeminiRateLimitError: レート制限超過時。
        """
        await self._rate_limiter.acquire_gemini()

        try:
            response = await self._model.generate_content_async(prompt)
            return response.text
        except Exception as exc:
            error_msg = str(exc).lower()
            if "rate" in error_msg or "quota" in error_msg or "429" in error_msg:
                logger.error("Gemini API rate limit exceeded: %s", exc)
                raise GeminiRateLimitError(
                    detail=f"Gemini API rate limit exceeded: {exc}",
                )
            logger.error("Gemini API call failed: %s", exc)
            raise GeminiParseError(
                detail=f"Gemini API call failed: {exc}",
            )

    # ------------------------------------------------------------------
    # Internal: JSONパース
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_response(raw_text: str) -> dict[str, Any] | None:
        """GeminiレスポンスからJSON辞書を抽出する。

        レスポンスがそのままJSONとしてパースできない場合は、
        コードブロック内のJSONを探索する。

        Args:
            raw_text: Geminiの生レスポンステキスト。

        Returns:
            パース済み辞書。パース不能な場合はNone。
        """
        if not raw_text:
            return None

        # 1. そのままパース
        try:
            result = json.loads(raw_text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # 2. ```json ... ``` ブロックからの抽出
        import re
        json_block_pattern = re.compile(
            r"```(?:json)?\s*\n?(.*?)\n?\s*```",
            re.DOTALL,
        )
        match = json_block_pattern.search(raw_text)
        if match:
            try:
                result = json.loads(match.group(1).strip())
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        # 3. 最初の { から最後の } までを抽出
        first_brace = raw_text.find("{")
        last_brace = raw_text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            try:
                result = json.loads(raw_text[first_brace : last_brace + 1])
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        logger.warning("Failed to parse JSON from Gemini response: %s", raw_text[:300])
        return None

    # ------------------------------------------------------------------
    # Internal: プロンプト構築
    # ------------------------------------------------------------------

    @staticmethod
    def _build_diff_analysis_prompt(
        diff: str,
        commit_message: str,
        repo_name: str,
    ) -> str:
        """diff分析用プロンプトを構築する。"""
        return f"""あなたはソフトウェア開発のコード変更を分析する専門家です。
以下のコミット情報を分析し、指定されたJSON形式で結果を出力してください。

## リポジトリ
{repo_name}

## コミットメッセージ
{commit_message}

## Diff
{diff}

## 出力形式 (JSON)
以下のJSON形式で出力してください。他のテキストは含めないでください。

{{
    "summary": "変更内容の要約（日本語、1-2文）",
    "work_category": "feature|bugfix|refactor|test|docs|ci|style|performance|security|dependency のいずれか1つ",
    "technologies_detected": ["検出された技術名・フレームワーク・ライブラリ名の配列"],
    "complexity_score": 1.0,
    "quality_notes": ["コード品質に関する所見の配列"]
}}

注意事項:
- summary は日本語で簡潔に（1-2文）
- work_category は上記の選択肢から最も適切なものを1つ選択
- complexity_score は 1.0（単純）から 10.0（非常に複雑）の範囲
- technologies_detected は具体的な技術名（Python, FastAPI, React, PostgreSQL など）
- quality_notes は改善点や良い点を日本語で記述"""

    @staticmethod
    def _build_weekly_summary_prompt(
        commits_data: list[dict[str, Any]],
        prs_data: list[dict[str, Any]],
        analyses_data: list[dict[str, Any]],
        week_start: str,
        week_end: str,
    ) -> str:
        """週次サマリー用プロンプトを構築する。"""
        # コミット情報を要約形式に変換
        commits_summary = []
        for c in commits_data[:50]:  # 上限50件
            commits_summary.append({
                "message": c.get("message", ""),
                "repo": c.get("repo_name", ""),
                "additions": c.get("additions", 0),
                "deletions": c.get("deletions", 0),
            })

        # PR情報を要約形式に変換
        prs_summary = []
        for pr in prs_data[:30]:  # 上限30件
            prs_summary.append({
                "title": pr.get("title", ""),
                "repo": pr.get("repo_name", ""),
                "state": pr.get("state", ""),
            })

        # 分析結果を要約形式に変換
        analyses_summary = []
        for a in analyses_data[:50]:  # 上限50件
            analyses_summary.append({
                "summary": a.get("summary", ""),
                "work_category": a.get("work_category", ""),
                "technologies": a.get("tech_tags", []),
            })

        return f"""あなたはソフトウェア開発チームの週次レポートを作成する専門家です。
以下の1週間の活動データを分析し、週次サマリーをJSON形式で出力してください。

## 対象期間
{week_start} 〜 {week_end}

## コミット一覧
{json.dumps(commits_summary, ensure_ascii=False, indent=2)}

## プルリクエスト一覧
{json.dumps(prs_summary, ensure_ascii=False, indent=2)}

## Diff分析結果
{json.dumps(analyses_summary, ensure_ascii=False, indent=2)}

## 出力形式 (JSON)
以下のJSON形式で出力してください。他のテキストは含めないでください。

{{
    "highlight": "今週のハイライト（日本語、1-2文で簡潔に）",
    "key_achievements": ["主な成果を3-5項目（日本語）"],
    "technologies_used": ["今週使用した技術名"],
    "suggestions": ["改善提案を1-3項目（日本語）"],
    "focus_areas": ["注力していた領域（日本語）"]
}}"""

    @staticmethod
    def _build_repo_tech_stack_prompt(
        dependency_files: dict[str, str],
        repo_description: str | None,
        primary_language: str | None,
    ) -> str:
        """リポジトリ技術スタック分析用プロンプトを構築する。"""
        files_section = ""
        for fname, content in dependency_files.items():
            files_section += f"\n### {fname}\n```\n{content}\n```\n"

        return f"""あなたはソフトウェアプロジェクトの技術スタックを分析する専門家です。
以下のリポジトリ情報と依存ファイルから、プロジェクトの技術スタックを分析してJSON形式で出力してください。

## リポジトリ情報
- 説明: {repo_description or '(なし)'}
- 主要言語: {primary_language or '(不明)'}

## 依存ファイル
{files_section}

## 出力形式 (JSON)
以下のJSON形式で出力してください。他のテキストは含めないでください。

{{
    "domain": "web_frontend|web_backend|mobile|data_science|machine_learning|devops|cli_tool|library|game|iot|general のいずれか1つ",
    "domain_detail": "ドメインの詳細説明（例: 'SPA with server-side rendering', 'REST API server'）（英語、1文）",
    "frameworks": ["検出されたフレームワーク名の配列（例: Next.js, FastAPI, Django）"],
    "tools": ["検出されたツール・ライブラリ名の配列（例: ESLint, Pytest, Docker）"],
    "infrastructure": ["検出されたインフラ・サービス名の配列（例: PostgreSQL, Redis, AWS S3）"],
    "project_type": "プロジェクトの種類の簡潔な説明（英語、1文）"
}}

注意事項:
- domain は上記の選択肢から最も適切なものを1つ選択
- frameworks にはWebフレームワーク、UIライブラリ等を含める
- tools にはビルドツール、テストツール、リンター、開発ツールを含める
- infrastructure にはDB、キャッシュ、クラウドサービス、CI/CDを含める
- 確信が持てない項目は空配列で返す"""

    @staticmethod
    def _build_monthly_summary_prompt(
        weekly_summaries: list[dict[str, Any]],
        month_stats: dict[str, Any],
    ) -> str:
        """月次サマリー用プロンプトを構築する。"""
        return f"""あなたはソフトウェア開発者の月次振り返りレポートを作成する専門家です。
以下の週次サマリーと月間統計を基に、月次サマリーをJSON形式で出力してください。

## 週次サマリー
{json.dumps(weekly_summaries, ensure_ascii=False, indent=2)}

## 月間統計
{json.dumps(month_stats, ensure_ascii=False, indent=2)}

## 出力形式 (JSON)
以下のJSON形式で出力してください。他のテキストは含めないでください。

{{
    "narrative": "今月の振り返り（日本語、200-400字程度で開発活動を総括）",
    "growth_areas": ["今月の成長領域を3-5項目（日本語）"],
    "monthly_highlights": ["月間ハイライトを3-5項目（日本語）"]
}}"""
