import { apiClient } from "@/lib/api/client";
import { DEFAULT_ORG_ID, orgPath } from "@/lib/api/org";
import type { SignatureRequest, Signer, SignerStatus } from "@/lib/types";

export interface CreateSignatureRequestInput {
  document_id: string;
  document_version_id: string;
  title: string;
  message?: string;
  signers: Array<{ user_id: string; order: number }>;
}

export interface SignatureRequestFilters {
  status?: string;
  document_id?: string;
  created_by?: string;
}

export async function listSignatureRequests(
  params: SignatureRequestFilters = {},
  orgId: string = DEFAULT_ORG_ID,
): Promise<SignatureRequest[]> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.document_id) qs.set("document_id", params.document_id);
  if (params.created_by) qs.set("created_by", params.created_by);
  const query = qs.toString();
  return apiClient<SignatureRequest[]>(
    `${orgPath(orgId, "/signatures/requests")}${query ? `?${query}` : ""}`,
  );
}

export async function getSignatureRequest(
  requestId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<SignatureRequest> {
  return apiClient<SignatureRequest>(orgPath(orgId, `/signatures/requests/${requestId}`));
}

export async function createSignatureRequest(
  input: CreateSignatureRequestInput,
  orgId: string = DEFAULT_ORG_ID,
): Promise<SignatureRequest> {
  return apiClient<SignatureRequest>(orgPath(orgId, "/signatures/requests"), {
    method: "POST",
    body: input,
  });
}

export async function cancelSignatureRequest(
  requestId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<SignatureRequest> {
  return apiClient<SignatureRequest>(
    orgPath(orgId, `/signatures/requests/${requestId}/cancel`),
    { method: "POST" },
  );
}

export async function submitSignature(
  requestId: string,
  input: { signature_data: string; signature_hash: string },
  orgId: string = DEFAULT_ORG_ID,
): Promise<Signer> {
  return apiClient<Signer>(orgPath(orgId, `/signatures/requests/${requestId}/sign`), {
    method: "POST",
    body: input,
  });
}

export async function declineSignature(
  requestId: string,
  reason: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<Signer> {
  return apiClient<Signer>(orgPath(orgId, `/signatures/requests/${requestId}/decline`), {
    method: "POST",
    body: { reason },
  });
}

export async function remindSigners(
  requestId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<{ reminded: number }> {
  return apiClient<{ reminded: number }>(
    orgPath(orgId, `/signatures/requests/${requestId}/remind`),
    { method: "POST" },
  );
}

export function signerProgress(request: SignatureRequest): {
  signed: number;
  total: number;
  percent: number;
} {
  const total = request.signers.length;
  const signed = request.signers.filter((s) => s.status === "signed").length;
  return { signed, total, percent: total === 0 ? 0 : Math.round((signed / total) * 100) };
}

export function nextPendingSigner(request: SignatureRequest): Signer | null {
  return (
    request.signers
      .filter((s) => s.status === "pending")
      .sort((a, b) => a.order - b.order)[0] ?? null
  );
}

export function signerStatusLabel(status: SignerStatus): string {
  const labels: Record<SignerStatus, string> = {
    pending: "Awaiting signature",
    signed: "Signed",
    declined: "Declined",
  };
  return labels[status];
}
