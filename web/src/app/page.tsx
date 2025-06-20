import { Button } from "@/components/ui/Button";
import { Shield } from "lucide-react";
import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-vault-950 vault-pattern">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-vault-900/40 via-transparent to-vault-950" />
      <div className="pointer-events-none absolute -right-32 top-1/4 h-96 w-96 rounded-full bg-teal-900/20 blur-3xl" />
      <div className="pointer-events-none absolute -left-24 bottom-1/4 h-80 w-80 rounded-full bg-cyan-900/10 blur-3xl" />

      <header className="relative z-10 flex items-center justify-between px-6 py-6 lg:px-12">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-950/50 ring-1 ring-teal-700/50">
            <Shield className="h-5 w-5 text-teal-400" />
          </div>
          <span className="font-serif text-lg tracking-wide text-slate-100">VaultForge</span>
        </div>
        <nav className="flex items-center gap-4">
          <Link href="/login" className="text-sm text-slate-400 transition hover:text-slate-200">
            Sign in
          </Link>
          <Link href="/register">
            <Button size="sm">Get started</Button>
          </Link>
        </nav>
      </header>

      <main className="relative z-10 flex min-h-[calc(100vh-5rem)] flex-col items-center justify-center px-6 text-center">
        <p className="mb-4 text-xs font-medium uppercase tracking-[0.2em] text-teal-500/80">
          Enterprise document vault
        </p>
        <h1 className="max-w-3xl font-serif text-4xl font-semibold leading-tight text-slate-50 sm:text-5xl lg:text-6xl">
          Secure every asset. Control every workflow.
        </h1>
        <p className="mt-6 max-w-xl text-lg text-slate-400">
          VaultForge unifies document storage, approval chains, and e-signatures in one
          industrial-grade platform built for regulated teams.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link href="/register">
            <Button size="lg">Start your vault</Button>
          </Link>
          <Link href="/login">
            <Button variant="secondary" size="lg">
              Sign in to console
            </Button>
          </Link>
        </div>
      </main>

      <footer className="relative z-10 border-t border-vault-800/60 px-6 py-6 text-center text-xs text-slate-600 lg:px-12">
        © {new Date().getFullYear()} VaultForge. All rights reserved.
      </footer>
    </div>
  );
}
