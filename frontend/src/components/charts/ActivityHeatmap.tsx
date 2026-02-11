"use client";

import { useState, useRef, useCallback, useMemo } from "react";

type ActivityHeatmapProps = {
  data: { dayOfWeek: number; hour: number; count: number }[];
  colorScale?: { min: string; max: string };
};

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DAY_LABELS_JP = ["月曜", "火曜", "水曜", "木曜", "金曜", "土曜", "日曜"];
const HOUR_LABELS = [0, 3, 6, 9, 12, 15, 18, 21];
const COLOR_LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"];

function getColor(count: number, maxCount: number): string {
  if (count === 0) return COLOR_LEVELS[0];
  if (maxCount === 0) return COLOR_LEVELS[0];
  const ratio = count / maxCount;
  if (ratio <= 0.25) return COLOR_LEVELS[1];
  if (ratio <= 0.5) return COLOR_LEVELS[2];
  if (ratio <= 0.75) return COLOR_LEVELS[3];
  return COLOR_LEVELS[4];
}

type TooltipInfo = {
  x: number;
  y: number;
  dayOfWeek: number;
  hour: number;
  count: number;
};

export default function ActivityHeatmap({ data }: ActivityHeatmapProps) {
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const dataMap = useMemo(() => {
    const map = new Map<string, number>();
    let max = 0;
    for (const d of data) {
      const key = `${d.dayOfWeek}-${d.hour}`;
      map.set(key, d.count);
      if (d.count > max) max = d.count;
    }
    return { map, max };
  }, [data]);

  const handleMouseEnter = useCallback(
    (
      e: React.MouseEvent<SVGRectElement>,
      dayOfWeek: number,
      hour: number,
      count: number
    ) => {
      const containerRect = containerRef.current?.getBoundingClientRect();
      const rect = (e.target as SVGRectElement).getBoundingClientRect();
      if (!containerRect) return;
      setTooltip({
        x: rect.left - containerRect.left + rect.width / 2,
        y: rect.top - containerRect.top - 8,
        dayOfWeek,
        hour,
        count,
      });
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  const labelWidth = 36;
  const gap = 2;
  const headerHeight = 20;
  const cellSize = 18;
  const svgWidth = labelWidth + 24 * (cellSize + gap);
  const svgHeight = headerHeight + 7 * (cellSize + gap);

  return (
    <div ref={containerRef} className="relative w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        width="100%"
        style={{ maxWidth: svgWidth }}
      >
        {/* Hour labels */}
        {HOUR_LABELS.map((h) => (
          <text
            key={`h-${h}`}
            x={labelWidth + h * (cellSize + gap) + cellSize / 2}
            y={14}
            textAnchor="middle"
            fill="var(--text-secondary)"
            fontSize={10}
          >
            {h}
          </text>
        ))}

        {/* Day labels + cells */}
        {DAY_LABELS.map((day, dayIdx) => (
          <g key={day}>
            <text
              x={0}
              y={headerHeight + dayIdx * (cellSize + gap) + cellSize / 2 + 4}
              fill="var(--text-secondary)"
              fontSize={10}
            >
              {day}
            </text>
            {Array.from({ length: 24 }, (_, hourIdx) => {
              const count =
                dataMap.map.get(`${dayIdx}-${hourIdx}`) ?? 0;
              return (
                <rect
                  key={`${dayIdx}-${hourIdx}`}
                  x={labelWidth + hourIdx * (cellSize + gap)}
                  y={headerHeight + dayIdx * (cellSize + gap)}
                  width={cellSize}
                  height={cellSize}
                  rx={3}
                  fill={getColor(count, dataMap.max)}
                  style={{ cursor: "pointer" }}
                  onMouseEnter={(e) =>
                    handleMouseEnter(e, dayIdx, hourIdx, count)
                  }
                  onMouseLeave={handleMouseLeave}
                />
              );
            })}
          </g>
        ))}
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded-lg border px-3 py-1.5 text-xs shadow-lg whitespace-nowrap"
          style={{
            left: tooltip.x,
            top: tooltip.y,
            transform: "translate(-50%, -100%)",
            backgroundColor: "var(--bg-secondary)",
            borderColor: "var(--border)",
            color: "var(--text-primary)",
          }}
        >
          {DAY_LABELS_JP[tooltip.dayOfWeek]} {tooltip.hour}:00 -{" "}
          {tooltip.count} commits
        </div>
      )}
    </div>
  );
}
