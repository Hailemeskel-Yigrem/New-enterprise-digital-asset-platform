import { apiClient } from "@/lib/api/client";
import { DEFAULT_ORG_ID, orgPath } from "@/lib/api/org";
import type { GlobalSearchHit, GlobalSearchResponse, SearchFilters } from "@/lib/types";

export interface GlobalSearchParams extends SearchFilters {
  query: string;
  limit?: number;
  offset?: number;
  resource_types?: string[];
  highlight?: boolean;
}

export async function globalSearch(
  params: GlobalSearchParams,
  orgId: string = DEFAULT_ORG_ID,
): Promise<GlobalSearchResponse> {
  const qs = new URLSearchParams();
  qs.set("q", params.query);
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  if (params.offset !== undefined) qs.set("offset", String(params.offset));
  if (params.resource_types?.length) qs.set("resource_types", params.resource_types.join(","));
  if (params.folder_id) qs.set("folder_id", params.folder_id);
  if (params.sensitivity?.length) qs.set("sensitivity", params.sensitivity.join(","));
  if (params.tags?.length) qs.set("tags", params.tags.join(","));
  if (params.date_from) qs.set("date_from", params.date_from);
  if (params.date_to) qs.set("date_to", params.date_to);
  if (params.highlight) qs.set("highlight", "true");
  return apiClient<GlobalSearchResponse>(
    `${orgPath(orgId, "/search")}?${qs.toString()}`,
  );
}

export async function searchSuggestions(
  query: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<string[]> {
  if (query.trim().length < 2) return [];
  return apiClient<string[]>(
    `${orgPath(orgId, "/search/suggestions")}?q=${encodeURIComponent(query)}`,
  );
}

export function highlightSnippet(hit: GlobalSearchHit): string {
  return hit.snippet.replace(/\*\*(.+?)\*\*/g, "<mark>$1</mark>");
}

export function groupHitsByType(
  hits: GlobalSearchHit[],
): Record<string, GlobalSearchHit[]> {
  return hits.reduce<Record<string, GlobalSearchHit[]>>((acc, hit) => {
    const list = acc[hit.resource_type] ?? [];
    list.push(hit);
    acc[hit.resource_type] = list;
    return acc;
  }, {});
}

export function buildSearchQueryString(params: GlobalSearchParams): string {
  const qs = new URLSearchParams();
  qs.set("q", params.query);
  if (params.resource_types?.length) qs.set("types", params.resource_types.join(","));
  return qs.toString();
}
