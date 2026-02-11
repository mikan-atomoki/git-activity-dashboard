/** Settings API functions. */

import { apiFetch } from "./client";
import type {
  SettingsResponse,
  ValidateGitHubTokenResponse,
} from "@/types/api";

export async function getSettings(): Promise<SettingsResponse> {
  return apiFetch<SettingsResponse>("/api/v1/settings");
}

export async function updateSettings(data: {
  github_token?: string;
  sync_interval_hours?: number;
  gemini_analysis_enabled?: boolean;
  timezone?: string;
}): Promise<SettingsResponse> {
  return apiFetch<SettingsResponse>("/api/v1/settings", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function validateGitHubToken(
  token: string,
): Promise<ValidateGitHubTokenResponse> {
  return apiFetch<ValidateGitHubTokenResponse>(
    "/api/v1/settings/validate-github-token",
    {
      method: "POST",
      body: JSON.stringify({ token }),
    },
  );
}
