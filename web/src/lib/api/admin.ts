import { apiClient } from "@/lib/api/client";
import { DEFAULT_ORG_ID, orgPath } from "@/lib/api/org";
import type {
  AdminMemberSummary,
  AdminOrgOverview,
  AdminStorageBreakdown,
  MembershipStatus,
  OrgRole,
} from "@/lib/types";

export interface InviteMemberInput {
  email: string;
  role: OrgRole;
  full_name?: string;
}

export interface UpdateMemberInput {
  role?: OrgRole;
  status?: MembershipStatus;
}

export async function getAdminOverview(orgId: string = DEFAULT_ORG_ID): Promise<AdminOrgOverview> {
  return apiClient<AdminOrgOverview>(orgPath(orgId, "/admin/overview"));
}

export async function listAdminMembers(orgId: string = DEFAULT_ORG_ID): Promise<AdminMemberSummary[]> {
  return apiClient<AdminMemberSummary[]>(orgPath(orgId, "/admin/members"));
}

export async function inviteMember(
  input: InviteMemberInput,
  orgId: string = DEFAULT_ORG_ID,
): Promise<AdminMemberSummary> {
  return apiClient<AdminMemberSummary>(orgPath(orgId, "/admin/members/invite"), {
    method: "POST",
    body: input,
  });
}

export async function updateMember(
  membershipId: string,
  patch: UpdateMemberInput,
  orgId: string = DEFAULT_ORG_ID,
): Promise<AdminMemberSummary> {
  return apiClient<AdminMemberSummary>(orgPath(orgId, `/admin/members/${membershipId}`), {
    method: "PATCH",
    body: patch,
  });
}

export async function suspendMember(
  membershipId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<AdminMemberSummary> {
  return apiClient<AdminMemberSummary>(
    orgPath(orgId, `/admin/members/${membershipId}/suspend`),
    { method: "POST" },
  );
}

export async function getStorageBreakdown(
  orgId: string = DEFAULT_ORG_ID,
): Promise<AdminStorageBreakdown> {
  return apiClient<AdminStorageBreakdown>(orgPath(orgId, "/admin/storage"));
}

export async function exportAuditLog(
  params: { from?: string; to?: string; format?: "csv" | "json" } = {},
  orgId: string = DEFAULT_ORG_ID,
): Promise<Blob> {
  const qs = new URLSearchParams();
  if (params.from) qs.set("from", params.from);
  if (params.to) qs.set("to", params.to);
  if (params.format) qs.set("format", params.format);
  const query = qs.toString();
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}${orgPath(orgId, "/admin/audit/export")}${query ? `?${query}` : ""}`,
    { headers: { Authorization: `Bearer ${typeof window !== "undefined" ? localStorage.getItem("vf_access_token") ?? "" : ""}` } },
  );
  if (!response.ok) throw new Error("Audit export failed");
  return response.blob();
}

export function roleDescription(role: OrgRole): string {
  const descriptions: Record<OrgRole, string> = {
    owner: "Full control including billing and deletion",
    admin: "Manage members, policies, and organization settings",
    editor: "Create and edit documents and folders",
    viewer: "Read-only access to shared content",
  };
  return descriptions[role];
}
