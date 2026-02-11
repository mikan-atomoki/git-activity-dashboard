interface HeaderProps {
  title: string;
  children?: React.ReactNode;
}

export default function Header({ title, children }: HeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <h2
        className="text-2xl font-bold"
        style={{ color: "var(--text-primary)" }}
      >
        {title}
      </h2>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}
