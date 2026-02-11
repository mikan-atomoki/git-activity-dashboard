/** Dashboard API functions. */

import { apiFetch } from "./client";
import type {
  CommitActivityResponse,
  LanguageBreakdownResponse,
  RepoBreakdownResponse,
  HourlyHeatmapResponse,
  TechTrendsResponse,
  CategoryBreakdownResponse,
  DashboardStatsResponse,
} from "@/types/api";

export async function getDashboardStats(): Promise<DashboardStatsResponse> {
  return apiFetch<DashboardStatsResponse>("/api/v1/dashboard/stats");
}

export async function getCommitActivity(params?: {
  period?: "daily" | "weekly" | "monthly";
  start_date?: string;
  end_date?: string;
}): Promise<CommitActivityResponse> {
  const query = new URLSearchParams();
  if (params?.period) query.set("period", params.period);
  if (params?.start_date) query.set("start_date", params.start_date);
  if (params?.end_date) query.set("end_date", params.end_date);
  const qs = query.toString();
  return apiFetch<CommitActivityResponse>(
    `/api/v1/dashboard/commit-activity${qs ? `?${qs}` : ""}`,
  );
}

export async function getLanguageBreakdown(): Promise<LanguageBreakdownResponse> {
  return apiFetch<LanguageBreakdownResponse>(
    "/api/v1/dashboard/language-breakdown",
  );
}

export async function getRepoBreakdown(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}): Promise<RepoBreakdownResponse> {
  const query = new URLSearchParams();
  if (params?.start_date) query.set("start_date", params.start_date);
  if (params?.end_date) query.set("end_date", params.end_date);
  if (params?.limit) query.set("limit", String(params.limit));
  const qs = query.toString();
  return apiFetch<RepoBreakdownResponse>(
    `/api/v1/dashboard/repository-breakdown${qs ? `?${qs}` : ""}`,
  );
}

export async function getHourlyHeatmap(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<HourlyHeatmapResponse> {
  const query = new URLSearchParams();
  if (params?.start_date) query.set("start_date", params.start_date);
  if (params?.end_date) query.set("end_date", params.end_date);
  const qs = query.toString();
  return apiFetch<HourlyHeatmapResponse>(
    `/api/v1/dashboard/hourly-heatmap${qs ? `?${qs}` : ""}`,
  );
}

export async function getTechTrends(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<TechTrendsResponse> {
  const query = new URLSearchParams();
  if (params?.start_date) query.set("start_date", params.start_date);
  if (params?.end_date) query.set("end_date", params.end_date);
  const qs = query.toString();
  return apiFetch<TechTrendsResponse>(
    `/api/v1/dashboard/tech-trends${qs ? `?${qs}` : ""}`,
  );
}

export async function getCategoryBreakdown(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<CategoryBreakdownResponse> {
  const query = new URLSearchParams();
  if (params?.start_date) query.set("start_date", params.start_date);
  if (params?.end_date) query.set("end_date", params.end_date);
  const qs = query.toString();
  return apiFetch<CategoryBreakdownResponse>(
    `/api/v1/dashboard/category-breakdown${qs ? `?${qs}` : ""}`,
  );
}
