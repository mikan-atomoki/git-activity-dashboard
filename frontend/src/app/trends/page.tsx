"use client";

import { useMemo, useState } from "react";
import Header from "@/components/layout/Header";
import Card from "@/components/ui/Card";
import Skeleton from "@/components/ui/Skeleton";
import DashboardGrid from "@/components/dashboard/DashboardGrid";
import {
  TechTrendChart,
  CategoryPieChart,
  RepoTechStackGrid,
} from "@/components/charts";
import { useTrendsData } from "@/hooks/useTrendsData";

type DateRange = "30d" | "90d" | "6m" | "1y";

const DATE_PRESETS: { value: DateRange; label: string }[] = [
  { value: "30d", label: "30 Days" },
  { value: "90d", label: "90 Days" },
  { value: "6m", label: "6 Months" },
  { value: "1y", label: "1 Year" },
];

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

export default function TrendsPage() {
  const [dateRange, setDateRange] = useState<DateRange>("90d");
  const { techTrends, categories, repoTechStacks, loading } =
    useTrendsData(dateRange);

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
  const effectiveTags =
    selectedTechTags.length > 0
      ? selectedTechTags
      : techTrendTags.map((t) => t.name);

  const handleTagToggle = (tag: string) => {
    setSelectedTechTags((prev) => {
      const allTags = (techTrendTags ?? []).map((t) => t.name);
      if (prev.length === 0) {
        return allTags.filter((t) => t !== tag);
      }
      return prev.includes(tag)
        ? prev.filter((t) => t !== tag)
        : [...prev, tag];
    });
  };

  // Transform category data for pie chart
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

  return (
    <>
      <Header title="Trends">
        <DatePresetSelector value={dateRange} onChange={setDateRange} />
      </Header>

      {loading ? (
        <>
          <DashboardGrid className="mb-6">
            {[...Array(2)].map((_, i) => (
              <Skeleton key={i} className="h-80 rounded-xl" />
            ))}
          </DashboardGrid>
          <Skeleton className="h-64 rounded-xl" />
        </>
      ) : (
        <>
          {/* Charts Row */}
          <DashboardGrid className="mb-6">
            <Card title="Tech Trends">
              {techTrendChartData.length > 0 ? (
                <TechTrendChart
                  data={techTrendChartData}
                  tags={techTrendTags}
                  selectedTags={effectiveTags}
                  onTagToggle={handleTagToggle}
                />
              ) : (
                <EmptyState message="No tech trend data for this period. Sync your repositories and let Gemini analyze your commits." />
              )}
            </Card>
            <Card title="Work Categories">
              {categoryPieData.length > 0 ? (
                <CategoryPieChart data={categoryPieData} />
              ) : (
                <EmptyState message="No category data for this period. Run a sync to analyze your commit history." />
              )}
            </Card>
          </DashboardGrid>

          {/* Repository Tech Stacks */}
          <Card title="Repository Tech Stacks">
            <RepoTechStackGrid items={repoTechStacks} />
          </Card>
        </>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function DatePresetSelector({
  value,
  onChange,
}: {
  value: DateRange;
  onChange: (v: DateRange) => void;
}) {
  return (
    <div className="flex gap-1 rounded-lg border p-1" style={{ borderColor: "var(--border)" }}>
      {DATE_PRESETS.map((preset) => (
        <button
          key={preset.value}
          type="button"
          onClick={() => onChange(preset.value)}
          className="rounded-md px-3 py-1 text-xs font-medium transition-colors"
          style={{
            backgroundColor:
              value === preset.value ? "var(--accent)" : "transparent",
            color:
              value === preset.value
                ? "var(--accent-foreground)"
                : "var(--text-secondary)",
          }}
        >
          {preset.label}
        </button>
      ))}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div
      className="flex h-64 items-center justify-center rounded-lg"
      style={{ backgroundColor: "var(--bg-tertiary)" }}
    >
      <p
        className="max-w-xs text-center text-sm"
        style={{ color: "var(--text-secondary)" }}
      >
        {message}
      </p>
    </div>
  );
}
