"use client";

import { TopBar } from "@/components/layout/TopBar";
import { getUsageReport } from "@/lib/api/analytics";
import { formatBytes, formatDateTime } from "@/lib/utils";
import type { ReportDimension } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

const dimensions: { value: ReportDimension; label: string }[] = [
  { value: "user", label: "By user" },
  { value: "folder", label: "By folder" },
  { value: "sensitivity", label: "By sensitivity" },
];

export default function ReportsPage() {
  const [dimension, setDimension] = useState<ReportDimension>("folder");
  const { data, isLoading, error } = useQuery({
    queryKey: ["usage-report", dimension],
    queryFn: () => getUsageReport(dimension),
  });

  return (
    <>
      <TopBar title="Reports" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6 flex gap-2">
          {dimensions.map((d) => (
            <button
              key={d.value}
              type="button"
              onClick={() => setDimension(d.value)}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                dimension === d.value
                  ? "bg-vault-800 text-teal-300 ring-1 ring-vault-600"
                  : "text-slate-400 hover:bg-vault-900 hover:text-slate-200"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
        {isLoading && <p className="text-sm text-slate-500">Generating report…</p>}
        {error && (
          <p className="text-sm text-red-400">
            {error instanceof Error ? error.message : "Failed to load report"}
          </p>
        )}
        {data && (
          <>
            <p className="mb-4 text-xs text-slate-500">
              Generated {formatDateTime(data.generated_at)}
            </p>
            <div className="overflow-hidden rounded-lg border border-vault-700">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-vault-700 bg-vault-900/80 text-xs uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Label</th>
                    <th className="px-4 py-3 font-medium">Documents</th>
                    <th className="px-4 py-3 font-medium">Storage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-vault-800">
                  {data.rows.map((row) => (
                    <tr key={row.key} className="hover:bg-vault-900/50">
                      <td className="px-4 py-3 text-slate-200">{row.label}</td>
                      <td className="px-4 py-3 text-slate-400">{row.document_count}</td>
                      <td className="px-4 py-3 text-slate-400">
                        {formatBytes(row.storage_bytes)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </>
  );
}
