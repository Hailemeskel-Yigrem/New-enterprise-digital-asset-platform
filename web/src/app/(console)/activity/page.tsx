"use client";

import { ActivityTimeline } from "@/components/activity/ActivityTimeline";
import { TopBar } from "@/components/layout/TopBar";
import { getActivityFeed } from "@/lib/api/analytics";
import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { useState } from "react";

export default function ActivityPage() {
  const [limit, setLimit] = useState(50);
  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["activity", limit],
    queryFn: () => getActivityFeed({ limit }),
  });

  return (
    <>
      <TopBar title="Activity" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6 flex items-center justify-between">
          <p className="flex items-center gap-2 text-sm text-slate-400">
            <Activity className="h-4 w-4 text-teal-500" />
            {data ? `${data.total} events` : "Organization activity feed"}
          </p>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="rounded-md border border-vault-700 bg-vault-900 px-3 py-1.5 text-xs text-slate-300"
          >
            {[25, 50, 100].map((n) => (
              <option key={n} value={n}>
                Show {n}
              </option>
            ))}
          </select>
        </div>
        {error && (
          <p className="text-sm text-red-400">
            {error instanceof Error ? error.message : "Failed to load activity"}
          </p>
        )}
        <ActivityTimeline
          items={data?.items ?? []}
          isLoading={isLoading || isFetching}
        />
      </div>
    </>
  );
}
