"use client";

import { useAuth as useAuthContext } from "@/providers/auth-provider";
import type { OrgRole } from "@/lib/types";
import { useMemo } from "react";

const ROLE_RANK: Record<OrgRole, number> = {
  viewer: 1,
  editor: 2,
  admin: 3,
  owner: 4,
};

export function useAuth() {
  const ctx = useAuthContext();
  return ctx;
}

export function useCurrentUser() {
  const { user, isLoading } = useAuth();
  return { user, isLoading, userId: user?.id ?? null };
}

export function useRequireAuth() {
  const auth = useAuth();
  if (!auth.isLoading && !auth.isAuthenticated) {
    throw new Error("Authentication required");
  }
  return auth;
}

export function useHasMinRole(required: OrgRole, actual?: OrgRole | null): boolean {
  return useMemo(() => {
    if (!actual) return false;
    return ROLE_RANK[actual] >= ROLE_RANK[required];
  }, [actual, required]);
}
