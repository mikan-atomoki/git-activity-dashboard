/** Backend API response types — mirrors backend Pydantic schemas. */

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface UserResponse {
  user_id: number;
  github_login: string;
  display_name: string | null;
  avatar_url: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: UserResponse;
  access_token: string;
  refresh_token: string;
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export interface CommitActivityPoint {
  date: string;
  count: number;
  additions: number;
  deletions: number;
}

export interface CommitActivityResponse {
  period: string;
  data: CommitActivityPoint[];
  total_commits: number;
}

export interface LanguageRatio {
  language: string;
  percentage: number;
  color: string;
}

export interface LanguageBreakdownResponse {
  data: LanguageRatio[];
}

export interface RepoRatio {
  repo_id: number;
  repo_name: string;
  commit_count: number;
  percentage: number;
  primary_language: string | null;
}

export interface RepoBreakdownResponse {
  data: RepoRatio[];
  total_commits: number;
}

export interface HeatmapCellResponse {
  day_of_week: number;
  hour: number;
  count: number;
}

export interface HourlyHeatmapResponse {
  data: HeatmapCellResponse[];
  max_count: number;
}

export interface TechTrendItem {
  period_start: string;
  tag: string;
  count: number;
}

export interface TechTrendsResponse {
  data: TechTrendItem[];
}

export interface CategoryItem {
  category: string;
  count: number;
  percentage: number;
}

export interface CategoryBreakdownResponse {
  data: CategoryItem[];
}

export interface DashboardStatsResponse {
  total_commits: number;
  active_repos: number;
  current_streak: number;
  top_language: string | null;
  commit_change_pct: number | null;
}

// ---------------------------------------------------------------------------
// Repo Tech Stack
// ---------------------------------------------------------------------------

export interface RepoTechAnalysis {
  domain: string;
  domain_detail: string;
  frameworks: string[];
  tools: string[];
  infrastructure: string[];
  project_type: string;
  analyzed_at: string | null;
}

export interface RepoTechStackItem {
  repo_id: number;
  full_name: string;
  description: string | null;
  primary_language: string | null;
  tech_analysis: RepoTechAnalysis | null;
}

export interface RepoTechStacksResponse {
  data: RepoTechStackItem[];
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

export interface WeeklySummary {
  week_start: string;
  week_end: string;
  total_commits: number;
  total_prs_merged: number;
  highlight: string;
  key_achievements: string[];
  technologies_used: string[];
  generated_at: string | null;
}

export interface WeeklySummaryResponse {
  summaries: WeeklySummary[];
}

export interface MonthlySummary {
  year: number;
  month: number;
  total_commits: number;
  active_repos: string[];
  narrative: string;
  growth_areas: string[];
  generated_at: string | null;
}

export interface MonthlySummaryResponse {
  summaries: MonthlySummary[];
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

export interface SettingsResponse {
  github_token_configured: boolean;
  github_username: string | null;
  sync_interval_hours: number;
  gemini_analysis_enabled: boolean;
  timezone: string;
  tracked_repos_count: number;
}

export interface ValidateGitHubTokenResponse {
  valid: boolean;
  github_login: string | null;
  github_user_id: number | null;
  scopes: string[] | null;
  message: string;
}

// ---------------------------------------------------------------------------
// Repository
// ---------------------------------------------------------------------------

export interface RepositoryWithStats {
  repo_id: number;
  github_repo_id: number;
  full_name: string;
  description: string | null;
  primary_language: string | null;
  is_private: boolean;
  is_active: boolean;
  last_synced_at: string | null;
  repo_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  commit_count: number;
  pr_count: number;
}

export interface PaginationMeta {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

export interface RepositoryListResponse {
  repositories: RepositoryWithStats[];
  pagination: PaginationMeta;
}

export interface DiscoveredRepository {
  github_repo_id: number;
  full_name: string;
  description: string | null;
  primary_language: string | null;
  is_private: boolean;
  is_fork: boolean;
  already_tracked: boolean;
  repo_id: number | null;
  pushed_at: string | null;
  stargazers_count: number;
}

export interface DiscoverResponse {
  repositories: DiscoveredRepository[];
  total: number;
}

// ---------------------------------------------------------------------------
// Sync
// ---------------------------------------------------------------------------

export interface SyncTriggerResponse {
  job_id: number;
  status: string;
  target_repos: number[];
  message: string;
}

export interface SyncStatusResponse {
  job_id: number;
  status: string;
  job_type: string;
  started_at: string | null;
  completed_at: string | null;
  items_fetched: number;
  error_detail: Record<string, unknown> | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Error
// ---------------------------------------------------------------------------

export interface ApiErrorResponse {
  detail: string;
}
