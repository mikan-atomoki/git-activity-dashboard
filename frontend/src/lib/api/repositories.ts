/** Repository API functions. */

import { apiFetch } from "./client";
import type {
  RepositoryListResponse,
  DiscoverResponse,
} from "@/types/api";

export async function getRepositories(params?: {
  page?: number;
  per_page?: number;
  active_only?: boolean;
}): Promise<RepositoryListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.per_page) query.set("per_page", String(params.per_page));
  if (params?.active_only !== undefined)
    query.set("active_only", String(params.active_only));
  const qs = query.toString();
  return apiFetch<RepositoryListResponse>(
    `/api/v1/repositories${qs ? `?${qs}` : ""}`,
  );
}

export async function discoverRepositories(params?: {
  include_private?: boolean;
  include_forks?: boolean;
}): Promise<DiscoverResponse> {
  return apiFetch<DiscoverResponse>("/api/v1/repositories/discover", {
    method: "POST",
    body: JSON.stringify(params ?? {}),
  });
}

export async function updateRepository(
  repoId: number,
  data: { is_active: boolean },
): Promise<unknown> {
  return apiFetch(`/api/v1/repositories/${repoId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
