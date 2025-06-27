import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info";

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-vault-700 text-slate-200 ring-vault-600",
  success: "bg-emerald-950/60 text-emerald-300 ring-emerald-800/60",
  warning: "bg-amber-950/60 text-amber-300 ring-amber-800/60",
  danger: "bg-red-950/60 text-red-300 ring-red-800/60",
  info: "bg-cyan-950/60 text-cyan-300 ring-cyan-800/60",
};

export function Badge({
  children,
  variant = "default",
  className,
}: {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
