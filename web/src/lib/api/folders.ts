import { apiClient } from "@/lib/api/client";
import type { Folder } from "@/lib/types";

export async function listFolders(): Promise<Folder[]> {
  return apiClient<Folder[]>("/folders");
}

export async function getFolder(id: string): Promise<Folder> {
  return apiClient<Folder>(`/folders/${id}`);
}

export async function createFolder(data: {
  name: string;
  parent_id?: string | null;
  kind?: string;
  description?: string;
}): Promise<Folder> {
  return apiClient<Folder>("/folders", { method: "POST", body: data });
}
