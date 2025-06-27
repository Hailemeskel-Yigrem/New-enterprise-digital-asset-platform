"use client";

import { Sidebar } from "@/components/layout/Sidebar";
import { isAuthenticated } from "@/lib/auth/store";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

export default function ConsoleLayout({ children }: { children: ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div className="flex h-screen overflow-hidden bg-vault-950">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">{children}</div>
    </div>
  );
}
