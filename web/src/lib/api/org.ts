/** Default organization scope for org-prefixed API routes. */

export const DEFAULT_ORG_ID =
  process.env.NEXT_PUBLIC_ORG_ID ?? "00000000-0000-0000-0000-000000000001";

export function orgPath(orgId: string, suffix: string): string {
  const normalized = suffix.startsWith("/") ? suffix : `/${suffix}`;
  return `/organizations/${orgId}${normalized}`;
}
