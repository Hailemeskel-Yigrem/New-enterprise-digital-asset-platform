"use client";

import { useAuth } from "@/providers/auth-provider";
import { Bell, LogOut, Search } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";

export function TopBar({ title }: { title: string }) {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-vault-800 bg-vault-950/80 px-6 backdrop-blur">
      <h1 className="font-serif text-xl text-slate-100">{title}</h1>
      <div className="flex items-center gap-3">
        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="search"
            placeholder="Search documents, folders…"
            className="h-9 w-64 rounded-md border border-vault-700 bg-vault-900 pl-9 pr-3 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500/30"
          />
        </div>
        <Button variant="ghost" size="sm" aria-label="Notifications">
          <Bell className="h-4 w-4" />
        </Button>
        <div className="hidden h-6 w-px bg-vault-700 sm:block" />
        <div className="hidden text-right sm:block">
          <p className="text-sm text-slate-200">{user?.full_name ?? "User"}</p>
          <p className="text-xs text-slate-500">{user?.email}</p>
        </div>
        <Button variant="ghost" size="sm" onClick={handleLogout} aria-label="Sign out">
          <LogOut className="h-4 w-4" />
        </Button>
        {!user && (
          <Link href="/login" className="text-sm text-teal-400 hover:text-teal-300">
            Sign in
          </Link>
        )}
      </div>
    </header>
  );
}
