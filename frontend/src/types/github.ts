export interface CommitData {
  sha: string;
  message: string;
  author: string;
  date: string;
  repository: string;
  additions: number;
  deletions: number;
  filesChanged: number;
}

export interface RepositoryData {
  name: string;
  fullName: string;
  description: string | null;
  language: string | null;
  stars: number;
  forks: number;
  openIssues: number;
  lastUpdated: string;
  commitCount: number;
  isPrivate: boolean;
}

export interface LanguageData {
  name: string;
  bytes: number;
  percentage: number;
  color: string;
}

export interface PullRequestData {
  id: number;
  title: string;
  state: "open" | "closed" | "merged";
  author: string;
  repository: string;
  createdAt: string;
  mergedAt: string | null;
  closedAt: string | null;
  additions: number;
  deletions: number;
  reviewCount: number;
}
