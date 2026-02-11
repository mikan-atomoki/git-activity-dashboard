"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getDashboardStats,
  getCommitActivity,
  getLanguageBreakdown,
  getRepoBreakdown,
  getHourlyHeatmap,
  getTechTrends,
  getCategoryBreakdown,
} from "@/lib/api/dashboard";
import type {
  DashboardStatsResponse,
  CommitActivityPoint,
  LanguageRatio,
  RepoRatio,
  HeatmapCellResponse,
  TechTrendItem,
  CategoryItem,
} from "@/types/api";

type Period = "daily" | "weekly" | "monthly";

interface DashboardData {
  stats: DashboardStatsResponse | null;
  commitTimeline: CommitActivityPoint[];
  languages: LanguageRatio[];
  repos: { data: RepoRatio[]; total: number };
  heatmap: HeatmapCellResponse[];
  techTrends: TechTrendItem[];
  categories: CategoryItem[];
  loading: boolean;
  error: string | null;
}

export function useDashboardData(period: Period) {
  const [data, setData] = useState<DashboardData>({
    stats: null,
    commitTimeline: [],
    languages: [],
    repos: { data: [], total: 0 },
    heatmap: [],
    techTrends: [],
    categories: [],
    loading: true,
    error: null,
  });

  const fetchAll = useCallback(async () => {
    setData((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const fallbackStats: DashboardStatsResponse = {
        total_commits: 0,
        active_repos: 0,
        current_streak: 0,
        top_language: null,
        commit_change_pct: null,
      };

      const [stats, commits, langs, repos, heatmap, tech, cats] =
        await Promise.all([
          getDashboardStats().catch(() => fallbackStats),
          getCommitActivity({ period }).catch(() => ({ data: [] as CommitActivityPoint[], total_commits: 0, period })),
          getLanguageBreakdown().catch(() => ({ data: [] as LanguageRatio[] })),
          getRepoBreakdown().catch(() => ({ data: [] as RepoRatio[], total_commits: 0 })),
          getHourlyHeatmap().catch(() => ({ data: [] as HeatmapCellResponse[], max_count: 0 })),
          getTechTrends().catch(() => ({ data: [] as TechTrendItem[] })),
          getCategoryBreakdown().catch(() => ({ data: [] as CategoryItem[] })),
        ]);

      setData({
        stats,
        commitTimeline: commits.data ?? [],
        languages: langs.data ?? [],
        repos: { data: repos.data ?? [], total: repos.total_commits ?? 0 },
        heatmap: heatmap.data ?? [],
        techTrends: tech.data ?? [],
        categories: cats.data ?? [],
        loading: false,
        error: null,
      });
    } catch (err) {
      setData((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to load dashboard data",
      }));
    }
  }, [period]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return { ...data, refresh: fetchAll };
}
