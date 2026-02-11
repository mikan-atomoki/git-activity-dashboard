"use client";

import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import Sidebar from "./Sidebar";
import MobileNav from "./MobileNav";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const pathname = usePathname();

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div
        className="flex h-screen items-center justify-center"
        style={{ backgroundColor: "var(--bg-primary)" }}
      >
        <div
          className="h-8 w-8 animate-spin rounded-full border-2 border-t-transparent"
          style={{ borderColor: "var(--accent-blue)", borderTopColor: "transparent" }}
        />
      </div>
    );
  }

  // Login page: no sidebar/nav
  if (pathname === "/login") {
    return <>{children}</>;
  }

  // If not authenticated and not on login page, redirect
  if (!isAuthenticated) {
    // Client-side redirect
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    return null;
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-6 pb-20 lg:pb-6">
        {children}
      </main>
      <MobileNav />
    </div>
  );
}
