/** Sync API functions. */

import { apiFetch } from "./client";
import type { SyncTriggerResponse, SyncStatusResponse } from "@/types/api";

export async function triggerSync(params?: {
  repo_ids?: number[];
  full_sync?: boolean;
}): Promise<SyncTriggerResponse> {
  return apiFetch<SyncTriggerResponse>("/api/v1/sync/trigger", {
    method: "POST",
    body: JSON.stringify(params ?? {}),
  });
}

export async function getSyncStatus(
  jobId: number,
): Promise<SyncStatusResponse> {
  return apiFetch<SyncStatusResponse>(`/api/v1/sync/status/${jobId}`);
}
