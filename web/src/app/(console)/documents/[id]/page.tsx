"use client";

import { VersionList } from "@/components/documents/VersionList";
import { TopBar } from "@/components/layout/TopBar";
import { Badge } from "@/components/ui/Badge";
import { getDocument, getDocumentVersions } from "@/lib/api/documents";
import { formatDate, formatBytes } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, FileText } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function DocumentDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const { data: doc, isLoading, error } = useQuery({
    queryKey: ["document", id],
    queryFn: () => getDocument(id),
  });

  const { data: versions = [] } = useQuery({
    queryKey: ["document-versions", id],
    queryFn: () => getDocumentVersions(id),
    enabled: Boolean(doc),
  });

  return (
    <>
      <TopBar title={doc?.name ?? "Document"} />
      <div className="flex-1 overflow-y-auto p-6">
        <Link
          href="/documents"
          className="mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-teal-300"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to documents
        </Link>
        {isLoading && <p className="text-sm text-slate-500">Loading…</p>}
        {error && (
          <p className="text-sm text-red-400">
            {error instanceof Error ? error.message : "Document not found"}
          </p>
        )}
        {doc && (
          <div className="space-y-8">
            <div className="rounded-lg border border-vault-700 bg-vault-900/50 p-6">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-vault-800">
                  <FileText className="h-6 w-6 text-teal-500" />
                </div>
                <div className="flex-1">
                  <h2 className="font-serif text-xl text-slate-100">{doc.name}</h2>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge variant="info">{doc.status}</Badge>
                    <Badge variant="warning">{doc.sensitivity}</Badge>
                  </div>
                  <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="text-slate-500">Created</dt>
                      <dd className="text-slate-300">{formatDate(doc.created_at)}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">Updated</dt>
                      <dd className="text-slate-300">{formatDate(doc.updated_at)}</dd>
                    </div>
                    {doc.current_version && (
                      <div>
                        <dt className="text-slate-500">Size</dt>
                        <dd className="text-slate-300">
                          {formatBytes(doc.current_version.size_bytes)}
                        </dd>
                      </div>
                    )}
                  </dl>
                  {doc.tags.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {doc.tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded bg-vault-800 px-2 py-0.5 text-xs text-slate-400"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
            <section>
              <h3 className="mb-3 font-serif text-lg text-slate-200">Version history</h3>
              <VersionList versions={versions} />
            </section>
          </div>
        )}
      </div>
    </>
  );
}
