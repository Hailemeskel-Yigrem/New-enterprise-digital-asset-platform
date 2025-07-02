"use client";

import { StatStrip } from "@/components/dashboard/StatStrip";
import { TopBar } from "@/components/layout/TopBar";
import { getDashboard } from "@/lib/api/analytics";
import { formatRelative } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });

  return (
    <>
      <TopBar title="Dashboard" />
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading && (
          <p className="text-sm text-slate-500">Loading dashboard…</p>
        )}
        {error && (
          <p className="text-sm text-red-400">
            {error instanceof Error ? error.message : "Failed to load dashboard"}
          </p>
        )}
        {data && (
          <div className="space-y-8">
            <StatStrip stats={data.stats} />
            <section>
              <h2 className="mb-4 flex items-center gap-2 font-serif text-lg text-slate-200">
                <Activity className="h-5 w-5 text-teal-500" />
                Recent activity
              </h2>
              {data.recent_activity.length === 0 ? (
                <p className="text-sm text-slate-500">No recent activity.</p>
              ) : (
                <ul className="divide-y divide-vault-800 rounded-lg border border-vault-700">
                  {data.recent_activity.map((item) => (
                    <li
                      key={`${item.kind}-${item.resource_id}-${item.occurred_at}`}
                      className="flex items-center justify-between px-4 py-3"
                    >
                      <div>
                        <p className="text-sm text-slate-200">{item.resource_name}</p>
                        <p className="text-xs capitalize text-slate-500">
                          {item.kind.replace(/_/g, " ")}
                        </p>
                      </div>
                      <time className="text-xs text-slate-500">
                        {formatRelative(item.occurred_at)}
                      </time>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </div>
    </>
  );
}
