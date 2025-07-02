"use client";

import { uploadDocument } from "@/lib/api/documents";
import { listFolders } from "@/lib/api/folders";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { useRef, useState } from "react";

interface UploadDialogProps {
  open: boolean;
  onClose: () => void;
}

export function UploadDialog({ open, onClose }: UploadDialogProps) {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [folderId, setFolderId] = useState("");
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const { data: folders = [] } = useQuery({
    queryKey: ["folders"],
    queryFn: listFolders,
    enabled: open,
  });

  const reset = () => {
    setFile(null);
    setName("");
    setFolderId("");
    setError("");
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSubmit = async () => {
    if (!file || !folderId) {
      setError("Select a file and destination folder.");
      return;
    }
    setIsUploading(true);
    setError("");
    try {
      await uploadDocument(folderId, file, {
        name: name || file.name,
        sensitivity: "internal",
      });
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      handleClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Upload document"
      description="Add a new file to your vault."
      footer={
        <>
          <Button variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} isLoading={isUploading}>
            Upload
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div
          className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-vault-600 bg-vault-950/50 px-6 py-8 transition-colors hover:border-teal-600/50"
          onClick={() => fileRef.current?.click()}
        >
          <Upload className="h-8 w-8 text-slate-500" />
          <p className="mt-2 text-sm text-slate-300">
            {file ? file.name : "Click to select a file"}
          </p>
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              setFile(f);
              if (f && !name) setName(f.name);
            }}
          />
        </div>
        <Input
          label="Display name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Document name"
        />
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-slate-300">Folder</label>
          <select
            value={folderId}
            onChange={(e) => setFolderId(e.target.value)}
            className="w-full rounded-md border border-vault-600 bg-vault-900 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500/40"
          >
            <option value="">Select folder…</option>
            {folders.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
      </div>
    </Modal>
  );
}
