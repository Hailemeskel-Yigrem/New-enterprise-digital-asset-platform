"use client";

import { TopBar } from "@/components/layout/TopBar";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  deleteNotification,
  groupNotificationsByDay,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  notificationIconType,
} from "@/lib/api/notifications";
import { formatRelative } from "@/lib/utils";
import type { Notification } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck, PenLine, Share2, Trash2, Workflow } from "lucide-react";
import { useState } from "react";

function NotificationIcon({ type }: { type: string }) {
  const kind = notificationIconType(type);
  const className = "h-4 w-4 text-teal-500";
  if (kind === "share") return <Share2 className={className} />;
  if (kind === "signature") return <PenLine className={className} />;
  if (kind === "workflow") return <Workflow className={className} />;
  return <Bell className={className} />;
}

function NotificationRow({
  notification,
  onRead,
  onDelete,
}: {
  notification: Notification;
  onRead: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const unread = !notification.read_at;
  return (
    <article
      className={
        unread
          ? "flex items-start justify-between gap-4 border-l-2 border-teal-600 bg-teal-950/10 px-4 py-4"
          : "flex items-start justify-between gap-4 px-4 py-4"
      }
    >
      <div className="flex gap-3">
        <NotificationIcon type={notification.notification_type} />
        <div>
          <p className="text-sm font-medium text-slate-200">{notification.title}</p>
          <p className="mt-0.5 text-sm text-slate-400">{notification.body}</p>
          <time className="mt-1 block text-xs text-slate-600">
            {formatRelative(notification.created_at)}
          </time>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {unread && <Badge variant="info">New</Badge>}
        {unread && (
          <button
            type="button"
            onClick={() => onRead(notification.id)}
            className="text-xs text-teal-500 hover:text-teal-300"
          >
            Mark read
          </button>
        )}
        <button
          type="button"
          onClick={() => onDelete(notification.id)}
          className="text-slate-600 hover:text-red-400"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </article>
  );
}

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const [unreadOnly, setUnreadOnly] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["notifications", unreadOnly],
    queryFn: () => listNotifications({ unread_only: unreadOnly, limit: 100 }),
  });

  const readMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const readAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteNotification,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const grouped = data ? groupNotificationsByDay(data.items) : new Map<string, Notification[]>();

  return (
    <>
      <TopBar title="Notifications" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Bell className="h-5 w-5 text-teal-500" />
            <p className="text-sm text-slate-400">
              {data ? `${data.unread_count} unread of ${data.total}` : "Your inbox"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setUnreadOnly((v) => !v)}
              className={
                unreadOnly
                  ? "rounded-md bg-teal-900/40 px-3 py-1.5 text-xs text-teal-300"
                  : "rounded-md bg-vault-800 px-3 py-1.5 text-xs text-slate-400"
              }
            >
              Unread only
            </button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => readAllMutation.mutate()}
              isLoading={readAllMutation.isPending}
              disabled={!data?.unread_count}
            >
              <CheckCheck className="h-4 w-4" />
              Mark all read
            </Button>
          </div>
        </div>

        {isLoading && <p className="text-sm text-slate-500">Loading notifications…</p>}
        {error && (
          <p className="text-sm text-red-400">
            {error instanceof Error ? error.message : "Failed to load notifications"}
          </p>
        )}

        {data && data.items.length === 0 && (
          <div className="rounded-lg border border-dashed border-vault-700 py-16 text-center">
            <Bell className="mx-auto h-10 w-10 text-slate-700" />
            <p className="mt-3 text-sm text-slate-500">No notifications</p>
          </div>
        )}

        <div className="space-y-8">
          {[...grouped.entries()].map(([day, items]) => (
            <section key={day}>
              <h3 className="mb-3 text-xs font-medium uppercase tracking-widest text-slate-500">
                {day}
              </h3>
              <div className="divide-y divide-vault-800 rounded-lg border border-vault-700">
                {items.map((n) => (
                  <NotificationRow
                    key={n.id}
                    notification={n}
                    onRead={(id) => readMutation.mutate(id)}
                    onDelete={(id) => deleteMutation.mutate(id)}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </>
  );
}
