"use client";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { CHART_COLORS } from "@/constants/chart-colors";

type RepositoryPieChartProps = {
  data: { name: string; commits: number; color: string }[];
  showLabels?: boolean;
};

function aggregateData(
  data: { name: string; commits: number; color: string }[]
) {
  if (data.length <= 5) return data;

  const sorted = [...data].sort((a, b) => b.commits - a.commits);
  const top4 = sorted.slice(0, 4);
  const rest = sorted.slice(4);
  const otherCommits = rest.reduce((sum, d) => sum + d.commits, 0);

  return [
    ...top4,
    { name: "Other", commits: otherCommits, color: CHART_COLORS[4] },
  ];
}

export default function RepositoryPieChart({
  data,
  showLabels = true,
}: RepositoryPieChartProps) {
  const chartData = aggregateData(data);
  const total = chartData.reduce((sum, d) => sum + d.commits, 0);

  return (
    <div className="flex items-center gap-4">
      <div className="relative" style={{ width: 200, height: 200 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius="60%"
              outerRadius="80%"
              dataKey="commits"
              stroke="none"
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={entry.name}
                  fill={entry.color || CHART_COLORS[index % CHART_COLORS.length]}
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        {/* Center label */}
        <div
          className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"
        >
          <span
            className="text-2xl font-bold"
            style={{ color: "var(--text-primary)" }}
          >
            {total}
          </span>
          <span
            className="text-xs"
            style={{ color: "var(--text-secondary)" }}
          >
            commits
          </span>
        </div>
      </div>

      {/* Legend */}
      {showLabels && (
        <ul className="flex flex-1 flex-col gap-2">
          {chartData.map((entry, index) => {
            const pct = total > 0 ? ((entry.commits / total) * 100).toFixed(1) : "0";
            const color =
              entry.color || CHART_COLORS[index % CHART_COLORS.length];
            return (
              <li key={entry.name} className="flex items-center gap-2 text-sm">
                <span
                  className="inline-block h-3 w-3 shrink-0 rounded-sm"
                  style={{ backgroundColor: color }}
                />
                <span
                  className="truncate"
                  style={{ color: "var(--text-primary)" }}
                >
                  {entry.name}
                </span>
                <span
                  className="ml-auto whitespace-nowrap"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {entry.commits} ({pct}%)
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
