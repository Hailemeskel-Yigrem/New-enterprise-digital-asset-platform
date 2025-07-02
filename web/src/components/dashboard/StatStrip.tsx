import { cn, formatBytes } from "@/lib/utils";
import type { DashboardStats } from "@/lib/types";
import { FileText, FolderTree, GitBranch, HardDrive } from "lucide-react";

const items = [
  { key: "document_count" as const, label: "Documents", icon: FileText },
  { key: "folder_count" as const, label: "Folders", icon: FolderTree },
  { key: "pending_approvals" as const, label: "Pending approvals", icon: GitBranch },
  { key: "storage_used_bytes" as const, label: "Storage used", icon: HardDrive, format: formatBytes },
];

export function StatStrip({ stats }: { stats: DashboardStats }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {items.map(({ key, label, icon: Icon, format }) => {
        const raw = stats[key];
        const value = format ? format(raw) : raw.toLocaleString();
        const storagePct =
          key === "storage_used_bytes" && stats.storage_limit_bytes > 0
            ? Math.round((stats.storage_used_bytes / stats.storage_limit_bytes) * 100)
            : null;

        return (
          <div
            key={key}
            className="rounded-lg border border-vault-700 bg-vault-900/60 p-5"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-400">{label}</p>
              <Icon className="h-4 w-4 text-teal-500/70" />
            </div>
            <p className="mt-2 font-serif text-2xl text-slate-100">{value}</p>
            {storagePct !== null && (
              <div className="mt-3">
                <div className="h-1.5 overflow-hidden rounded-full bg-vault-800">
                  <div
                    className={cn(
                      "h-full rounded-full bg-teal-600 transition-all",
                      storagePct > 85 && "bg-amber-500",
                    )}
                    style={{ width: `${Math.min(storagePct, 100)}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-slate-500">{storagePct}% of quota</p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
