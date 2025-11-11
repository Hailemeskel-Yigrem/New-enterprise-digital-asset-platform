"use client";

import { SearchBar } from "@/components/search/SearchBar";
import { SearchResults } from "@/components/search/SearchResults";
import { TopBar } from "@/components/layout/TopBar";
import { globalSearch } from "@/lib/api/search";
import type { GlobalSearchResponse, SensitivityLabel } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { Filter, History, Search } from "lucide-react";
import { useEffect, useState } from "react";

const RECENT_KEY = "vf-recent-searches";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [resourceFilter, setResourceFilter] = useState<string[]>(["document", "folder"]);
  const [sensitivity, setSensitivity] = useState<SensitivityLabel[]>([]);
  const [recent, setRecent] = useState<string[]>([]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(RECENT_KEY);
      if (stored) setRecent(JSON.parse(stored) as string[]);
    } catch {
      /* ignore */
    }
  }, []);

  const { data, isLoading, error } = useQuery<GlobalSearchResponse>({
    queryKey: ["global-search", submitted, resourceFilter, sensitivity],
    queryFn: () =>
      globalSearch({
        query: submitted,
        limit: 40,
        resource_types: resourceFilter,
        sensitivity: sensitivity.length ? sensitivity : undefined,
        highlight: true,
      }),
    enabled: submitted.trim().length >= 2,
  });

  function handleSubmit(value: string) {
    setSubmitted(value);
    if (value.length >= 2) {
      setRecent((prev) => {
        const next = [value, ...prev.filter((q) => q !== value)].slice(0, 8);
        localStorage.setItem(RECENT_KEY, JSON.stringify(next));
        return next;
      });
    }
  }

  return (
    <>
      <TopBar title="Search" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-3xl space-y-6">
          <div className="rounded-xl border border-vault-700 bg-vault-900/40 p-6 vault-pattern">
            <h2 className="mb-4 flex items-center gap-2 font-serif text-xl text-slate-100">
              <Search className="h-5 w-5 text-teal-500" />
              Global search
            </h2>
            <SearchBar value={query} onChange={setQuery} onSubmit={handleSubmit} autoFocus />
          </div>

          {recent.length > 0 && !submitted && (
            <section>
              <h3 className="mb-2 flex items-center gap-2 text-xs uppercase tracking-widest text-slate-500">
                <History className="h-3.5 w-3.5" />
                Recent
              </h3>
              <div className="flex flex-wrap gap-2">
                {recent.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => {
                      setQuery(q);
                      handleSubmit(q);
                    }}
                    className="rounded-full bg-vault-800 px-3 py-1 text-xs text-slate-400 hover:text-teal-300"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </section>
          )}

          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Filter className="h-4 w-4 text-slate-500" />
              {(["document", "folder", "workflow"] as const).map((type) => {
                const active = resourceFilter.includes(type);
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() =>
                      setResourceFilter((prev) =>
                        active ? prev.filter((t) => t !== type) : [...prev, type],
                      )
                    }
                    className={
                      active
                        ? "rounded-full bg-teal-900/50 px-3 py-1 text-xs text-teal-200 ring-1 ring-teal-700"
                        : "rounded-full bg-vault-800 px-3 py-1 text-xs text-slate-400 hover:text-slate-200"
                    }
                  >
                    {type}
                  </button>
                );
              })}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {(["public", "internal", "confidential", "restricted"] as SensitivityLabel[]).map(
                (label) => {
                  const active = sensitivity.includes(label);
                  return (
                    <button
                      key={label}
                      type="button"
                      onClick={() =>
                        setSensitivity((prev) =>
                          active ? prev.filter((s) => s !== label) : [...prev, label],
                        )
                      }
                      className={
                        active
                          ? "rounded-full bg-amber-900/40 px-3 py-1 text-xs text-amber-200"
                          : "rounded-full border border-vault-700 px-3 py-1 text-xs text-slate-500"
                      }
                    >
                      {label}
                    </button>
                  );
                },
              )}
            </div>
          </div>

          <SearchResults
            results={data ?? null}
            isLoading={isLoading && submitted.length >= 2}
            error={error instanceof Error ? error : null}
          />
        </div>
      </div>
    </>
  );
}
