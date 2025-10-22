import { apiClient } from "@/lib/api/client";
import { DEFAULT_ORG_ID, orgPath } from "@/lib/api/org";
import type {
  AccessControlEntry,
  ShareAccessCheck,
  ShareGrant,
  ShareInvitation,
  ShareLink,
  SharePermission,
  ShareResourceType,
  ShareStatus,
} from "@/lib/types";

export interface CreateShareGrantInput {
  resource_type: ShareResourceType;
  resource_id: string;
  target_type: "user" | "team" | "external_email" | "organization";
  target_id?: string;
  target_email?: string;
  permission?: SharePermission;
  expires_at?: string | null;
  message?: string;
}

export interface CreateShareLinkInput {
  resource_type: ShareResourceType;
  resource_id: string;
  permission?: SharePermission;
  password?: string;
  max_uses?: number;
  expires_at?: string | null;
}

export interface ShareGrantFilters {
  resource_type?: ShareResourceType;
  resource_id?: string;
  status?: ShareStatus;
  target_email?: string;
}

export interface BatchRevokeResult {
  revoked: number;
  grant_ids: string[];
}

const PERMISSION_RANK: Record<SharePermission, number> = {
  view: 1,
  comment: 2,
  download: 3,
  edit: 4,
  share: 5,
  delete: 6,
  admin: 7,
};

export function compareSharePermissions(a: SharePermission, b: SharePermission): number {
  return PERMISSION_RANK[a] - PERMISSION_RANK[b];
}

export function strongestGrantPermission(grants: ShareGrant[]): SharePermission | null {
  const active = grants.filter((g) => g.status === "active");
  if (active.length === 0) return null;
  return active.reduce(
    (best, g) => (compareSharePermissions(g.permission, best) > 0 ? g.permission : best),
    active[0].permission,
  );
}

function buildGrantQuery(params: ShareGrantFilters): string {
  const qs = new URLSearchParams();
  if (params.resource_type) qs.set("resource_type", params.resource_type);
  if (params.resource_id) qs.set("resource_id", params.resource_id);
  if (params.status) qs.set("status", params.status);
  if (params.target_email) qs.set("target_email", params.target_email);
  const query = qs.toString();
  return query ? `?${query}` : "";
}

export async function listShareGrants(
  orgId: string = DEFAULT_ORG_ID,
  params: ShareGrantFilters = {},
): Promise<ShareGrant[]> {
  return apiClient<ShareGrant[]>(
    `${orgPath(orgId, "/shares/grants")}${buildGrantQuery(params)}`,
  );
}

export async function getShareGrant(
  grantId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<ShareGrant> {
  return apiClient<ShareGrant>(orgPath(orgId, `/shares/grants/${grantId}`));
}

export async function createShareGrant(
  input: CreateShareGrantInput,
  orgId: string = DEFAULT_ORG_ID,
): Promise<ShareGrant> {
  return apiClient<ShareGrant>(orgPath(orgId, "/shares/grants"), {
    method: "POST",
    body: input,
  });
}

export async function updateShareGrant(
  grantId: string,
  patch: Partial<Pick<CreateShareGrantInput, "permission" | "expires_at" | "message">>,
  orgId: string = DEFAULT_ORG_ID,
): Promise<ShareGrant> {
  return apiClient<ShareGrant>(orgPath(orgId, `/shares/grants/${grantId}`), {
    method: "PATCH",
    body: patch,
  });
}

export async function revokeShareGrant(
  grantId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<ShareGrant> {
  return apiClient<ShareGrant>(orgPath(orgId, `/shares/grants/${grantId}/revoke`), {
    method: "POST",
  });
}

export async function batchRevokeShareGrants(
  grantIds: string[],
  orgId: string = DEFAULT_ORG_ID,
): Promise<BatchRevokeResult> {
  return apiClient<BatchRevokeResult>(orgPath(orgId, "/shares/grants/batch-revoke"), {
    method: "POST",
    body: { grant_ids: grantIds },
  });
}

export async function createShareLink(
  input: CreateShareLinkInput,
  orgId: string = DEFAULT_ORG_ID,
): Promise<ShareLink> {
  return apiClient<ShareLink>(orgPath(orgId, "/shares/links"), {
    method: "POST",
    body: input,
  });
}

export async function listShareLinks(
  orgId: string = DEFAULT_ORG_ID,
  resourceId?: string,
): Promise<ShareLink[]> {
  const qs = resourceId ? `?resource_id=${resourceId}` : "";
  return apiClient<ShareLink[]>(`${orgPath(orgId, "/shares/links")}${qs}`);
}

export async function revokeShareLink(
  linkId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<ShareLink> {
  return apiClient<ShareLink>(orgPath(orgId, `/shares/links/${linkId}/revoke`), {
    method: "POST",
  });
}

export async function createShareInvitation(
  input: {
    resource_type: ShareResourceType;
    resource_id: string;
    email: string;
    permission?: SharePermission;
    expires_at?: string | null;
    message?: string;
  },
  orgId: string = DEFAULT_ORG_ID,
): Promise<ShareInvitation> {
  return apiClient<ShareInvitation>(orgPath(orgId, "/shares/invitations"), {
    method: "POST",
    body: input,
  });
}

export async function listShareInvitations(
  orgId: string = DEFAULT_ORG_ID,
  resourceId?: string,
): Promise<ShareInvitation[]> {
  const qs = resourceId ? `?resource_id=${resourceId}` : "";
  return apiClient<ShareInvitation[]>(`${orgPath(orgId, "/shares/invitations")}${qs}`);
}

export async function acceptShareInvitation(
  token: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<ShareGrant> {
  return apiClient<ShareGrant>(orgPath(orgId, "/shares/invitations/accept"), {
    method: "POST",
    body: { token },
  });
}

export async function getResourceAcl(
  resourceType: ShareResourceType,
  resourceId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<AccessControlEntry[]> {
  return apiClient<AccessControlEntry[]>(
    orgPath(orgId, `/shares/acl/${resourceType}/${resourceId}`),
  );
}

export async function replaceResourceAcl(
  resourceType: ShareResourceType,
  resourceId: string,
  entries: Array<{
    principal_type: string;
    principal_id: string;
    permission: SharePermission;
    effect: "allow" | "deny";
  }>,
  orgId: string = DEFAULT_ORG_ID,
): Promise<AccessControlEntry[]> {
  return apiClient<AccessControlEntry[]>(
    orgPath(orgId, `/shares/acl/${resourceType}/${resourceId}`),
    { method: "PUT", body: { entries } },
  );
}

export async function checkShareAccess(
  input: {
    resource_type: ShareResourceType;
    resource_id: string;
    permission: SharePermission;
    token?: string;
  },
  orgId: string = DEFAULT_ORG_ID,
): Promise<ShareAccessCheck> {
  return apiClient<ShareAccessCheck>(orgPath(orgId, "/shares/access-check"), {
    method: "POST",
    body: input,
  });
}

export async function previewShareAccessMatrix(
  resourceType: ShareResourceType,
  resourceId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<Record<SharePermission, boolean>> {
  const permissions: SharePermission[] = [
    "view",
    "comment",
    "download",
    "edit",
    "share",
    "delete",
    "admin",
  ];
  const results = await Promise.all(
    permissions.map(async (permission) => {
      const check = await checkShareAccess(
        { resource_type: resourceType, resource_id: resourceId, permission },
        orgId,
      );
      return [permission, check.allowed] as const;
    }),
  );
  return Object.fromEntries(results) as Record<SharePermission, boolean>;
}
