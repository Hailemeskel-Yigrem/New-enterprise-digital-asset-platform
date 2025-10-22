import { apiClient } from "@/lib/api/client";
import { DEFAULT_ORG_ID, orgPath } from "@/lib/api/org";
import type { LegalHold, RetentionPolicy, RetentionSchedule } from "@/lib/types";

export interface CreateRetentionPolicyInput {
  name: string;
  description?: string;
  scope: "organization" | "folder" | "sensitivity" | "tag";
  scope_ref_id?: string | null;
  trigger: "created_at" | "last_accessed" | "last_modified";
  retention_days: number;
  action: "archive" | "delete" | "review";
  priority?: number;
}

export interface RetentionPolicyFilters {
  scope?: string;
  status?: string;
}

export interface RetentionScheduleFilters {
  policy_id?: string;
  resource_type?: string;
  resource_id?: string;
  pending_only?: boolean;
}

export async function listRetentionPolicies(
  params: RetentionPolicyFilters = {},
  orgId: string = DEFAULT_ORG_ID,
): Promise<RetentionPolicy[]> {
  const qs = new URLSearchParams();
  if (params.scope) qs.set("scope", params.scope);
  if (params.status) qs.set("status", params.status);
  const query = qs.toString();
  return apiClient<RetentionPolicy[]>(
    `${orgPath(orgId, "/retention/policies")}${query ? `?${query}` : ""}`,
  );
}

export async function getRetentionPolicy(
  policyId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<RetentionPolicy> {
  return apiClient<RetentionPolicy>(orgPath(orgId, `/retention/policies/${policyId}`));
}

export async function createRetentionPolicy(
  input: CreateRetentionPolicyInput,
  orgId: string = DEFAULT_ORG_ID,
): Promise<RetentionPolicy> {
  return apiClient<RetentionPolicy>(orgPath(orgId, "/retention/policies"), {
    method: "POST",
    body: input,
  });
}

export async function updateRetentionPolicy(
  policyId: string,
  patch: Partial<CreateRetentionPolicyInput>,
  orgId: string = DEFAULT_ORG_ID,
): Promise<RetentionPolicy> {
  return apiClient<RetentionPolicy>(orgPath(orgId, `/retention/policies/${policyId}`), {
    method: "PATCH",
    body: patch,
  });
}

export async function deactivateRetentionPolicy(
  policyId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<RetentionPolicy> {
  return apiClient<RetentionPolicy>(
    orgPath(orgId, `/retention/policies/${policyId}/deactivate`),
    { method: "POST" },
  );
}

export async function listRetentionSchedules(
  params: RetentionScheduleFilters = {},
  orgId: string = DEFAULT_ORG_ID,
): Promise<RetentionSchedule[]> {
  const qs = new URLSearchParams();
  if (params.policy_id) qs.set("policy_id", params.policy_id);
  if (params.resource_type) qs.set("resource_type", params.resource_type);
  if (params.resource_id) qs.set("resource_id", params.resource_id);
  if (params.pending_only) qs.set("pending_only", "true");
  const query = qs.toString();
  return apiClient<RetentionSchedule[]>(
    `${orgPath(orgId, "/retention/schedules")}${query ? `?${query}` : ""}`,
  );
}

export async function simulateRetention(
  policyId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<{ affected_count: number; sample_resource_ids: string[] }> {
  return apiClient<{ affected_count: number; sample_resource_ids: string[] }>(
    orgPath(orgId, `/retention/policies/${policyId}/simulate`),
    { method: "POST" },
  );
}

export async function listLegalHolds(orgId: string = DEFAULT_ORG_ID): Promise<LegalHold[]> {
  return apiClient<LegalHold[]>(orgPath(orgId, "/retention/legal-holds"));
}

export async function createLegalHold(
  input: {
    name: string;
    description?: string;
    matter_id: string;
    resource_ids?: string[];
    folder_ids?: string[];
    custodian_ids?: string[];
  },
  orgId: string = DEFAULT_ORG_ID,
): Promise<LegalHold> {
  return apiClient<LegalHold>(orgPath(orgId, "/retention/legal-holds"), {
    method: "POST",
    body: input,
  });
}

export async function releaseLegalHold(
  holdId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<LegalHold> {
  return apiClient<LegalHold>(orgPath(orgId, `/retention/legal-holds/${holdId}/release`), {
    method: "POST",
  });
}

export function formatRetentionAction(action: string): string {
  switch (action) {
    case "archive":
      return "Move to archive";
    case "delete":
      return "Permanent delete";
    case "review":
      return "Compliance review";
    default:
      return action;
  }
}

export function daysUntilExpiry(schedule: RetentionSchedule): number {
  const expires = new Date(schedule.expires_at).getTime();
  const now = Date.now();
  return Math.max(0, Math.ceil((expires - now) / (1000 * 60 * 60 * 24)));
}
