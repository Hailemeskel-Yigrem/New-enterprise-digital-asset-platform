"""Aggregate API v1 router."""

from __future__ import annotations

from fastapi import APIRouter

from vaultforge.api.v1 import (
    activity,
    admin,
    analytics,
    audit,
    auth,
    comments,
    documents,
    folders,
    jobs,
    notifications,
    oauth,
    organizations,
    previews,
    reports,
    retention,
    search,
    settings,
    shares,
    signatures,
    teams,
    users,
    workflows,
)

api_v1_router = APIRouter()
api_v1_router.include_router(auth.router)
api_v1_router.include_router(oauth.router)
api_v1_router.include_router(organizations.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(teams.router)
api_v1_router.include_router(folders.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(shares.router)
api_v1_router.include_router(retention.router)
api_v1_router.include_router(jobs.router)
api_v1_router.include_router(workflows.router)
api_v1_router.include_router(signatures.router)
api_v1_router.include_router(audit.router)
api_v1_router.include_router(activity.router)
api_v1_router.include_router(comments.router)
api_v1_router.include_router(notifications.router)
api_v1_router.include_router(analytics.router)
api_v1_router.include_router(reports.router)
api_v1_router.include_router(search.router)
api_v1_router.include_router(admin.router)
api_v1_router.include_router(settings.router)
api_v1_router.include_router(previews.router)
