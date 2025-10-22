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

export type SharePermission = "view" | "comment" | "edit" | "download" | "share" | "delete" | "admin";
export type ShareResourceType = "document" | "folder" | "workflow" | "signature_request";
export type ShareStatus = "active" | "revoked" | "expired" | "pending";

export interface ShareGrant {
  id: string;
  organization_id: string;
  resource_type: ShareResourceType;
  resource_id: string;
  target_type: string;
  target_id: string | null;
  target_email: string | null;
  permission: SharePermission;
  granted_by: string;
  status: ShareStatus;
  expires_at: string | null;
  revoked_at: string | null;
  message: string;
  created_at: string;
  updated_at: string;
}

export interface ShareLink {
  id: string;
  organization_id: string;
  resource_type: ShareResourceType;
  resource_id: string;
  token: string;
  permission: SharePermission;
  created_by: string;
  status: ShareStatus;
  max_uses: number | null;
  use_count: number;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ShareInvitation {
  id: string;
  organization_id: string;
  resource_type: ShareResourceType;
  resource_id: string;
  email: string;
  permission: SharePermission;
  invited_by: string;
  status: ShareStatus;
  token: string;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccessControlEntry {
  id: string;
  organization_id: string;
  resource_type: ShareResourceType;
  resource_id: string;
  principal_type: string;
  principal_id: string;
  permission: SharePermission;
  effect: "allow" | "deny";
  inherited: boolean;
  source_folder_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ShareAccessCheck {
  allowed: boolean;
  permission: SharePermission;
  source: string;
}

export interface RetentionPolicy {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  scope: string;
  scope_ref_id: string | null;
  trigger: string;
  retention_days: number;
  action: string;
  status: string;
  created_by: string;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface RetentionSchedule {
  id: string;
  organization_id: string;
  policy_id: string;
  resource_type: string;
  resource_id: string;
  reference_time: string;
  expires_at: string;
  action: string;
  executed_at: string | null;
  blocked_by_legal_hold: boolean;
  created_at: string;
  updated_at: string;
}

export interface LegalHold {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  matter_id: string;
  status: string;
  created_by: string;
  released_by: string | null;
  released_at: string | null;
  resource_ids: string[];
  folder_ids: string[];
  custodian_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: string;
  organization_id: string;
  user_id: string;
  title: string;
  body: string;
  notification_type: string;
  resource_type: string | null;
  resource_id: string | null;
  read_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  unread_count: number;
}

export interface Comment {
  id: string;
  organization_id: string;
  resource_type: string;
  resource_id: string;
  author_id: string;
  body: string;
  parent_id: string | null;
  edited_at: string | null;
  deleted_at: string | null;
  mentions: Array<{ id: string; comment_id: string; user_id: string }>;
  created_at: string;
  updated_at: string;
}

export type SearchFacet = "document" | "folder" | "user" | "workflow";

export interface SearchFilters {
  resource_types?: string[];
  sensitivity?: SensitivityLabel[];
  folder_id?: string;
  tags?: string[];
  date_from?: string;
  date_to?: string;
}

export interface GlobalSearchHit {
  id: string;
  resource_type: string;
  title: string;
  snippet: string;
  score: number;
  metadata: Record<string, unknown>;
  updated_at: string;
}

export interface GlobalSearchResponse {
  query: string;
  hits: GlobalSearchHit[];
  total: number;
  limit: number;
  offset: number;
  took_ms: number;
}

export interface AdminMemberSummary {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: OrgRole;
  status: MembershipStatus;
  last_login_at: string | null;
}

export interface AdminOrgOverview {
  id: string;
  name: string;
  slug: string;
  plan_code: string;
  max_storage_gb: number;
  member_count: number;
  document_count: number;
}

export interface AdminStorageBreakdown {
  total_bytes: number;
  limit_bytes: number;
  by_sensitivity: Record<string, number>;
  by_folder: Array<{ folder_id: string; name: string; bytes: number }>;
}
