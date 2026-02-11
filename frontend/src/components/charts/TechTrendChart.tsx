"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TooltipContentProps } from "recharts";
import { formatDate } from "@/lib/utils";

type TechTrendChartProps = {
  data: { date: string; tags: Record<string, number> }[];
  tags: { name: string; color: string }[];
  selectedTags?: string[];
  onTagToggle?: (tag: string) => void;
};

function CustomTooltip({
  active,
  payload,
  label,
}: TooltipContentProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;

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
      {payload.map((entry) => (
        <p key={entry.dataKey} className="flex items-center gap-1.5">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span>{entry.dataKey}:</span>
          <span className="font-medium">{entry.value}</span>
        </p>
      ))}
    </div>
  );
}

export default function TechTrendChart({
  data,
  tags,
  selectedTags,
  onTagToggle,
}: TechTrendChartProps) {
  const visibleTags = selectedTags ?? tags.map((t) => t.name);

  // Flatten data for Recharts
  const chartData = data.map((d) => ({
    label: formatDate(d.date, "yyyy/M"),
    ...d.tags,
  }));

  return (
    <div>
      {/* Custom clickable tag legend */}
      <div className="mb-3 flex flex-wrap gap-2">
        {tags.map((tag) => {
          const isActive = visibleTags.includes(tag.name);
          return (
            <button
              key={tag.name}
              type="button"
              onClick={() => onTagToggle?.(tag.name)}
              className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-opacity"
              style={{
                borderColor: tag.color,
                backgroundColor: isActive ? `${tag.color}20` : "transparent",
                color: isActive
                  ? "var(--text-primary)"
                  : "var(--text-secondary)",
                opacity: isActive ? 1 : 0.5,
                cursor: onTagToggle ? "pointer" : "default",
              }}
            >
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ backgroundColor: tag.color }}
              />
              {tag.name}
            </button>
          );
        })}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={chartData}
          margin={{ top: 8, right: 8, left: -16, bottom: 0 }}
        >
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
          {tags.map((tag) => (
            <Line
              key={tag.name}
              type="monotone"
              dataKey={tag.name}
              stroke={tag.color}
              strokeWidth={2}
              dot={{ r: 3, fill: tag.color }}
              activeDot={{ r: 5 }}
              hide={!visibleTags.includes(tag.name)}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
