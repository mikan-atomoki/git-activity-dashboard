"use client";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

type CategoryPieChartProps = {
  data: {
    category: string;
    label: string;
    count: number;
    percentage: number;
    color: string;
  }[];
};

export default function CategoryPieChart({ data }: CategoryPieChartProps) {
  const total = data.reduce((sum, d) => sum + d.count, 0);

  return (
    <div className="flex items-center gap-4">
      <div className="relative" style={{ width: 200, height: 200 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius="60%"
              outerRadius="80%"
              dataKey="count"
              stroke="none"
            >
              {data.map((entry) => (
                <Cell key={entry.category} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
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
            total
          </span>
        </div>
      </div>

      {/* Legend */}
      <ul className="flex flex-1 flex-col gap-2">
        {data.map((entry) => (
          <li
            key={entry.category}
            className="flex items-center gap-2 text-sm"
          >
            <span
              className="inline-block h-3 w-3 shrink-0 rounded-sm"
              style={{ backgroundColor: entry.color }}
            />
            <span style={{ color: "var(--text-primary)" }}>{entry.label}</span>
            <span
              className="ml-auto whitespace-nowrap"
              style={{ color: "var(--text-secondary)" }}
            >
              {entry.count} ({entry.percentage}%)
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
