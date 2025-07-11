"use client";

import { TopBar } from "@/components/layout/TopBar";
import { Badge } from "@/components/ui/Badge";
import { Shield, Users, Building2 } from "lucide-react";

const adminSections = [
  {
    title: "Organizations",
    description: "Manage org plans, storage quotas, and activation status.",
    icon: Building2,
  },
  {
    title: "Members & roles",
    description: "Invite users and assign owner, admin, editor, or viewer roles.",
    icon: Users,
  },
  {
    title: "Audit & compliance",
    description: "Review immutable audit trails and export compliance reports.",
    icon: Shield,
  },
];

export default function AdminPage() {
  return (
    <>
      <TopBar title="Admin" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6 flex items-center gap-2">
          <Badge variant="warning">Administration</Badge>
          <p className="text-sm text-slate-500">Restricted to organization owners and admins</p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {adminSections.map(({ title, description, icon: Icon }) => (
            <article
              key={title}
              className="rounded-lg border border-vault-700 bg-vault-900/50 p-5"
            >
              <Icon className="h-6 w-6 text-teal-500" />
              <h3 className="mt-3 font-serif text-lg text-slate-100">{title}</h3>
              <p className="mt-2 text-sm text-slate-400">{description}</p>
            </article>
          ))}
        </div>
      </div>
    </>
  );
}
