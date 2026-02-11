"use client";

import { useCallback, useEffect, useState } from "react";
import Header from "@/components/layout/Header";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import {
  getSettings,
  updateSettings,
} from "@/lib/api/settings";
import { getRepositories } from "@/lib/api/repositories";
import { triggerSync, getSyncStatus } from "@/lib/api/sync";
import type {
  SettingsResponse,
  RepositoryWithStats,
  SyncStatusResponse,
} from "@/types/api";

export default function SettingsPage() {
  const [token, setToken] = useState("");
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [repos, setRepos] = useState<RepositoryWithStats[]>([]);
  const [loadingSettings, setLoadingSettings] = useState(true);
  const [savingToken, setSavingToken] = useState(false);
  const [tokenMessage, setTokenMessage] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<string>("");

  // Load settings + repos on mount
  useEffect(() => {
    Promise.all([
      getSettings().catch(() => null),
      getRepositories({ per_page: 100 }).catch(() => null),
    ]).then(([s, r]) => {
      if (s) setSettings(s);
      if (r) setRepos(r.repositories);
      setLoadingSettings(false);
    });
  }, []);

  // Save GitHub token
  const handleSaveToken = async () => {
    if (!token.trim()) return;
    setSavingToken(true);
    setTokenMessage("");
    try {
      // Save token (backend validates + auto-registers all repos)
      const updated = await updateSettings({ github_token: token });
      setSettings(updated);
      setToken("");
      setTokenMessage(
        `Token saved. ${updated.tracked_repos_count} repositories auto-registered.`,
      );
      refreshRepos();
    } catch (err) {
      setTokenMessage(err instanceof Error ? err.message : "Failed to save token");
    } finally {
      setSavingToken(false);
    }
  };

  // Refresh repos list
  const refreshRepos = async () => {
    const r = await getRepositories({ per_page: 100 }).catch(() => null);
    if (r) setRepos(r.repositories);
  };

  // Poll sync status
  const pollSyncStatus = useCallback(async (jobId: number) => {
    const poll = async () => {
      try {
        const status: SyncStatusResponse = await getSyncStatus(jobId);
        setSyncStatus(`${status.status} (${status.items_fetched} items)`);
        if (status.status === "completed" || status.status === "failed") {
          setSyncing(false);
          getSettings().then(setSettings).catch(() => {});
          refreshRepos();
          return;
        }
        setTimeout(poll, 3000);
      } catch {
        setSyncing(false);
      }
    };
    poll();
  }, []);

  // Trigger sync
  const handleSync = async () => {
    setSyncing(true);
    setSyncStatus("Starting...");
    try {
      const result = await triggerSync();
      setSyncStatus(`Job #${result.job_id}: ${result.status}`);
      pollSyncStatus(result.job_id);
    } catch (err) {
      setSyncing(false);
      setSyncStatus(err instanceof Error ? err.message : "Sync failed");
    }
  };

  if (loadingSettings) {
    return (
      <>
        <Header title="Settings" />
        <div className="flex items-center justify-center py-16">
          <div
            className="h-8 w-8 animate-spin rounded-full border-2 border-t-transparent"
            style={{ borderColor: "var(--accent-blue)", borderTopColor: "transparent" }}
          />
        </div>
      </>
    );
  }

  return (
    <>
      <Header title="Settings" />

      <div className="space-y-6">
        {/* GitHub Token Section */}
        <Card title="GitHub Token">
          <div className="space-y-4">
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              {settings?.github_token_configured
                ? `GitHub token is configured (${settings.github_username ?? "connected"}).`
                : "Enter your GitHub Personal Access Token to fetch your activity data."}
            </p>
            <div className="flex gap-3">
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder={
                  settings?.github_token_configured
                    ? "Enter new token to update"
                    : "ghp_xxxxxxxxxxxxxxxxxxxx"
                }
                className="flex-1 rounded-lg border px-4 py-2 text-sm focus:outline-none focus:ring-2"
                style={{
                  backgroundColor: "var(--bg-tertiary)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
              />
              <Button
                variant="primary"
                onClick={handleSaveToken}
                disabled={savingToken || !token.trim()}
              >
                {savingToken ? "Saving..." : "Save"}
              </Button>
            </div>
            {tokenMessage && (
              <p
                className="text-sm"
                style={{
                  color: tokenMessage.includes("saved") || tokenMessage.includes("success")
                    ? "var(--accent-green)"
                    : "var(--accent-red)",
                }}
              >
                {tokenMessage}
              </p>
            )}
            <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
              Required scopes: repo, read:user. Token is encrypted and stored securely.
            </p>
          </div>
        </Card>

        {/* Tracked Repositories */}
        <Card title="Tracked Repositories">
          <div className="space-y-4">
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              {repos.length > 0
                ? `${repos.length} repositories are being tracked. New repos are auto-detected on each sync.`
                : settings?.github_token_configured
                  ? "Repositories will be auto-registered when you save your token or run a sync."
                  : "Connect your GitHub token to start tracking repositories."}
            </p>

            {repos.length > 0 && (
              <div className="max-h-80 space-y-2 overflow-y-auto">
                {repos.map((repo) => (
                  <div
                    key={repo.repo_id}
                    className="flex items-center justify-between rounded-lg border px-4 py-3"
                    style={{
                      backgroundColor: "var(--bg-tertiary)",
                      borderColor: "var(--border)",
                    }}
                  >
                    <div>
                      <p
                        className="text-sm font-medium"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {repo.full_name}
                        {repo.is_private && (
                          <span
                            className="ml-2 text-xs"
                            style={{ color: "var(--text-secondary)" }}
                          >
                            (private)
                          </span>
                        )}
                      </p>
                      <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
                        {repo.primary_language ?? "—"}
                        {repo.commit_count > 0 && ` · ${repo.commit_count} commits`}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        {/* Data Management Section */}
        <Card title="Data Management">
          <div className="space-y-4">
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Sync your GitHub data. This will fetch commits, PRs, and run Gemini analysis.
            </p>
            <div className="flex items-center gap-4">
              <Button
                variant="primary"
                onClick={handleSync}
                disabled={syncing || !settings?.github_token_configured}
              >
                {syncing ? "Syncing..." : "Sync Now"}
              </Button>
            </div>
            {syncStatus && (
              <p className="text-sm" style={{ color: "var(--accent-blue)" }}>
                {syncStatus}
              </p>
            )}
            <div
              className="rounded-lg border p-4"
              style={{
                backgroundColor: "var(--bg-tertiary)",
                borderColor: "var(--border)",
              }}
            >
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span style={{ color: "var(--text-secondary)" }}>
                    Sync interval
                  </span>
                  <span style={{ color: "var(--text-primary)" }}>
                    Every {settings?.sync_interval_hours ?? 6} hours
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: "var(--text-secondary)" }}>
                    Gemini analysis
                  </span>
                  <span style={{ color: "var(--text-primary)" }}>
                    {settings?.gemini_analysis_enabled ? "Enabled" : "Disabled"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: "var(--text-secondary)" }}>
                    Timezone
                  </span>
                  <span style={{ color: "var(--text-primary)" }}>
                    {settings?.timezone ?? "Asia/Tokyo"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}
