"use client";

import { Badge } from "@/components/ui/Badge";
import { formatBytes, formatRelative } from "@/lib/utils";
import type { Document, SensitivityLabel } from "@/lib/types";
import { FileText, Lock } from "lucide-react";
import Link from "next/link";

const sensitivityVariant: Record<SensitivityLabel, "default" | "info" | "warning" | "danger"> = {
  public: "default",
  internal: "info",
  confidential: "warning",
  restricted: "danger",
};

export function DocumentTable({ documents }: { documents: Document[] }) {
  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-vault-700 py-16">
        <FileText className="h-10 w-10 text-slate-600" />
        <p className="mt-3 text-sm text-slate-400">No documents found</p>
        <p className="text-xs text-slate-500">Upload a file to get started</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-vault-700">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-vault-700 bg-vault-900/80 text-xs uppercase tracking-wider text-slate-500">
          <tr>
            <th className="px-4 py-3 font-medium">Name</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Sensitivity</th>
            <th className="px-4 py-3 font-medium">Size</th>
            <th className="px-4 py-3 font-medium">Updated</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-vault-800">
          {documents.map((doc) => (
            <tr key={doc.id} className="hover:bg-vault-900/50">
              <td className="px-4 py-3">
                <Link
                  href={`/documents/${doc.id}`}
                  className="flex items-center gap-2 font-medium text-slate-200 hover:text-teal-300"
                >
                  {doc.sensitivity === "restricted" && (
                    <Lock className="h-3.5 w-3.5 text-amber-500" />
                  )}
                  {doc.name}
                </Link>
                {doc.tags.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {doc.tags.slice(0, 3).map((tag) => (
                      <span key={tag} className="text-xs text-slate-500">
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </td>
              <td className="px-4 py-3 capitalize text-slate-400">{doc.status}</td>
              <td className="px-4 py-3">
                <Badge variant={sensitivityVariant[doc.sensitivity]}>
                  {doc.sensitivity}
                </Badge>
              </td>
              <td className="px-4 py-3 text-slate-400">
                {doc.current_version
                  ? formatBytes(doc.current_version.size_bytes)
                  : "—"}
              </td>
              <td className="px-4 py-3 text-slate-500">
                {formatRelative(doc.updated_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
