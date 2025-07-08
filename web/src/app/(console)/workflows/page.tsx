"use client";

import { TopBar } from "@/components/layout/TopBar";
import { WorkflowStatusBadge } from "@/components/workflows/WorkflowStatusBadge";
import { listWorkflows } from "@/lib/api/workflows";
import { formatRelative } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { GitBranch } from "lucide-react";

export default function WorkflowsPage() {
  const { data: workflows = [], isLoading, error } = useQuery({
    queryKey: ["workflows"],
    queryFn: listWorkflows,
  });

  return (
    <>
      <TopBar title="Workflows" />
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading && <p className="text-sm text-slate-500">Loading workflows…</p>}
        {error && (
          <p className="text-sm text-red-400">
            {error instanceof Error ? error.message : "Failed to load workflows"}
          </p>
        )}
        {workflows.length === 0 && !isLoading ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-vault-700 py-16">
            <GitBranch className="h-10 w-10 text-slate-600" />
            <p className="mt-3 text-sm text-slate-400">No workflows defined</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {workflows.map((wf) => (
              <article
                key={wf.id}
                className="rounded-lg border border-vault-700 bg-vault-900/50 p-5"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-serif text-lg text-slate-100">{wf.name}</h3>
                  <WorkflowStatusBadge status={wf.status} />
                </div>
                {wf.description && (
                  <p className="mt-2 text-sm text-slate-400">{wf.description}</p>
                )}
                <p className="mt-4 text-xs text-slate-500">
                  {wf.steps.length} step{wf.steps.length !== 1 ? "s" : ""} · Updated{" "}
                  {formatRelative(wf.updated_at)}
                </p>
              </article>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
