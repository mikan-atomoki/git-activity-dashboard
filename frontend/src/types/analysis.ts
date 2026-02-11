export interface TechTrendData {
  technology: string;
  category: "language" | "framework" | "tool" | "library";
  usageCount: number;
  trend: "rising" | "stable" | "declining";
  firstSeen: string;
  lastSeen: string;
}

export interface WorkCategoryData {
  category: string;
  commitCount: number;
  percentage: number;
  description: string;
}

export interface WeeklySummaryData {
  weekStart: string;
  weekEnd: string;
  totalCommits: number;
  totalPRs: number;
  activeRepos: string[];
  summary: string;
  highlights: string[];
  tags: string[];
}

export interface MonthlySummaryData {
  month: string;
  year: number;
  totalCommits: number;
  totalPRs: number;
  activeRepos: string[];
  topLanguages: { name: string; percentage: number }[];
  summary: string;
  achievements: string[];
  goals: string[];
  tags: string[];
}
