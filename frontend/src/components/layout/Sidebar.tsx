"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { NAV_ITEMS } from "@/constants/navigation";
import { useAuth } from "@/contexts/AuthContext";

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { username, logout } = useAuth();

  return (
    <aside
      className="hidden w-64 flex-col border-r lg:flex"
      style={{
        backgroundColor: "var(--bg-secondary)",
        borderColor: "var(--border)",
      }}
    >
      {/* Logo */}
      <div
        className="flex h-16 items-center border-b px-6"
        style={{ borderColor: "var(--border)" }}
      >
        <h1 className="text-xl font-bold" style={{ color: "var(--accent-blue)" }}>
          Git Dashboard
        </h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
              style={{
                backgroundColor: isActive ? "var(--bg-tertiary)" : "transparent",
                color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
              }}
            >
              <span className="text-lg">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div
        className="space-y-3 border-t px-6 py-4"
        style={{ borderColor: "var(--border)" }}
      >
        {username && (
          <p className="truncate text-sm font-medium" style={{ color: "var(--text-primary)" }}>
            {username}
          </p>
        )}
        <button
          onClick={() => {
            logout();
            router.push("/login");
          }}
          className="text-xs transition-colors hover:underline"
          style={{ color: "var(--text-secondary)" }}
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
