import { apiClient } from "@/lib/api/client";
import type { Workflow, WorkflowInstance } from "@/lib/types";

export async function listWorkflows(): Promise<Workflow[]> {
  return apiClient<Workflow[]>("/workflows");
}

export async function getWorkflowInstance(id: string): Promise<WorkflowInstance> {
  return apiClient<WorkflowInstance>(`/workflows/instances/${id}`);
}

export async function startWorkflowInstance(data: {
  workflow_id: string;
  document_id: string;
}): Promise<WorkflowInstance> {
  return apiClient<WorkflowInstance>("/workflows/instances", {
    method: "POST",
    body: data,
  });
}

export async function approveStep(instanceId: string, comment = ""): Promise<WorkflowInstance> {
  return apiClient<WorkflowInstance>(`/workflows/instances/${instanceId}/approve`, {
    method: "POST",
    body: { comment },
  });
}
