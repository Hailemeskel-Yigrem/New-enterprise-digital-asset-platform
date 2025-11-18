import { createFolder, listFolders } from "@/lib/api/folders";
import type { Folder } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";

export function useFolders(enabled = true) {
  return useQuery<Folder[]>({
    queryKey: ["folders"],
    queryFn: listFolders,
    enabled,
    staleTime: 60_000,
  });
}

export function useFolderTree() {
  const { data: folders = [], ...rest } = useFolders();
  const tree = useMemo(() => buildFolderTree(folders), [folders]);
  return { folders, tree, ...rest };
}

export function useCreateFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createFolder,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["folders"] }),
  });
}

export interface FolderTreeNode extends Folder {
  children: FolderTreeNode[];
}

export function buildFolderTree(folders: Folder[]): FolderTreeNode[] {
  const map = new Map<string, FolderTreeNode>();
  for (const f of folders) {
    map.set(f.id, { ...f, children: [] });
  }
  const roots: FolderTreeNode[] = [];
  for (const node of map.values()) {
    if (node.parent_id && map.has(node.parent_id)) {
      map.get(node.parent_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  }
  return roots;
}
