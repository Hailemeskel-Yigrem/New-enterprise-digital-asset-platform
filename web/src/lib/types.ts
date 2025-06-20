/** Domain types aligned with VaultForge backend schemas. */

export type DocumentStatus = "draft" | "active" | "archived" | "deleted";
export type VersionStatus = "pending" | "current" | "superseded";
export type SensitivityLabel = "public" | "internal" | "confidential" | "restricted";
export type FolderKind = "root" | "standard" | "shared" | "archive";
export type WorkflowStatus =
  | "draft"
  | "active"
  | "in_progress"
  | "completed"
  | "rejected"
  | "cancelled";
export type StepType = "approval" | "review" | "notification";
export type StepDecision = "pending" | "approved" | "rejected" | "skipped";
export type OrgRole = "owner" | "admin" | "editor" | "viewer";
export type MembershipStatus = "active" | "invited" | "suspended";
export type SignatureRequestStatus = "pending" | "in_progress" | "completed" | "declined" | "cancelled";
export type SignerStatus = "pending" | "signed" | "declined";
export type ActivityKind =
  | "document_created"
  | "document_updated"
  | "version_uploaded"
  | "folder_created";
export type ReportDimension = "user" | "folder" | "sensitivity";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_email_verified: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  plan_code: string;
  max_storage_gb: number;
  created_at: string;
  updated_at: string;
}

export interface Team {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  member_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface Membership {
  id: string;
  organization_id: string;
  user_id: string;
  role: OrgRole;
  status: MembershipStatus;
  created_at: string;
  updated_at: string;
}

export interface Folder {
  id: string;
  organization_id: string;
  name: string;
  parent_id: string | null;
  kind: FolderKind;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  checksum_sha256: string;
  content_type: string;
  size_bytes: number;
  status: VersionStatus;
  created_by: string;
  comment: string;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  organization_id: string;
  folder_id: string;
  name: string;
  status: DocumentStatus;
  sensitivity: SensitivityLabel;
  tags: string[];
  current_version_id: string | null;
  created_by: string;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
  current_version?: DocumentVersion | null;
}

export interface DocumentSearchResponse {
  items: Document[];
  total: number;
  limit: number;
  offset: number;
}

export interface WorkflowStep {
  id: string;
  workflow_id: string;
  order: number;
  name: string;
  step_type: StepType;
  assignee_id: string | null;
  required: boolean;
  created_at: string;
  updated_at: string;
}

export interface Workflow {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  status: WorkflowStatus;
  created_by: string;
  steps: WorkflowStep[];
  created_at: string;
  updated_at: string;
}

export interface StepInstance {
  id: string;
  instance_id: string;
  step_id: string;
  order: number;
  name: string;
  step_type: StepType;
  assignee_id: string;
  status: StepDecision;
  decided_by: string | null;
  decided_at: string | null;
  comment: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowInstance {
  id: string;
  organization_id: string;
  workflow_id: string;
  document_id: string;
  status: WorkflowStatus;
  current_step_order: number;
  started_by: string;
  completed_at: string | null;
  step_instances: StepInstance[];
  created_at: string;
  updated_at: string;
}

export interface Signer {
  id: string;
  request_id: string;
  user_id: string;
  order: number;
  status: SignerStatus;
  signature_hash: string | null;
  signed_at: string | null;
  declined_at: string | null;
  decline_reason: string;
  created_at: string;
  updated_at: string;
}

export interface SignatureRequest {
  id: string;
  organization_id: string;
  document_id: string;
  document_version_id: string;
  document_checksum: string;
  title: string;
  message: string;
  status: SignatureRequestStatus;
  created_by: string;
  completed_at: string | null;
  signers: Signer[];
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  id: string;
  organization_id: string;
  actor_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  metadata: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActivityItem {
  id: string;
  organization_id: string;
  user_id: string;
  activity_type: string;
  summary: string;
  resource_type: string;
  resource_id: string;
  audit_event_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActivityFeedResponse {
  items: ActivityItem[];
  total: number;
}

export interface DashboardStats {
  document_count: number;
  folder_count: number;
  pending_approvals: number;
  storage_used_bytes: number;
  storage_limit_bytes: number;
}

export interface RecentActivityItem {
  kind: ActivityKind;
  resource_id: string;
  resource_name: string;
  actor_id: string | null;
  occurred_at: string;
}

export interface DashboardResponse {
  stats: DashboardStats;
  recent_activity: RecentActivityItem[];
}

export interface ReportRow {
  key: string;
  label: string;
  document_count: number;
  storage_bytes: number;
}

export interface UsageReportResponse {
  organization_id: string;
  dimension: ReportDimension;
  rows: ReportRow[];
  generated_at: string;
}

export interface ApiError {
  detail: string | { msg: string; type: string }[];
}
