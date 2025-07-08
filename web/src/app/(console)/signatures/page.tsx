"use client";

import { TopBar } from "@/components/layout/TopBar";
import { Badge } from "@/components/ui/Badge";
import { PenLine } from "lucide-react";

export default function SignaturesPage() {
  return (
    <>
      <TopBar title="Signatures" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-vault-700 py-16">
          <PenLine className="h-10 w-10 text-slate-600" />
          <p className="mt-3 text-sm text-slate-400">Signature requests</p>
          <p className="mt-1 max-w-md text-center text-xs text-slate-500">
            Create multi-signer requests tied to document versions. Pending and completed
            requests will appear here once connected to the API.
          </p>
          <Badge variant="info" className="mt-4">
            API ready
          </Badge>
        </div>
      </div>
    </>
  );
}
