"use client";

import { Badge } from "@/components/ui/Badge";
import { cn, formatRelative } from "@/lib/utils";
import { signerStatusLabel } from "@/lib/api/signatures";
import type { Signer, SignatureRequest } from "@/lib/types";
import { CheckCircle2, Clock, UserX } from "lucide-react";

interface SignerListProps {
  request: SignatureRequest;
  currentUserId?: string;
  onRemind?: (signerId: string) => void;
  className?: string;
}

function statusIcon(status: Signer["status"]) {
  switch (status) {
    case "signed":
      return CheckCircle2;
    case "declined":
      return UserX;
    default:
      return Clock;
  }
}

function statusVariant(status: Signer["status"]): "success" | "warning" | "danger" {
  switch (status) {
    case "signed":
      return "success";
    case "declined":
      return "danger";
    default:
      return "warning";
  }
}

export function SignerList({ request, currentUserId, onRemind, className }: SignerListProps) {
  const ordered = [...request.signers].sort((a, b) => a.order - b.order);

  return (
    <ul className={cn("divide-y divide-vault-800 rounded-lg border border-vault-700", className)}>
      {ordered.map((signer, index) => {
        const Icon = statusIcon(signer.status);
        const isCurrent = signer.user_id === currentUserId;
        const isNext =
          signer.status === "pending" &&
          ordered.slice(0, index).every((s) => s.status === "signed");

        return (
          <li
            key={signer.id}
            className={cn(
              "flex items-center justify-between gap-4 px-4 py-3",
              isNext && "bg-teal-950/20 ring-1 ring-inset ring-teal-900/40",
            )}
          >
            <div className="flex items-center gap-3">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-vault-800 text-xs text-slate-400">
                {signer.order}
              </span>
              <div>
                <p className="text-sm text-slate-200">
                  <span className="font-mono text-slate-400">{signer.user_id.slice(0, 8)}</span>
                  {isCurrent && <span className="ml-2 text-teal-400">(you)</span>}
                </p>
                <p className="text-xs text-slate-500">{signerStatusLabel(signer.status)}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Icon
                className={cn(
                  "h-4 w-4",
                  signer.status === "signed" && "text-teal-400",
                  signer.status === "declined" && "text-red-400",
                  signer.status === "pending" && "text-slate-500",
                )}
              />
              <Badge variant={statusVariant(signer.status)}>{signer.status}</Badge>
              {signer.signed_at && (
                <time className="text-xs text-slate-600">{formatRelative(signer.signed_at)}</time>
              )}
              {signer.status === "pending" && onRemind && (
                <button
                  type="button"
                  onClick={() => onRemind(signer.id)}
                  className="text-xs text-teal-500 hover:text-teal-300"
                >
                  Remind
                </button>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
