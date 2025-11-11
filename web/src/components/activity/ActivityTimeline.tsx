"use client";

import { cn, formatRelative } from "@/lib/utils";
import type { ActivityItem, AuditEvent } from "@/lib/types";
import {
  FileText,
  FolderTree,
  GitBranch,
  PenLine,
  Share2,
  Upload,
  User,
} from "lucide-react";
import { useMemo } from "react";

type TimelineEvent = ActivityItem | AuditEvent;

interface ActivityTimelineProps {
  items: TimelineEvent[];
  isLoading?: boolean;
  className?: string;
  groupByDay?: boolean;
}

function eventIcon(type: string) {
  if (type.includes("document") || type.includes("version")) return FileText;
  if (type.includes("folder")) return FolderTree;
  if (type.includes("workflow")) return GitBranch;
  if (type.includes("signature")) return PenLine;
  if (type.includes("share")) return Share2;
  if (type.includes("upload")) return Upload;
  return User;
}

function eventSummary(item: TimelineEvent): string {
  if ("summary" in item) return item.summary;
  return `${item.action} on ${item.resource_type}`;
}

function eventTimestamp(item: TimelineEvent): string {
  return item.created_at;
}

export function ActivityTimeline({
  items,
  isLoading = false,
  className,
  groupByDay = true,
}: ActivityTimelineProps) {
  const grouped = useMemo(() => {
    if (!groupByDay) return { all: items };
    return items.reduce<Record<string, TimelineEvent[]>>((acc, item) => {
      const day = eventTimestamp(item).slice(0, 10);
      const list = acc[day] ?? [];
      list.push(item);
      acc[day] = list;
      return acc;
    }, {});
  }, [groupByDay, items]);

  if (isLoading) {
    return <p className="text-sm text-slate-500">Loading activity timeline…</p>;
  }

  if (items.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-vault-700 px-4 py-12 text-center text-sm text-slate-500">
        No activity to display.
      </p>
    );
  }

  return (
    <div className={cn("space-y-8", className)}>
      {Object.entries(grouped).map(([day, dayItems]) => (
        <section key={day}>
          {groupByDay && (
            <h3 className="mb-4 text-xs font-medium uppercase tracking-widest text-slate-500">
              {day}
            </h3>
          )}
          <ol className="relative space-y-0 border-l border-vault-800 pl-6">
            {dayItems.map((item) => {
              const type =
                "activity_type" in item ? item.activity_type : item.action;
              const Icon = eventIcon(type);
              return (
                <li key={item.id} className="relative pb-8 last:pb-0">
                  <span className="absolute -left-[1.65rem] flex h-7 w-7 items-center justify-center rounded-full border border-vault-700 bg-vault-900">
                    <Icon className="h-3.5 w-3.5 text-teal-500" />
                  </span>
                  <div className="rounded-lg border border-vault-800 bg-vault-900/40 px-4 py-3">
                    <p className="text-sm text-slate-200">{eventSummary(item)}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                      <span className="capitalize">{type.replace(/_/g, " ")}</span>
                      <span>·</span>
                      <span>{item.resource_type}</span>
                      <span>·</span>
                      <time>{formatRelative(eventTimestamp(item))}</time>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        </section>
      ))}
    </div>
  );
}
