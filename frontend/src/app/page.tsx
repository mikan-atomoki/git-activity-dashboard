"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Header from "@/components/layout/Header";
import PeriodSelector from "@/components/dashboard/PeriodSelector";
import StatCard from "@/components/dashboard/StatCard";
import SummaryCard from "@/components/dashboard/SummaryCard";
import DashboardGrid from "@/components/dashboard/DashboardGrid";
import Card from "@/components/ui/Card";
import Skeleton from "@/components/ui/Skeleton";
import {
  CommitTimeline,
  RepositoryPieChart,
  LanguageBreakdown,
  ActivityHeatmap,
  TechTrendChart,
  CategoryPieChart,
} from "@/components/charts";
import { CHART_COLORS, getLanguageColor } from "@/constants/chart-colors";
import { useDashboardData } from "@/hooks/useDashboardData";
import { useWeeklySummary } from "@/hooks/useWeeklySummary";

type Period = "daily" | "weekly" | "monthly";

// Category display config
const CATEGORY_COLORS: Record<string, string> = {
  feature: "#3fb950",
  bugfix: "#f85149",
  refactor: "#58a6ff",
  docs: "#d29922",
  test: "#a371f7",
  ci: "#f778ba",
  style: "#79c0ff",
  performance: "#ffa657",
  security: "#ff7b72",
  dependency: "#8b949e",
  other: "#8b949e",
};

