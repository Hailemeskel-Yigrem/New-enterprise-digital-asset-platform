"use client";

import { groupHitsByType } from "@/lib/api/search";
import { cn, formatRelative } from "@/lib/utils";
import type { GlobalSearchResponse } from "@/lib/types";
import { FileText, FolderTree, GitBranch, Loader2 } from "lucide-react";
import Link from "next/link";

interface SearchResultsProps {
  results: GlobalSearchResponse | null;
  isLoading?: boolean;
  error?: Error | null;
  className?: string;
}

function typeIcon(type: string) {
  if (type === "folder") return FolderTree;
  if (type === "workflow") return GitBranch;
  return FileText;
}

function resourceHref(type: string, id: string): string {
  if (type === "folder") return `/folders?highlight=${id}`;
  if (type === "workflow") return `/workflows`;
  return `/documents/${id}`;
}

export function SearchResults({
  results,
  isLoading = false,
  error = null,
  className,
}: SearchResultsProps) {
  if (isLoading) {
    return (
      <div className={cn("flex items-center gap-2 py-12 text-sm text-slate-500", className)}>
        <Loader2 className="h-4 w-4 animate-spin text-teal-500" />
        Searching…
      </div>
    );
  }

  if (error) {
    return (
      <p className={cn("rounded-lg border border-red-900/50 bg-red-950/20 px-4 py-3 text-sm text-red-400", className)}>
        {error.message}
      </p>
    );
  }

  if (!results) {
    return (
      <p className={cn("py-12 text-center text-sm text-slate-500", className)}>
        Enter at least two characters to search.
      </p>
    );
  }

  if (results.hits.length === 0) {
    return (
      <p className={cn("py-12 text-center text-sm text-slate-500", className)}>
        No results for &ldquo;{results.query}&rdquo;
      </p>
    );
  }

  const grouped = groupHitsByType(results.hits);

  return (
    <div className={cn("space-y-6", className)}>
      <p className="text-xs text-slate-500">
        {results.total} result{results.total !== 1 ? "s" : ""} in {results.took_ms}ms
      </p>
      {Object.entries(grouped).map(([type, hits]) => {
        const Icon = typeIcon(type);
        return (
          <section key={type}>
            <h3 className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-slate-500">
              <Icon className="h-3.5 w-3.5" />
              {type}
            </h3>
            <ul className="divide-y divide-vault-800 rounded-lg border border-vault-700">
              {hits.map((hit) => (
                <li key={hit.id}>
                  <Link
                    href={resourceHref(hit.resource_type, hit.id)}
                    className="flex items-start justify-between gap-4 px-4 py-3 transition-colors hover:bg-vault-900/60"
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-200">{hit.title}</p>
                      <p
                        className="mt-1 text-xs text-slate-500"
                        dangerouslySetInnerHTML={{ __html: hit.snippet }}
                      />
                    </div>
                    <div className="shrink-0 text-right">
                      <span className="text-xs text-teal-600">{Math.round(hit.score * 100)}%</span>
                      <time className="mt-1 block text-[10px] text-slate-600">
                        {formatRelative(hit.updated_at)}
                      </time>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
