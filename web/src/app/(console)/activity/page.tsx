"use client";

import { TopBar } from "@/components/layout/TopBar";
import { getActivityFeed } from "@/lib/api/analytics";
import { formatRelative } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";

export default function ActivityPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["activity"],
    queryFn: () => getActivityFeed({ limit: 50 }),
  });

  return (
    <>
      <TopBar title="Activity" />
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading && <p className="text-sm text-slate-500">Loading activity…</p>}
        {error && (
          <p className="text-sm text-red-400">
            {error instanceof Error ? error.message : "Failed to load activity"}
          </p>
        )}
        {data && (
          <ul className="divide-y divide-vault-800 rounded-lg border border-vault-700">
            {data.items.length === 0 ? (
              <li className="px-4 py-8 text-center text-sm text-slate-500">
                No activity recorded.
              </li>
            ) : (
              data.items.map((item) => (
                <li key={item.id} className="flex items-start justify-between gap-4 px-4 py-4">
                  <div>
                    <p className="text-sm text-slate-200">{item.summary}</p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {item.activity_type} · {item.resource_type}
                    </p>
                  </div>
                  <time className="shrink-0 text-xs text-slate-500">
                    {formatRelative(item.created_at)}
                  </time>
                </li>
              ))
            )}
          </ul>
        )}
      </div>
    </>
  );
}
