import { apiClient } from "@/lib/api/client";
import type { Document, DocumentSearchResponse, DocumentVersion } from "@/lib/types";

export interface DocumentSearchParams {
  name?: string;
  status?: string;
  folder_id?: string;
  tags?: string[];
  include_deleted?: boolean;
  limit?: number;
  offset?: number;
}

export async function searchDocuments(
  params: DocumentSearchParams = {},
): Promise<DocumentSearchResponse> {
  return apiClient<DocumentSearchResponse>("/documents/search", {
    method: "POST",
    body: params,
  });
}

export async function getDocument(id: string): Promise<Document> {
  return apiClient<Document>(`/documents/${id}`);
}

export async function uploadDocument(
  folderId: string,
  file: File,
  meta: { name: string; sensitivity?: string; tags?: string[]; comment?: string },
): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  form.append("folder_id", folderId);
  form.append("name", meta.name);
  if (meta.sensitivity) form.append("sensitivity", meta.sensitivity);
  if (meta.tags?.length) form.append("tags", JSON.stringify(meta.tags));
  if (meta.comment) form.append("comment", meta.comment);

  return apiClient<Document>("/documents", { method: "POST", body: form });
}

export async function getDocumentVersions(documentId: string): Promise<DocumentVersion[]> {
  const doc = await getDocument(documentId);
  if (doc.current_version) {
    return [doc.current_version];
  }
  return [];
}

export async function deleteDocument(id: string): Promise<Document> {
  return apiClient<Document>(`/documents/${id}`, { method: "DELETE" });
}
