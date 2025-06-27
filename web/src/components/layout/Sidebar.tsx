"use client";

import { cn } from "@/lib/utils";
import {
  Activity,
  FileText,
  FolderTree,
  GitBranch,
  LayoutDashboard,
  PenLine,
  Settings,
  Shield,
  Users,
  BarChart3,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/folders", label: "Folders", icon: FolderTree },
  { href: "/workflows", label: "Workflows", icon: GitBranch },
  { href: "/signatures", label: "Signatures", icon: PenLine },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/reports", label: "Reports", icon: BarChart3 },
  { href: "/teams", label: "Teams", icon: Users },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/admin", label: "Admin", icon: Shield },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 flex-col border-r border-vault-800 bg-vault-950">
      <div className="flex h-16 items-center gap-2 border-b border-vault-800 px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded bg-forge-teal/20 ring-1 ring-forge-teal/40">
          <Shield className="h-4 w-4 text-teal-400" />
        </div>
        <div>
          <p className="font-serif text-sm font-semibold tracking-wide text-slate-100">
            VaultForge
          </p>
          <p className="text-[10px] uppercase tracking-widest text-slate-500">Console</p>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-vault-800 text-teal-300 ring-1 ring-vault-600"
                  : "text-slate-400 hover:bg-vault-900 hover:text-slate-200",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-vault-800 p-4">
        <p className="text-xs text-slate-500">Enterprise document vault</p>
      </div>
    </aside>
  );
}
