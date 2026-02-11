import { cn } from "@/lib/utils";
import { formatNumber } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number;
    direction: "up" | "down" | "stable";
  };
}

export default function StatCard({ title, value, subtitle, trend }: StatCardProps) {
  const trendColor = (): string => {
    if (!trend) return "";
    switch (trend.direction) {
      case "up":
        return "var(--accent-green)";
      case "down":
        return "var(--accent-red)";
      case "stable":
        return "var(--text-secondary)";
    }
  };

  const trendArrow = (): string => {
    if (!trend) return "";
    switch (trend.direction) {
      case "up":
        return "\u2191";
      case "down":
        return "\u2193";
      case "stable":
        return "\u2192";
    }
  };

  const displayValue = typeof value === "number" ? formatNumber(value) : value;

  return (
    <div
      className="rounded-xl border p-6"
      style={{
        backgroundColor: "var(--bg-secondary)",
        borderColor: "var(--border)",
      }}
    >
      <p
        className="text-sm font-medium"
        style={{ color: "var(--text-secondary)" }}
      >
        {title}
      </p>
      <p
        className="mt-2 text-3xl font-bold"
        style={{ color: "var(--text-primary)" }}
      >
        {displayValue}
      </p>
      <div className="mt-2 flex items-center gap-2">
        {trend && (
          <span
            className="flex items-center gap-1 text-sm font-medium"
            style={{ color: trendColor() }}
          >
            <span>{trendArrow()}</span>
            <span>{trend.value}%</span>
          </span>
        )}
        {subtitle && (
          <span
            className={cn("text-sm", trend && "ml-1")}
            style={{ color: "var(--text-secondary)" }}
          >
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
}
