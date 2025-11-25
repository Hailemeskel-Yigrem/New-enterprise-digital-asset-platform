"use client";

import { SignerList } from "@/components/signatures/SignerList";
import { TopBar } from "@/components/layout/TopBar";
import { Badge } from "@/components/ui/Badge";
import { listSignatureRequests, signerProgress } from "@/lib/api/signatures";
import { formatRelative } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { PenLine } from "lucide-react";
import Link from "next/link";

export default function SignaturesPage() {
  const { data: requests = [], isLoading, error } = useQuery({
    queryKey: ["signature-requests"],
    queryFn: () => listSignatureRequests(),
  });

  return (
    <>
      <TopBar title="Signatures" />
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading && <p className="text-sm text-slate-500">Loading signature requests…</p>}
        {error && (
          <p className="text-sm text-red-400">
            {error instanceof Error ? error.message : "Failed to load requests"}
          </p>
        )}
        {!isLoading && requests.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-vault-700 py-16">
            <PenLine className="h-10 w-10 text-slate-600" />
            <p className="mt-3 text-sm text-slate-400">No signature requests yet</p>
            <p className="mt-1 max-w-md text-center text-xs text-slate-500">
              Create multi-signer requests from any document detail page.
            </p>
          </div>
        )}
        <div className="space-y-6">
          {requests.map((req) => {
            const progress = signerProgress(req);
            return (
              <article
                key={req.id}
                className="rounded-lg border border-vault-700 bg-vault-900/40 p-5"
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h3 className="font-serif text-lg text-slate-100">{req.title}</h3>
                    <p className="mt-1 text-sm text-slate-500">{req.message || "No message"}</p>
                    <p className="mt-2 text-xs text-slate-600">
                      Created {formatRelative(req.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={req.status === "completed" ? "success" : "warning"}>
                      {req.status}
                    </Badge>
                    <Badge variant="info">{progress.percent}% signed</Badge>
                  </div>
                </div>
                <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-vault-800">
                  <div
                    className="h-full bg-teal-600 transition-all"
                    style={{ width: `${progress.percent}%` }}
                  />
                </div>
                <div className="mt-4">
                  <SignerList request={req} />
                </div>
                <Link
                  href={`/documents/${req.document_id}`}
                  className="mt-4 inline-block text-xs text-teal-500 hover:text-teal-300"
                >
                  View document →
                </Link>
              </article>
            );
          })}
        </div>
      </div>
    </>
  );
}
