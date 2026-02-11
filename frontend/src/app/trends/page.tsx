import Header from "@/components/layout/Header";
import Card from "@/components/ui/Card";
import DashboardGrid from "@/components/dashboard/DashboardGrid";

export default function TrendsPage() {
  return (
    <>
      <Header title="Trends" />

      <DashboardGrid className="mb-6">
        <Card title="Technology Trend">
          <div
            className="flex h-64 items-center justify-center rounded-lg"
            style={{ backgroundColor: "var(--bg-tertiary)" }}
          >
            <p style={{ color: "var(--text-secondary)" }}>Coming Soon</p>
          </div>
        </Card>
        <Card title="Language Trend">
          <div
            className="flex h-64 items-center justify-center rounded-lg"
            style={{ backgroundColor: "var(--bg-tertiary)" }}
          >
            <p style={{ color: "var(--text-secondary)" }}>Coming Soon</p>
          </div>
        </Card>
      </DashboardGrid>

      <Card title="Monthly Summary List">
        <div className="space-y-4">
          {["2026-01", "2025-12", "2025-11"].map((month) => (
            <div
              key={month}
              className="flex items-center justify-between rounded-lg border p-4"
              style={{
                backgroundColor: "var(--bg-tertiary)",
                borderColor: "var(--border)",
              }}
            >
              <div>
                <p
                  className="font-medium"
                  style={{ color: "var(--text-primary)" }}
                >
                  {month}
                </p>
                <p
                  className="text-sm"
                  style={{ color: "var(--text-secondary)" }}
                >
                  Coming Soon
                </p>
              </div>
              <span
                className="text-sm"
                style={{ color: "var(--text-secondary)" }}
              >
                --
              </span>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}
