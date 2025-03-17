"""Identity enumerations."""

from __future__ import annotations

from enum import StrEnum


class OrgRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"
    AUDITOR = "auditor"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class Permission(StrEnum):
    ORG_MANAGE = "org:manage"
    USER_MANAGE = "user:manage"
    TEAM_MANAGE = "team:manage"
    FOLDER_CREATE = "folder:create"
    FOLDER_MANAGE = "folder:manage"
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_SHARE = "document:share"
    WORKFLOW_MANAGE = "workflow:manage"
    WORKFLOW_APPROVE = "workflow:approve"
    SIGNATURE_REQUEST = "signature:request"
    SIGNATURE_SIGN = "signature:sign"
    AUDIT_READ = "audit:read"
    REPORT_READ = "report:read"
    SETTINGS_MANAGE = "settings:manage"


ROLE_PERMISSIONS: dict[OrgRole, frozenset[Permission]] = {
    OrgRole.OWNER: frozenset(Permission),
    OrgRole.ADMIN: frozenset(
        {
            Permission.ORG_MANAGE,
            Permission.USER_MANAGE,
            Permission.TEAM_MANAGE,
            Permission.FOLDER_CREATE,
            Permission.FOLDER_MANAGE,
            Permission.DOCUMENT_UPLOAD,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_DELETE,
            Permission.DOCUMENT_SHARE,
            Permission.WORKFLOW_MANAGE,
            Permission.WORKFLOW_APPROVE,
            Permission.SIGNATURE_REQUEST,
            Permission.SIGNATURE_SIGN,
            Permission.AUDIT_READ,
            Permission.REPORT_READ,
            Permission.SETTINGS_MANAGE,
        }
    ),
    OrgRole.MANAGER: frozenset(
        {
            Permission.TEAM_MANAGE,
            Permission.FOLDER_CREATE,
            Permission.FOLDER_MANAGE,
            Permission.DOCUMENT_UPLOAD,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_SHARE,
            Permission.WORKFLOW_MANAGE,
            Permission.WORKFLOW_APPROVE,
            Permission.SIGNATURE_REQUEST,
            Permission.SIGNATURE_SIGN,
            Permission.REPORT_READ,
        }
    ),
    OrgRole.CONTRIBUTOR: frozenset(
        {
            Permission.FOLDER_CREATE,
            Permission.DOCUMENT_UPLOAD,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPDATE,
            Permission.SIGNATURE_SIGN,
            Permission.WORKFLOW_APPROVE,
        }
    ),
    OrgRole.VIEWER: frozenset({Permission.DOCUMENT_READ}),
    OrgRole.AUDITOR: frozenset(
        {
            Permission.DOCUMENT_READ,
            Permission.AUDIT_READ,
            Permission.REPORT_READ,
        }
    ),
}
