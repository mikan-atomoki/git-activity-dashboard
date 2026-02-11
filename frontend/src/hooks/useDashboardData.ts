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
      const [stats, commits, langs, repos, heatmap, tech, cats] =
        await Promise.all([
          getDashboardStats().catch(() => null),
          getCommitActivity({ period }).catch(() => ({ data: [], total_commits: 0, period })),
          getLanguageBreakdown().catch(() => ({ data: [] })),
          getRepoBreakdown().catch(() => ({ data: [], total_commits: 0 })),
          getHourlyHeatmap().catch(() => ({ data: [], max_count: 0 })),
          getTechTrends().catch(() => ({ data: [] })),
          getCategoryBreakdown().catch(() => ({ data: [] })),
        ]);

      setData({
        stats,
        commitTimeline: commits.data,
        languages: langs.data,
        repos: { data: repos.data, total: repos.total_commits },
        heatmap: heatmap.data,
        techTrends: tech.data,
        categories: cats.data,
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
