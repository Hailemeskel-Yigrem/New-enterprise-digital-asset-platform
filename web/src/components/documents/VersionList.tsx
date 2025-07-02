import { Badge } from "@/components/ui/Badge";
import { formatBytes, formatDateTime } from "@/lib/utils";
import type { DocumentVersion } from "@/lib/types";

export function VersionList({ versions }: { versions: DocumentVersion[] }) {
  if (versions.length === 0) {
    return <p className="text-sm text-slate-500">No versions recorded.</p>;
  }

  return (
    <ul className="divide-y divide-vault-800 rounded-lg border border-vault-700">
      {versions.map((v) => (
        <li key={v.id} className="flex items-center justify-between px-4 py-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-slate-200">v{v.version_number}</span>
              <Badge variant={v.status === "current" ? "success" : "default"}>
                {v.status}
              </Badge>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              {formatBytes(v.size_bytes)} · {v.content_type}
            </p>
            {v.comment && (
              <p className="mt-1 text-sm text-slate-400">{v.comment}</p>
            )}
          </div>
          <time className="text-xs text-slate-500">{formatDateTime(v.created_at)}</time>
        </li>
      ))}
    </ul>
  );
}
