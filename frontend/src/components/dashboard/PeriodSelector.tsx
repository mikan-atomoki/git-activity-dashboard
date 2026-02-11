"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";

type Period = "daily" | "weekly" | "monthly";

interface PeriodSelectorProps {
  value: Period;
  onChange: (period: Period) => void;
}

const periods: { label: string; value: Period }[] = [
  { label: "Daily", value: "daily" },
  { label: "Weekly", value: "weekly" },
  { label: "Monthly", value: "monthly" },
];

export default function PeriodSelector({ value, onChange }: PeriodSelectorProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleChange = (period: Period) => {
    onChange(period);
    const params = new URLSearchParams(searchParams.toString());
    params.set("period", period);
    router.push(`?${params.toString()}`);
  };

  return (
    <div
      className="inline-flex rounded-lg border p-1"
      style={{
        backgroundColor: "var(--bg-tertiary)",
        borderColor: "var(--border)",
      }}
    >
      {periods.map((period) => {
        const isActive = value === period.value;
        return (
          <button
            key={period.value}
            onClick={() => handleChange(period.value)}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
            )}
            style={{
              backgroundColor: isActive ? "var(--accent-blue)" : "transparent",
              color: isActive ? "#ffffff" : "var(--text-secondary)",
            }}
          >
            {period.label}
          </button>
        );
      })}
    </div>
  );
}
