"use client";

import { DocumentTable } from "@/components/documents/DocumentTable";
import { UploadDialog } from "@/components/documents/UploadDialog";
import { TopBar } from "@/components/layout/TopBar";
import { searchDocuments } from "@/lib/api/documents";
import { Button } from "@/components/ui/Button";
import { useQuery } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { useState } from "react";

export default function DocumentsPage() {
  const [uploadOpen, setUploadOpen] = useState(false);
  const { data, isLoading, error } = useQuery({
    queryKey: ["documents"],
    queryFn: () => searchDocuments({ limit: 50 }),
  });

  return (
    <>
      <TopBar title="Documents" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6 flex items-center justify-between">
          <p className="text-sm text-slate-400">
            {data ? `${data.total} document${data.total !== 1 ? "s" : ""}` : "Browse your vault"}
          </p>
          <Button onClick={() => setUploadOpen(true)}>
            <Upload className="h-4 w-4" />
            Upload
          </Button>
        </div>
        {isLoading && <p className="text-sm text-slate-500">Loading documents…</p>}
        {error && (
          <p className="text-sm text-red-400">
            {error instanceof Error ? error.message : "Failed to load documents"}
          </p>
        )}
        {data && <DocumentTable documents={data.items} />}
      </div>
      <UploadDialog open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </>
  );
}
