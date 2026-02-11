"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TooltipContentProps } from "recharts";
import { formatDate } from "@/lib/utils";

type CommitTimelineProps = {
  data: { date: string; count: number; additions: number; deletions: number }[];
  granularity: "daily" | "weekly" | "monthly";
  height?: number;
};

const GRANULARITY_FORMAT: Record<string, string> = {
  daily: "M/d",
  weekly: "M/d",
  monthly: "yyyy/M",
};

function CustomTooltip({
  active,
  payload,
  label,
}: TooltipContentProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;

  const data = payload[0]?.payload as {
    date: string;
    count: number;
    additions: number;
    deletions: number;
  };

  return (
    <div
      className="rounded-lg border px-3 py-2 text-sm shadow-lg"
      style={{
        backgroundColor: "var(--bg-secondary)",
        borderColor: "var(--border)",
        color: "var(--text-primary)",
      }}
    >
      <p className="mb-1 font-medium">{label}</p>
      <p>
        <span style={{ color: "var(--accent-blue)" }}>Commits: </span>
        {data.count}
      </p>
      <p>
        <span style={{ color: "var(--accent-green)" }}>+{data.additions}</span>
        {" / "}
        <span style={{ color: "var(--accent-red)" }}>-{data.deletions}</span>
      </p>
    </div>
  );
}

export default function CommitTimeline({
  data,
  granularity,
  height = 300,
}: CommitTimelineProps) {
  const fmt = GRANULARITY_FORMAT[granularity];

  const chartData = data.map((d) => ({
    ...d,
    label:
      formatDate(d.date, fmt) + (granularity === "weekly" ? "週" : ""),
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart
        data={chartData}
        margin={{ top: 8, right: 8, left: -16, bottom: 0 }}
      >
        <defs>
          <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
            <stop
              offset="5%"
              stopColor="var(--accent-blue)"
              stopOpacity={0.3}
            />
            <stop
              offset="95%"
              stopColor="var(--accent-blue)"
              stopOpacity={0}
            />
          </linearGradient>
        </defs>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="var(--border)"
          strokeOpacity={0.5}
        />
        <XAxis
          dataKey="label"
          tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
          axisLine={{ stroke: "var(--border)" }}
          tickLine={{ stroke: "var(--border)" }}
        />
        <YAxis
          tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
          axisLine={{ stroke: "var(--border)" }}
          tickLine={{ stroke: "var(--border)" }}
          allowDecimals={false}
        />
        <Tooltip content={CustomTooltip} />
        <Area
          type="monotone"
          dataKey="count"
          stroke="var(--accent-blue)"
          strokeWidth={2}
          fill="url(#colorCount)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
