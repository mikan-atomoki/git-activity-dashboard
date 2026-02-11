import Badge from "@/components/ui/Badge";

interface SummaryCardProps {
  title: string;
  period: string;
  content: string;
  tags?: string[];
}

export default function SummaryCard({
  title,
  period,
  content,
  tags,
}: SummaryCardProps) {
  return (
    <div
      className="rounded-xl border p-6"
      style={{
        backgroundColor: "var(--bg-secondary)",
        borderColor: "var(--border)",
      }}
    >
      <div className="mb-4 flex items-center justify-between">
        <h3
          className="text-lg font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          {title}
        </h3>
        <span
          className="text-sm"
          style={{ color: "var(--text-secondary)" }}
        >
          {period}
        </span>
      </div>

      <div
        className="whitespace-pre-wrap text-sm leading-relaxed"
        style={{ color: "var(--text-secondary)" }}
      >
        {content}
      </div>

      {tags && tags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {tags.map((tag) => (
            <Badge key={tag} label={tag} color="var(--accent-blue)" />
          ))}
        </div>
      )}
    </div>
  );
}
