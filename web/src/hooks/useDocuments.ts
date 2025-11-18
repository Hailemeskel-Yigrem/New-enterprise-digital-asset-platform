import {
  deleteDocument,
  getDocument,
  getDocumentVersions,
  searchDocuments,
} from "@/lib/api/documents";
import type { Document, DocumentSearchResponse, DocumentVersion } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface UseDocumentsOptions {
  folderId?: string;
  status?: string;
  tags?: string[];
  limit?: number;
  offset?: number;
  enabled?: boolean;
}

export function documentsQueryKey(options: UseDocumentsOptions = {}) {
  return ["documents", options] as const;
}

export function useDocuments(options: UseDocumentsOptions = {}) {
  const { folderId, status, tags, limit = 50, offset = 0, enabled = true } = options;
  return useQuery<DocumentSearchResponse>({
    queryKey: documentsQueryKey({ folderId, status, tags, limit, offset }),
    queryFn: () =>
      searchDocuments({
        folder_id: folderId,
        status,
        tags,
        limit,
        offset,
      }),
    enabled,
    staleTime: 30_000,
  });
}

export function useDocument(documentId: string | undefined) {
  return useQuery<Document>({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId!),
    enabled: Boolean(documentId),
  });
}

export function useDocumentVersions(documentId: string | undefined) {
  return useQuery<DocumentVersion[]>({
    queryKey: ["document-versions", documentId],
    queryFn: () => getDocumentVersions(documentId!),
    enabled: Boolean(documentId),
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => deleteDocument(documentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });
}
