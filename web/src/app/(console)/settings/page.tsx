"use client";

import { TopBar } from "@/components/layout/TopBar";
import { useAuth } from "@/providers/auth-provider";
import { Input } from "@/components/ui/Input";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <>
      <TopBar title="Settings" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-xl space-y-6">
          <section className="rounded-lg border border-vault-700 bg-vault-900/50 p-6">
            <h2 className="font-serif text-lg text-slate-200">Profile</h2>
            <p className="mt-1 text-sm text-slate-500">Your account details</p>
            <div className="mt-4 space-y-4">
              <Input label="Full name" value={user?.full_name ?? ""} readOnly />
              <Input label="Email" value={user?.email ?? ""} readOnly />
            </div>
          </section>
          <section className="rounded-lg border border-vault-700 bg-vault-900/50 p-6">
            <h2 className="font-serif text-lg text-slate-200">Organization</h2>
            <p className="mt-1 text-sm text-slate-500">
              Organization settings are managed by administrators.
            </p>
          </section>
        </div>
      </div>
    </>
  );
}
