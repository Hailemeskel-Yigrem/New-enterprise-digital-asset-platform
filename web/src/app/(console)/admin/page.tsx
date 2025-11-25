"use client";

import { TopBar } from "@/components/layout/TopBar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  getAdminOverview,
  getStorageBreakdown,
  listAdminMembers,
  roleDescription,
} from "@/lib/api/admin";
import { formatBytes } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { Building2, HardDrive, Shield, Users } from "lucide-react";

export default function AdminPage() {
  const { data: overview } = useQuery({ queryKey: ["admin-overview"], queryFn: getAdminOverview });
  const { data: members = [] } = useQuery({ queryKey: ["admin-members"], queryFn: listAdminMembers });
  const { data: storage } = useQuery({ queryKey: ["admin-storage"], queryFn: getStorageBreakdown });

  return (
    <>
      <TopBar title="Admin" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6 flex items-center gap-2">
          <Badge variant="warning">Administration</Badge>
          <p className="text-sm text-slate-500">Restricted to organization owners and admins</p>
        </div>

        {overview && (
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Members", value: overview.member_count, icon: Users },
              { label: "Documents", value: overview.document_count, icon: Building2 },
              { label: "Plan", value: overview.plan_code, icon: Shield },
              { label: "Storage cap", value: `${overview.max_storage_gb} GB`, icon: HardDrive },
            ].map(({ label, value, icon: Icon }) => (
              <div
                key={label}
                className="rounded-lg border border-vault-700 bg-vault-900/50 p-4"
              >
                <Icon className="h-5 w-5 text-teal-500" />
                <p className="mt-2 text-xs uppercase tracking-widest text-slate-500">{label}</p>
                <p className="mt-1 font-serif text-2xl text-slate-100">{value}</p>
              </div>
            ))}
          </div>
        )}

        {storage && (
          <section className="mb-8 rounded-lg border border-vault-700 bg-vault-900/40 p-5">
            <h3 className="font-serif text-lg text-slate-200">Storage breakdown</h3>
            <p className="mt-1 text-sm text-slate-500">
              {formatBytes(storage.total_bytes)} of {formatBytes(storage.limit_bytes)} used
            </p>
            <ul className="mt-4 space-y-2">
              {storage.by_folder.slice(0, 5).map((row) => (
                <li key={row.folder_id} className="flex justify-between text-sm">
                  <span className="text-slate-400">{row.name}</span>
                  <span className="text-slate-300">{formatBytes(row.bytes)}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-serif text-lg text-slate-200">Members</h3>
            <Button variant="secondary" size="sm">
              Invite member
            </Button>
          </div>
          <div className="overflow-hidden rounded-lg border border-vault-700">
            <table className="w-full text-sm">
              <thead className="border-b border-vault-800 bg-vault-950/80 text-left text-xs uppercase tracking-widest text-slate-500">
                <tr>
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-vault-800">
                {members.map((m) => (
                  <tr key={m.id} className="hover:bg-vault-900/40">
                    <td className="px-4 py-3">
                      <p className="text-slate-200">{m.full_name}</p>
                      <p className="text-xs text-slate-500">{m.email}</p>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="info">{m.role}</Badge>
                      <p className="mt-1 text-xs text-slate-600">{roleDescription(m.role)}</p>
                    </td>
                    <td className="px-4 py-3 capitalize text-slate-400">{m.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </>
  );
}
