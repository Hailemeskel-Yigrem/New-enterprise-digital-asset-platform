"use client";

import { ActivityTimeline } from "@/components/activity/ActivityTimeline";
import { StatStrip } from "@/components/dashboard/StatStrip";
import { TopBar } from "@/components/layout/TopBar";
import { getActivityFeed, getDashboard } from "@/lib/api/analytics";
import { formatBytes, formatRelative } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { Activity, HardDrive, TrendingUp } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });

  const { data: activity } = useQuery({
    queryKey: ["activity-recent"],
    queryFn: () => getActivityFeed({ limit: 12 }),
  });

  const storagePercent = data
    ? Math.min(
        100,
        Math.round((data.stats.storage_used_bytes / data.stats.storage_limit_bytes) * 100),
      )
    : 0;

  return (
    <>
      <TopBar title="Dashboard" />
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading && <p className="text-sm text-slate-500">Loading dashboard…</p>}
        {error && (
          <p className="text-sm text-red-400">
            {error instanceof Error ? error.message : "Failed to load dashboard"}
          </p>
        )}
        {data && (
          <div className="space-y-8">
            <StatStrip stats={data.stats} />

            <div className="grid gap-4 md:grid-cols-2">
              <section className="rounded-lg border border-vault-700 bg-vault-900/40 p-5">
                <h3 className="flex items-center gap-2 text-sm font-medium text-slate-300">
                  <HardDrive className="h-4 w-4 text-teal-500" />
                  Storage utilization
                </h3>
                <div className="mt-4">
                  <div className="flex justify-between text-xs text-slate-500">
                    <span>{formatBytes(data.stats.storage_used_bytes)} used</span>
                    <span>{formatBytes(data.stats.storage_limit_bytes)} limit</span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-vault-800">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-teal-700 to-teal-500"
                      style={{ width: `${storagePercent}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-slate-500">{storagePercent}% of quota</p>
                </div>
              </section>

              <section className="rounded-lg border border-vault-700 bg-vault-900/40 p-5">
                <h3 className="flex items-center gap-2 text-sm font-medium text-slate-300">
                  <TrendingUp className="h-4 w-4 text-teal-500" />
                  Quick actions
                </h3>
                <ul className="mt-4 space-y-2 text-sm">
                  <li>
                    <Link href="/documents" className="text-teal-400 hover:text-teal-300">
                      Upload a document →
                    </Link>
                  </li>
                  <li>
                    <Link href="/workflows" className="text-teal-400 hover:text-teal-300">
                      Review pending approvals ({data.stats.pending_approvals}) →
                    </Link>
                  </li>
                  <li>
                    <Link href="/search" className="text-teal-400 hover:text-teal-300">
                      Search the vault →
                    </Link>
                  </li>
                </ul>
              </section>
            </div>

            <section>
              <div className="mb-4 flex items-center justify-between">
                <h2 className="flex items-center gap-2 font-serif text-lg text-slate-200">
                  <Activity className="h-5 w-5 text-teal-500" />
                  Recent activity
                </h2>
                <Link href="/activity" className="text-xs text-teal-500 hover:text-teal-300">
                  View all
                </Link>
              </div>
              {data.recent_activity.length === 0 && !activity?.items.length ? (
                <p className="text-sm text-slate-500">No recent activity.</p>
              ) : (
                <ul className="mb-6 divide-y divide-vault-800 rounded-lg border border-vault-700">
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
              {activity && activity.items.length > 0 && (
                <ActivityTimeline items={activity.items.slice(0, 6)} groupByDay={false} />
              )}
            </section>
          </div>
        )}
      </div>
    </>
  );
}
