import { Badge } from "@/components/ui/Badge";
import type { WorkflowStatus } from "@/lib/types";

const config: Record<WorkflowStatus, { label: string; variant: "default" | "success" | "warning" | "danger" | "info" }> = {
  draft: { label: "Draft", variant: "default" },
  active: { label: "Active", variant: "info" },
  in_progress: { label: "In progress", variant: "warning" },
  completed: { label: "Completed", variant: "success" },
  rejected: { label: "Rejected", variant: "danger" },
  cancelled: { label: "Cancelled", variant: "default" },
};

export function WorkflowStatusBadge({ status }: { status: WorkflowStatus }) {
  const { label, variant } = config[status];
  return <Badge variant={variant}>{label}</Badge>;
}
