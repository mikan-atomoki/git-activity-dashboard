"use client";

import Badge from "@/components/ui/Badge";
import type { RepoTechStackItem } from "@/types/api";

const DOMAIN_COLORS: Record<string, string> = {
  web_frontend: "#3178c6",
  web_backend: "#3572A5",
  mobile: "#F05138",
  data_science: "#DA5B0B",
  machine_learning: "#ff6f00",
  devops: "#00ADD8",
  cli_tool: "#89e051",
  library: "#A97BFF",
  game: "#db5855",
  iot: "#178600",
  general: "#8b8b8b",
};

const DOMAIN_LABELS: Record<string, string> = {
  web_frontend: "Web Frontend",
  web_backend: "Web Backend",
  mobile: "Mobile",
  data_science: "Data Science",
  machine_learning: "ML / AI",
  devops: "DevOps",
  cli_tool: "CLI Tool",
  library: "Library",
  game: "Game",
  iot: "IoT",
  general: "General",
};

interface RepoTechStackGridProps {
  items: RepoTechStackItem[];
}

export default function RepoTechStackGrid({ items }: RepoTechStackGridProps) {
  if (items.length === 0) {
    return (
      <div
        className="flex h-48 items-center justify-center rounded-lg"
        style={{ backgroundColor: "var(--bg-tertiary)" }}
      >
        <p style={{ color: "var(--text-secondary)" }}>
          No repository data available. Run a sync to analyze your repositories.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <RepoCard key={item.repo_id} item={item} />
      ))}
    </div>
  );
}

function RepoCard({ item }: { item: RepoTechStackItem }) {
  const analysis = item.tech_analysis;
  const domainColor = analysis
    ? DOMAIN_COLORS[analysis.domain] ?? DOMAIN_COLORS.general
    : DOMAIN_COLORS.general;
  const domainLabel = analysis
    ? DOMAIN_LABELS[analysis.domain] ?? analysis.domain
    : "Not Analyzed";

  const repoShortName = item.full_name.includes("/")
    ? item.full_name.split("/")[1]
    : item.full_name;

  return (
    <div
      className="flex flex-col gap-3 rounded-xl border p-4"
      style={{
        backgroundColor: "var(--bg-secondary)",
        borderColor: "var(--border)",
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h4
            className="truncate text-sm font-semibold"
            style={{ color: "var(--text-primary)" }}
            title={item.full_name}
          >
            {repoShortName}
          </h4>
          {item.description && (
            <p
              className="mt-0.5 line-clamp-2 text-xs"
              style={{ color: "var(--text-secondary)" }}
            >
              {item.description}
            </p>
          )}
        </div>
        <Badge label={domainLabel} color={domainColor} />
      </div>

      {/* Language */}
      {item.primary_language && (
        <div className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: domainColor }}
          />
          <span
            className="text-xs"
            style={{ color: "var(--text-secondary)" }}
          >
            {item.primary_language}
          </span>
        </div>
      )}

      {analysis && (
        <>
          {/* Project type */}
          {analysis.project_type && (
            <p
              className="text-xs"
              style={{ color: "var(--text-secondary)" }}
            >
              {analysis.project_type}
            </p>
          )}

          {/* Frameworks */}
          {analysis.frameworks?.length > 0 && (
            <div>
              <p
                className="mb-1 text-xs font-medium"
                style={{ color: "var(--text-secondary)" }}
              >
                Frameworks
              </p>
              <div className="flex flex-wrap gap-1">
                {analysis.frameworks.map((fw) => (
                  <Badge key={fw} label={fw} color="#6366f1" />
                ))}
              </div>
            </div>
          )}

          {/* Tools */}
          {analysis.tools?.length > 0 && (
            <div>
              <p
                className="mb-1 text-xs font-medium"
                style={{ color: "var(--text-secondary)" }}
              >
                Tools
              </p>
              <div className="flex flex-wrap gap-1">
                {analysis.tools.map((tool) => (
                  <Badge key={tool} label={tool} color="#10b981" />
                ))}
              </div>
            </div>
          )}

          {/* Infrastructure */}
          {analysis.infrastructure?.length > 0 && (
            <div>
              <p
                className="mb-1 text-xs font-medium"
                style={{ color: "var(--text-secondary)" }}
              >
                Infrastructure
              </p>
              <div className="flex flex-wrap gap-1">
                {analysis.infrastructure.map((infra) => (
                  <Badge key={infra} label={infra} color="#f59e0b" />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {!analysis && (
        <p
          className="text-xs italic"
          style={{ color: "var(--text-secondary)" }}
        >
          Tech analysis pending. Run sync to analyze.
        </p>
      )}
    </div>
  );
}
