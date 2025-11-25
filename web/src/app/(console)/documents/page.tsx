"use client";

import { DocumentTable } from "@/components/documents/DocumentTable";
import { UploadDialog } from "@/components/documents/UploadDialog";
import { TopBar } from "@/components/layout/TopBar";
import { useDocuments } from "@/hooks/useDocuments";
import { useFolderTree } from "@/hooks/useFolders";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { Filter, FolderTree, Upload } from "lucide-react";
import { useState } from "react";

export default function DocumentsPage() {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [folderFilter, setFolderFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>("active");
  const { data, isLoading, error } = useDocuments({
    folderId: folderFilter,
    status: statusFilter,
    limit: 50,
  });
  const { folders } = useFolderTree();

  return (
    <>
      <TopBar title="Documents" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm text-slate-400">
              {data ? `${data.total} document${data.total !== 1 ? "s" : ""}` : "Browse your vault"}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Filter className="h-3.5 w-3.5 text-slate-600" />
              {(["active", "draft", "archived"] as const).map((status) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => setStatusFilter(status)}
                  className={cn(
                    "rounded-full px-3 py-1 text-xs capitalize",
                    statusFilter === status
                      ? "bg-teal-900/50 text-teal-200 ring-1 ring-teal-700"
                      : "bg-vault-800 text-slate-400 hover:text-slate-200",
                  )}
                >
                  {status}
                </button>
              ))}
            </div>
          </div>
          <Button onClick={() => setUploadOpen(true)}>
            <Upload className="h-4 w-4" />
            Upload
          </Button>
        </div>

        <div className="mb-6 grid gap-6 lg:grid-cols-[240px_1fr]">
          <aside className="rounded-lg border border-vault-700 bg-vault-900/40 p-4">
            <h3 className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-slate-500">
              <FolderTree className="h-3.5 w-3.5" />
              Folders
            </h3>
            <ul className="space-y-1 text-sm">
              <li>
                <button
                  type="button"
                  onClick={() => setFolderFilter(undefined)}
                  className={cn(
                    "w-full rounded px-2 py-1.5 text-left",
                    !folderFilter ? "bg-vault-800 text-teal-300" : "text-slate-400 hover:text-slate-200",
                  )}
                >
                  All folders
                </button>
              </li>
              {folders.slice(0, 12).map((f) => (
                <li key={f.id}>
                  <button
                    type="button"
                    onClick={() => setFolderFilter(f.id)}
                    className={cn(
                      "w-full truncate rounded px-2 py-1.5 text-left",
                      folderFilter === f.id
                        ? "bg-vault-800 text-teal-300"
                        : "text-slate-400 hover:text-slate-200",
                    )}
                  >
                    {f.name}
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          <div>
            {isLoading && <p className="text-sm text-slate-500">Loading documents…</p>}
            {error && (
              <p className="text-sm text-red-400">
                {error instanceof Error ? error.message : "Failed to load documents"}
              </p>
            )}
            {data && <DocumentTable documents={data.items} />}
          </div>
        </div>
      </div>
      <UploadDialog open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </>
  );
}
