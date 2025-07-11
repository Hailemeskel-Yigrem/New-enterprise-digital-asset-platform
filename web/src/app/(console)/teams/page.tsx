"use client";

import { TopBar } from "@/components/layout/TopBar";
import { Badge } from "@/components/ui/Badge";
import { Users } from "lucide-react";

export default function TeamsPage() {
  return (
    <>
      <TopBar title="Teams" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-vault-700 py-16">
          <Users className="h-10 w-10 text-slate-600" />
          <p className="mt-3 text-sm text-slate-400">Team management</p>
          <p className="mt-1 max-w-md text-center text-xs text-slate-500">
            Create teams, assign members, and scope folder access. Connect to{" "}
            <code className="text-teal-500/80">/teams</code> API endpoints to list and manage teams.
          </p>
          <Badge variant="info" className="mt-4">
            API ready
          </Badge>
        </div>
      </div>
    </>
  );
}
