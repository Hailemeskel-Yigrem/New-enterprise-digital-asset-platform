"use client";

import { cn, formatBytes } from "@/lib/utils";
import type { Document, DocumentVersion } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import {
  Download,
  Eye,
  FileText,
  Image,
  Lock,
  Maximize2,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useCallback, useState } from "react";

interface DocumentPreviewProps {
  document: Document;
  version?: DocumentVersion | null;
  previewUrl?: string | null;
  watermark?: boolean;
  className?: string;
  onDownload?: () => void;
  onFullscreen?: () => void;
}

function mimeIcon(contentType: string) {
  if (contentType.startsWith("image/")) return Image;
  if (contentType.includes("pdf")) return FileText;
  return FileText;
}

function sensitivityVariant(
  label: Document["sensitivity"],
): "info" | "warning" | "danger" | "success" {
  switch (label) {
    case "public":
      return "success";
    case "internal":
      return "info";
    case "confidential":
      return "warning";
    case "restricted":
      return "danger";
    default:
      return "info";
  }
}

export function DocumentPreview({
  document,
  version,
  previewUrl,
  watermark = false,
  className,
  onDownload,
  onFullscreen,
}: DocumentPreviewProps) {
  const active = version ?? document.current_version ?? null;
  const Icon = active ? mimeIcon(active.content_type) : FileText;
  const isRestricted =
    document.sensitivity === "restricted" || document.sensitivity === "confidential";
  const [zoom, setZoom] = useState(100);

  const handleZoomIn = useCallback(() => setZoom((z) => Math.min(z + 25, 200)), []);
  const handleZoomOut = useCallback(() => setZoom((z) => Math.max(z - 25, 50)), []);

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-lg border border-vault-700 bg-vault-900/60",
        className,
      )}
    >
      <div className="flex items-center justify-between border-b border-vault-800 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-vault-800">
            <Icon className="h-4 w-4 text-teal-400" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-200">{document.name}</p>
            {active && (
              <p className="text-xs text-slate-500">
                v{active.version_number} · {formatBytes(active.size_bytes)} · {active.content_type}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={sensitivityVariant(document.sensitivity)}>{document.sensitivity}</Badge>
          {isRestricted && (
            <span className="inline-flex items-center gap-1 rounded bg-amber-900/40 px-2 py-0.5 text-xs text-amber-200">
              <Lock className="h-3 w-3" />
              Protected
            </span>
          )}
          <div className="flex items-center rounded-md border border-vault-700">
            <button
              type="button"
              onClick={handleZoomOut}
              className="px-2 py-1 text-slate-400 hover:text-teal-300"
              title="Zoom out"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <span className="px-2 text-xs text-slate-500">{zoom}%</span>
            <button
              type="button"
              onClick={handleZoomIn}
              className="px-2 py-1 text-slate-400 hover:text-teal-300"
              title="Zoom in"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
          </div>
          <button
            type="button"
            onClick={onFullscreen}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-400 hover:bg-vault-800 hover:text-teal-300"
            title="Fullscreen"
          >
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-400 hover:bg-vault-800 hover:text-teal-300"
            title="Preview"
          >
            <Eye className="h-3.5 w-3.5" />
            Preview
          </button>
          <button
            type="button"
            onClick={onDownload}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-400 hover:bg-vault-800 hover:text-teal-300"
            title="Download"
          >
            <Download className="h-3.5 w-3.5" />
            Download
          </button>
        </div>
      </div>

      <div className="relative flex min-h-[320px] items-center justify-center bg-vault-950/80 p-6">
        {previewUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={previewUrl}
            alt={`Preview of ${document.name}`}
            style={{ transform: `scale(${zoom / 100})` }}
            className="max-h-[480px] max-w-full rounded shadow-lg shadow-black/30 transition-transform"
          />
        ) : (
          <div className="text-center">
            <FileText className="mx-auto h-16 w-16 text-slate-700" />
            <p className="mt-3 text-sm text-slate-500">Preview not generated yet</p>
            <p className="mt-1 text-xs text-slate-600">
              A thumbnail will appear after background processing completes.
            </p>
            {active && (
              <dl className="mx-auto mt-4 max-w-xs text-left text-xs text-slate-500">
                <div className="flex justify-between border-b border-vault-800 py-1">
                  <dt>Checksum</dt>
                  <dd className="font-mono text-slate-400">{active.checksum_sha256.slice(0, 12)}…</dd>
                </div>
                <div className="flex justify-between py-1">
                  <dt>Status</dt>
                  <dd className="capitalize text-slate-400">{active.status}</dd>
                </div>
              </dl>
            )}
          </div>
        )}
        {watermark && (
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-20"
          >
            <span className="rotate-[-24deg] font-serif text-4xl uppercase tracking-widest text-teal-300">
              VaultForge
            </span>
          </div>
        )}
      </div>

      {document.tags.length > 0 && (
        <footer className="flex flex-wrap gap-2 border-t border-vault-800 px-4 py-2">
          {document.tags.map((tag) => (
            <span key={tag} className="rounded bg-vault-800 px-2 py-0.5 text-xs text-slate-400">
              #{tag}
            </span>
          ))}
        </footer>
      )}
    </div>
  );
}
