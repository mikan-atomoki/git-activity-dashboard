"use client";

import { getLanguageColor } from "@/constants/chart-colors";

type LanguageBreakdownProps = {
  data: { language: string; percentage: number; color: string }[];
};

export default function LanguageBreakdown({ data }: LanguageBreakdownProps) {
  return (
    <div className="flex flex-col gap-3">
      {/* Stacked bar (GitHub-style) */}
      <div className="flex h-3 w-full overflow-hidden rounded-full">
        {data.map((item, idx) => (
          <div
            key={item.language}
            style={{
              width: `${item.percentage}%`,
              backgroundColor:
                item.color || getLanguageColor(item.language, idx),
            }}
          />
        ))}
      </div>

      {/* Language list */}
      <ul className="flex flex-col gap-2">
        {data.map((item, idx) => {
          const color =
            item.color || getLanguageColor(item.language, idx);
          return (
            <li key={item.language} className="flex items-center gap-2 text-sm">
              <span
                className="inline-block h-3 w-3 shrink-0 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span style={{ color: "var(--text-primary)" }}>
                {item.language}
              </span>
              <div
                className="mx-2 flex-1"
                style={{ height: 6, backgroundColor: "var(--bg-tertiary)", borderRadius: 3 }}
              >
                <div
                  style={{
                    width: `${item.percentage}%`,
                    height: "100%",
                    backgroundColor: color,
                    borderRadius: 3,
                  }}
                />
              </div>
              <span
                className="whitespace-nowrap font-medium"
                style={{ color: "var(--text-secondary)" }}
              >
                {item.percentage}%
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
