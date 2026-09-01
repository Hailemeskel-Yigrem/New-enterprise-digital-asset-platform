"use client";

import { cn } from "@/lib/utils";
import type { Folder } from "@/lib/types";
import { Archive, ChevronRight, Folder as FolderIcon, FolderOpen, Share2 } from "lucide-react";
import { useMemo, useState } from "react";

function kindIcon(kind: Folder["kind"]) {
  switch (kind) {
    case "archive":
      return Archive;
    case "shared":
      return Share2;
    default:
      return FolderIcon;
  }
}

interface TreeNode extends Folder {
  children: TreeNode[];
}

function buildTree(folders: Folder[]): TreeNode[] {
  const map = new Map<string, TreeNode>();
  folders.forEach((f) => map.set(f.id, { ...f, children: [] }));
  const roots: TreeNode[] = [];
  map.forEach((node) => {
    if (node.parent_id && map.has(node.parent_id)) {
      map.get(node.parent_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  });
  return roots;
}

function TreeItem({ node, depth = 0 }: { node: TreeNode; depth?: number }) {
  const [open, setOpen] = useState(depth < 1);
  const hasChildren = node.children.length > 0;
  const Icon = open && hasChildren ? FolderOpen : kindIcon(node.kind);

  return (
    <div>
      <button
        type="button"
        onClick={() => hasChildren && setOpen(!open)}
        className={cn(
          "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-slate-300",
          "hover:bg-vault-800 hover:text-slate-100",
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {hasChildren ? (
          <ChevronRight
            className={cn("h-3.5 w-3.5 shrink-0 text-slate-500 transition-transform", open && "rotate-90")}
          />
        ) : (
          <span className="w-3.5 shrink-0" />
        )}
        <Icon className="h-4 w-4 shrink-0 text-teal-500/80" />
        <span className="truncate">{node.name}</span>
      </button>
      {open &&
        node.children.map((child) => (
          <TreeItem key={child.id} node={child} depth={depth + 1} />
        ))}
    </div>
  );
}

export function FolderTree({ folders }: { folders: Folder[] }) {
  const tree = useMemo(() => buildTree(folders), [folders]);

  if (folders.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-slate-500">No folders yet.</p>
    );
  }

  return (
    <div className="space-y-0.5">
      {tree.map((node) => (
        <TreeItem key={node.id} node={node} />
      ))}
    </div>
  );
}
