"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api/client";
import type { WeeklySummary, WeeklySummaryResponse } from "@/types/api";

export function useWeeklySummary() {
  const [summary, setSummary] = useState<WeeklySummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<WeeklySummaryResponse>("/api/v1/summaries/weekly?count=1")
      .then((res) => {
        if (res.summaries.length > 0) {
          setSummary(res.summaries[0]);
        }
      })
      .catch(() => {
        // No summary available yet — not an error
      })
      .finally(() => setLoading(false));
  }, []);

  return { summary, loading };
}
