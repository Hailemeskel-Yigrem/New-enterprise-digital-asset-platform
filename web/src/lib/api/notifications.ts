import { apiClient } from "@/lib/api/client";
import { DEFAULT_ORG_ID, orgPath } from "@/lib/api/org";
import type { Notification, NotificationListResponse } from "@/lib/types";

export interface NotificationFilters {
  unread_only?: boolean;
  notification_type?: string;
  limit?: number;
  offset?: number;
}

export async function listNotifications(
  params: NotificationFilters = {},
  orgId: string = DEFAULT_ORG_ID,
): Promise<NotificationListResponse> {
  const qs = new URLSearchParams();
  if (params.unread_only) qs.set("unread_only", "true");
  if (params.notification_type) qs.set("notification_type", params.notification_type);
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  if (params.offset !== undefined) qs.set("offset", String(params.offset));
  const query = qs.toString();
  return apiClient<NotificationListResponse>(
    `${orgPath(orgId, "/notifications")}${query ? `?${query}` : ""}`,
  );
}

export async function getNotification(
  notificationId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<Notification> {
  return apiClient<Notification>(orgPath(orgId, `/notifications/${notificationId}`));
}

export async function markNotificationRead(
  notificationId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<Notification> {
  return apiClient<Notification>(
    orgPath(orgId, `/notifications/${notificationId}/read`),
    { method: "POST" },
  );
}

export async function markAllNotificationsRead(
  orgId: string = DEFAULT_ORG_ID,
): Promise<{ updated: number }> {
  return apiClient<{ updated: number }>(orgPath(orgId, "/notifications/read-all"), {
    method: "POST",
  });
}

export async function deleteNotification(
  notificationId: string,
  orgId: string = DEFAULT_ORG_ID,
): Promise<void> {
  await apiClient<void>(orgPath(orgId, `/notifications/${notificationId}`), {
    method: "DELETE",
  });
}

export async function getUnreadCount(orgId: string = DEFAULT_ORG_ID): Promise<number> {
  const response = await listNotifications({ unread_only: true, limit: 1 }, orgId);
  return response.unread_count;
}

export function groupNotificationsByDay(
  notifications: Notification[],
): Map<string, Notification[]> {
  const groups = new Map<string, Notification[]>();
  for (const n of notifications) {
    const day = n.created_at.slice(0, 10);
    const list = groups.get(day) ?? [];
    list.push(n);
    groups.set(day, list);
  }
  return groups;
}

export function notificationIconType(type: string): "share" | "signature" | "workflow" | "system" {
  if (type.includes("share")) return "share";
  if (type.includes("signature")) return "signature";
  if (type.includes("workflow")) return "workflow";
  return "system";
}
