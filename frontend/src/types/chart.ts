export interface CommitTimelineDataPoint {
  date: string;
  commits: number;
  additions: number;
  deletions: number;
}

export interface RepositorySlice {
  name: string;
  value: number;
  color: string;
  percentage: number;
}

export interface HeatmapCell {
  date: string;
  count: number;
  level: 0 | 1 | 2 | 3 | 4;
}

export interface TechTrendDataPoint {
  date: string;
  technologies: Record<string, number>;
}
