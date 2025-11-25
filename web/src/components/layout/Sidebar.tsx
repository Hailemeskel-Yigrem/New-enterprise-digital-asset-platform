"use client";

import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";
import { getUnreadCount } from "@/lib/api/notifications";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Bell,
  FileText,
  FolderTree,
  GitBranch,
  LayoutDashboard,
  PenLine,
  Search,
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
  { href: "/search", label: "Search", icon: Search },
  { href: "/workflows", label: "Workflows", icon: GitBranch },
  { href: "/signatures", label: "Signatures", icon: PenLine },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/notifications", label: "Notifications", icon: Bell, badge: true },
  { href: "/reports", label: "Reports", icon: BarChart3 },
  { href: "/teams", label: "Teams", icon: Users },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/admin", label: "Admin", icon: Shield },
];

export function Sidebar() {
  const pathname = usePathname();
  const { isAuthenticated } = useAuth();
  const { data: unreadCount = 0 } = useQuery({
    queryKey: ["notifications-unread-count"],
    queryFn: getUnreadCount,
    enabled: isAuthenticated,
    refetchInterval: 60_000,
  });

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
        {navItems.map(({ href, label, icon: Icon, badge }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          const showBadge = badge && unreadCount > 0;
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
              <span className="flex-1">{label}</span>
              {showBadge && (
                <span className="rounded-full bg-teal-700 px-1.5 py-0.5 text-[10px] font-medium text-white">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-vault-800 p-4">
        <p className="text-xs text-slate-500">Enterprise document vault · v0.9.0</p>
      </div>
    </aside>
  );
}