function DashboardContent() {
  const searchParams = useSearchParams();
  const initialPeriod = (searchParams.get("period") as Period) ?? "weekly";
  const [period, setPeriod] = useState<Period>(initialPeriod);

  const { stats, commitTimeline, languages, repos, heatmap, techTrends, categories, loading } =
    useDashboardData(period);
  const { summary } = useWeeklySummary();

  // Transform repo data for pie chart
  const repoPieData = useMemo(
    () =>
      repos.data.map((r, i) => ({
        name: r.repo_name,
        commits: r.commit_count,
        color: CHART_COLORS[i % CHART_COLORS.length],
      })),
    [repos.data],
  );

  // Transform language data
  const langData = useMemo(
    () =>
      languages.map((l) => ({
        language: l.language,
        percentage: l.percentage,
        color: l.color || getLanguageColor(l.language),
      })),
    [languages],
  );

  // Transform heatmap data
  const heatmapData = useMemo(
    () =>
      heatmap.map((h) => ({
        dayOfWeek: h.day_of_week,
        hour: h.hour,
        count: h.count,
      })),
    [heatmap],
  );

  // Transform tech trend data into chart format
  const { techTrendChartData, techTrendTags } = useMemo(() => {
    const tagSet = new Set<string>();
    const dateMap = new Map<string, Record<string, number>>();

    for (const item of techTrends) {
      tagSet.add(item.tag);
      const dateKey = item.period_start;
      if (!dateMap.has(dateKey)) dateMap.set(dateKey, {});
      dateMap.get(dateKey)![item.tag] = item.count;
    }

    const tags = Array.from(tagSet);
    const TAG_COLORS = [
      "#61dafb", "#3178c6", "#336791", "#2496ed", "#3fb950",
      "#f85149", "#d29922", "#a371f7", "#ffa657", "#79c0ff",
    ];

    return {
      techTrendChartData: Array.from(dateMap.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([date, tagCounts]) => ({ date, tags: tagCounts })),
      techTrendTags: tags.map((name, i) => ({
        name,
        color: TAG_COLORS[i % TAG_COLORS.length],
      })),
    };
  }, [techTrends]);

  const [selectedTechTags, setSelectedTechTags] = useState<string[]>([]);
  // Sync selectedTechTags when tags change
  const effectiveTags =
    selectedTechTags.length > 0
      ? selectedTechTags
      : techTrendTags.map((t) => t.name);

  const handleTagToggle = (tag: string) => {
    setSelectedTechTags((prev) => {
      const allTags = techTrendTags.map((t) => t.name);
      if (prev.length === 0) {
        // First toggle: show all except this one
        return allTags.filter((t) => t !== tag);
      }
      return prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag];
    });
  };

  // Transform category data
  const categoryPieData = useMemo(
    () =>
      categories.map((c) => ({
        category: c.category,
        label: c.category.charAt(0).toUpperCase() + c.category.slice(1),
        count: c.count,
        percentage: c.percentage,
        color: CATEGORY_COLORS[c.category] || CATEGORY_COLORS.other,
      })),
    [categories],
  );

  // Commit timeline data for chart
  const timelineData = useMemo(
    () =>
      commitTimeline.map((p) => ({
        date: p.date,
        count: p.count,
        additions: p.additions,
        deletions: p.deletions,
      })),
    [commitTimeline],
  );

  const hasData = stats && stats.total_commits > 0;

  if (loading) {
    return (
      <>
        <Header title="Dashboard">
          <PeriodSelector value={period} onChange={setPeriod} />
        </Header>
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <DashboardGrid className="mb-6">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-72 rounded-xl" />
          ))}
        </DashboardGrid>
      </>
    );
  }

  return (
    <>
      <Header title="Dashboard">
        <PeriodSelector value={period} onChange={setPeriod} />
      </Header>

      {/* Stat Cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Commits"
          value={stats?.total_commits ?? 0}
          trend={
            stats?.commit_change_pct != null
              ? {
                  value: Math.abs(Math.round(stats.commit_change_pct)),
                  direction: stats.commit_change_pct > 0 ? "up" : stats.commit_change_pct < 0 ? "down" : "stable",
                }
              : undefined
          }
          subtitle="vs last period"
        />
        <StatCard
          title="Active Repos"
          value={stats?.active_repos ?? 0}
          subtitle="repositories"
        />
        <StatCard
          title="Streak"
          value={`${stats?.current_streak ?? 0} days`}
          subtitle="current streak"
        />
        <StatCard
          title="Top Language"
          value={stats?.top_language ?? "-"}
          subtitle="most used"
        />
      </div>

      {!hasData ? (
        <div
          className="flex flex-col items-center justify-center rounded-xl border py-16"
          style={{ backgroundColor: "var(--bg-secondary)", borderColor: "var(--border)" }}
        >
          <p className="mb-2 text-lg font-medium" style={{ color: "var(--text-primary)" }}>
            No data yet
          </p>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            Go to Settings to connect your GitHub token and trigger a sync.
          </p>
        </div>
      ) : (
        <>
          {/* Charts Area */}
          <DashboardGrid className="mb-6">
            <Card title="Commit Timeline">
              <CommitTimeline data={timelineData} granularity={period} />
            </Card>
            <Card title="Repository Breakdown">
              <RepositoryPieChart data={repoPieData} />
            </Card>
            <Card title="Activity Heatmap">
              <ActivityHeatmap data={heatmapData} />
            </Card>
            <Card title="Language Distribution">
              <LanguageBreakdown data={langData} />
            </Card>
          </DashboardGrid>

          <DashboardGrid className="mb-6">
            {techTrendChartData.length > 0 && (
              <Card title="Tech Trends">
                <TechTrendChart
                  data={techTrendChartData}
                  tags={techTrendTags}
                  selectedTags={effectiveTags}
                  onTagToggle={handleTagToggle}
                />
              </Card>
            )}
            {categoryPieData.length > 0 && (
              <Card title="Work Categories">
                <CategoryPieChart data={categoryPieData} />
              </Card>
            )}
          </DashboardGrid>

          {/* Weekly Summary */}
          {summary && (
            <SummaryCard
              title="AI Weekly Summary"
              period={`${summary.week_start} ~ ${summary.week_end}`}
              content={summary.highlight}
              tags={summary.technologies_used}
            />
          )}
        </>
      )}
    </>
  );
}

export default function DashboardPage() {
  return (
    <Suspense>
      <DashboardContent />
    </Suspense>
  );
}
