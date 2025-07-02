"use client";

import { FolderTree } from "@/components/folders/FolderTree";
import { TopBar } from "@/components/layout/TopBar";
import { createFolder, listFolders } from "@/lib/api/folders";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderPlus } from "lucide-react";
import { useState } from "react";

export default function FoldersPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const { data: folders = [], isLoading, error } = useQuery({
    queryKey: ["folders"],
    queryFn: listFolders,
  });

  const createMutation = useMutation({
    mutationFn: () => createFolder({ name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["folders"] });
      setName("");
    },
  });

  return (
    <>
      <TopBar title="Folders" />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Input
              label="New folder"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Folder name"
            />
          </div>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={!name.trim()}
            isLoading={createMutation.isPending}
          >
            <FolderPlus className="h-4 w-4" />
            Create
          </Button>
        </div>
        {isLoading && <p className="text-sm text-slate-500">Loading folders…</p>}
        {error && (
          <p className="text-sm text-red-400">
            {error instanceof Error ? error.message : "Failed to load folders"}
          </p>
        )}
        <div className="rounded-lg border border-vault-700 bg-vault-900/40 p-4">
          <FolderTree folders={folders} />
        </div>
      </div>
    </>
  );
}
