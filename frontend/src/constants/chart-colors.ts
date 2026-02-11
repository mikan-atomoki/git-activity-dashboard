/** GitHub-inspired 10-color palette for charts */
export const CHART_COLORS = [
  "#58a6ff", // blue
  "#3fb950", // green
  "#d29922", // orange
  "#f85149", // red
  "#bc8cff", // purple
  "#f778ba", // pink
  "#79c0ff", // light blue
  "#56d364", // light green
  "#e3b341", // yellow
  "#ff7b72", // coral
] as const;

/** Language-specific colors matching GitHub's language color scheme */
export const LANGUAGE_COLORS: Record<string, string> = {
  TypeScript: "#3178c6",
  JavaScript: "#f1e05a",
  Python: "#3572A5",
  Java: "#b07219",
  Go: "#00ADD8",
  Rust: "#dea584",
  Ruby: "#701516",
  "C++": "#f34b7d",
  C: "#555555",
  "C#": "#178600",
  PHP: "#4F5D95",
  Swift: "#F05138",
  Kotlin: "#A97BFF",
  Dart: "#00B4AB",
  Shell: "#89e051",
  HTML: "#e34c26",
  CSS: "#563d7c",
  SCSS: "#c6538c",
  Vue: "#41b883",
  Svelte: "#ff3e00",
} as const;

/** Get color for a language, falling back to chart palette */
export function getLanguageColor(language: string, index: number = 0): string {
  return LANGUAGE_COLORS[language] ?? CHART_COLORS[index % CHART_COLORS.length];
}
