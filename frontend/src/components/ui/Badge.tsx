import { cn } from "@/lib/utils";

interface BadgeProps {
  label: string;
  color?: string;
}

export default function Badge({ label, color }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
      )}
      style={{
        backgroundColor: color
          ? `${color}20`
          : "var(--bg-tertiary)",
        color: color ?? "var(--text-secondary)",
        border: `1px solid ${color ? `${color}40` : "var(--border)"}`,
      }}
    >
      {label}
    </span>
  );
}
