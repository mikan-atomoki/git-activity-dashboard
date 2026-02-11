"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getTechTrends,
  getCategoryBreakdown,
  getRepoTechStacks,
} from "@/lib/api/dashboard";
import type {
  TechTrendItem,
  CategoryItem,
  RepoTechStackItem,
} from "@/types/api";

type DateRange = "30d" | "90d" | "6m" | "1y";

function dateRangeToStartDate(range: DateRange): string {
  const now = new Date();
  switch (range) {
    case "30d":
      now.setDate(now.getDate() - 30);
      break;
    case "90d":
      now.setDate(now.getDate() - 90);
      break;
    case "6m":
      now.setMonth(now.getMonth() - 6);
      break;
    case "1y":
      now.setFullYear(now.getFullYear() - 1);
      break;
  }
  return now.toISOString().slice(0, 10);
}

interface TrendsData {
  techTrends: TechTrendItem[];
  categories: CategoryItem[];
  repoTechStacks: RepoTechStackItem[];
  loading: boolean;
  error: string | null;
}

export function useTrendsData(dateRange: DateRange) {
  const [data, setData] = useState<TrendsData>({
    techTrends: [],
    categories: [],
    repoTechStacks: [],
    loading: true,
    error: null,
  });

  const fetchAll = useCallback(async () => {
    setData((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const startDate = dateRangeToStartDate(dateRange);
      const params = { start_date: startDate };

      const [tech, cats, stacks] = await Promise.all([
        getTechTrends(params).catch(() => ({ data: [] as TechTrendItem[] })),
        getCategoryBreakdown(params).catch(() => ({ data: [] as CategoryItem[] })),
        getRepoTechStacks().catch(() => ({ data: [] as RepoTechStackItem[] })),
      ]);

      setData({
        techTrends: tech.data,
        categories: cats.data,
        repoTechStacks: stacks.data,
        loading: false,
        error: null,
      });
    } catch (err) {
      setData((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : "Failed to load trends data",
      }));
    }
  }, [dateRange]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return { ...data, refresh: fetchAll };
}
