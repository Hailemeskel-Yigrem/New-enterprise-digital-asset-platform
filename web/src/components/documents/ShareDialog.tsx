"use client";

import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import {
  batchRevokeShareGrants,
  createShareGrant,
  createShareLink,
  listShareGrants,
  previewShareAccessMatrix,
  revokeShareGrant,
} from "@/lib/api/shares";
import type { Document, ShareGrant, ShareLink, SharePermission } from "@/lib/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Link2, Mail, Shield, Trash2, Users } from "lucide-react";
import { useState } from "react";

interface ShareDialogProps {
  open: boolean;
  onClose: () => void;
  document: Document;
}

const PERMISSIONS: SharePermission[] = ["view", "comment", "download", "edit", "share"];

export function ShareDialog({ open, onClose, document }: ShareDialogProps) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [permission, setPermission] = useState<SharePermission>("view");
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [selectedGrants, setSelectedGrants] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState<"invite" | "link" | "acl">("invite");

  const { data: grants = [], isLoading } = useQuery({
    queryKey: ["share-grants", document.id],
    queryFn: () =>
      listShareGrants(undefined, {
        resource_type: "document",
        resource_id: document.id,
      }),
    enabled: open,
  });

  const { data: accessMatrix } = useQuery({
    queryKey: ["share-matrix", document.id],
    queryFn: () => previewShareAccessMatrix("document", document.id),
    enabled: open && activeTab === "acl",
  });

  const inviteMutation = useMutation({
    mutationFn: () =>
      createShareGrant({
        resource_type: "document",
        resource_id: document.id,
        target_type: "external_email",
        target_email: email,
        permission,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["share-grants", document.id] });
      setEmail("");
    },
  });

  const linkMutation = useMutation({
    mutationFn: () =>
      createShareLink({
        resource_type: "document",
        resource_id: document.id,
        permission,
        max_uses: 50,
      }),
    onSuccess: (link: ShareLink) => setLinkToken(link.token),
  });

  const revokeMutation = useMutation({
    mutationFn: (grantId: string) => revokeShareGrant(grantId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["share-grants", document.id] }),
  });

  const batchRevokeMutation = useMutation({
    mutationFn: (ids: string[]) => batchRevokeShareGrants(ids),
    onSuccess: () => {
      setSelectedGrants(new Set());
      queryClient.invalidateQueries({ queryKey: ["share-grants", document.id] });
    },
  });

  async function handleCopyLink() {
    if (!linkToken) return;
    const url = `${window.location.origin}/shared/${linkToken}`;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  function toggleGrant(id: string) {
    setSelectedGrants((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Share document"
      description={`Manage access to ${document.name}`}
      size="lg"
      footer={
        <Button variant="secondary" onClick={onClose}>
          Done
        </Button>
      }
    >
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Badge variant="info">{document.sensitivity}</Badge>
          <Badge variant="warning">{document.status}</Badge>
        </div>

        <nav className="flex gap-1 rounded-lg border border-vault-800 bg-vault-950 p-1">
          {(["invite", "link", "acl"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={
                activeTab === tab
                  ? "flex-1 rounded-md bg-vault-800 py-2 text-xs capitalize text-teal-300"
                  : "flex-1 rounded-md py-2 text-xs capitalize text-slate-500 hover:text-slate-300"
              }
            >
              {tab === "acl" ? "Access matrix" : tab}
            </button>
          ))}
        </nav>

        {activeTab === "invite" && (
          <section>
            <h4 className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-300">
              <Mail className="h-4 w-4 text-teal-500" />
              Invite by email
            </h4>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1">
                <Input
                  label="Email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="colleague@company.com"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-500">Permission</label>
                <select
                  value={permission}
                  onChange={(e) => setPermission(e.target.value as SharePermission)}
                  className="h-10 rounded-md border border-vault-700 bg-vault-900 px-3 text-sm text-slate-200"
                >
                  {PERMISSIONS.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
              <Button
                onClick={() => inviteMutation.mutate()}
                disabled={!email.trim()}
                isLoading={inviteMutation.isPending}
              >
                Invite
              </Button>
            </div>
          </section>
        )}

        {activeTab === "link" && (
          <section>
            <h4 className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-300">
              <Link2 className="h-4 w-4 text-teal-500" />
              Public link
            </h4>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="secondary"
                onClick={() => linkMutation.mutate()}
                isLoading={linkMutation.isPending}
              >
                Generate link
              </Button>
              {linkToken && (
                <Button variant="ghost" size="sm" onClick={handleCopyLink}>
                  <Copy className="h-4 w-4" />
                  {copied ? "Copied" : "Copy link"}
                </Button>
              )}
            </div>
            {linkToken && (
              <p className="mt-2 break-all font-mono text-xs text-slate-500">{linkToken}</p>
            )}
          </section>
        )}

        {activeTab === "acl" && accessMatrix && (
          <section className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {Object.entries(accessMatrix).map(([perm, allowed]) => (
              <div
                key={perm}
                className={
                  allowed
                    ? "rounded-md border border-teal-900/50 bg-teal-950/30 px-3 py-2 text-center text-xs text-teal-300"
                    : "rounded-md border border-vault-800 bg-vault-950 px-3 py-2 text-center text-xs text-slate-600"
                }
              >
                {perm}
              </div>
            ))}
          </section>
        )}

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h4 className="flex items-center gap-2 text-sm font-medium text-slate-300">
              <Users className="h-4 w-4 text-teal-500" />
              Active grants ({grants.length})
            </h4>
            {selectedGrants.size > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => batchRevokeMutation.mutate([...selectedGrants])}
                isLoading={batchRevokeMutation.isPending}
              >
                <Trash2 className="h-3.5 w-3.5" />
                Revoke selected
              </Button>
            )}
          </div>
          {isLoading && <p className="text-sm text-slate-500">Loading shares…</p>}
          {!isLoading && grants.length === 0 && (
            <p className="text-sm text-slate-500">No active share grants.</p>
          )}
          <ul className="divide-y divide-vault-800 rounded-md border border-vault-700">
            {grants.map((grant: ShareGrant) => (
              <li key={grant.id} className="flex items-center justify-between px-3 py-2 text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={selectedGrants.has(grant.id)}
                    onChange={() => toggleGrant(grant.id)}
                    className="rounded border-vault-600"
                  />
                  <span className="text-slate-300">
                    {grant.target_email ?? grant.target_id?.slice(0, 8) ?? "Unknown"}
                  </span>
                </label>
                <div className="flex items-center gap-2">
                  <Badge variant="info">{grant.permission}</Badge>
                  <Badge variant={grant.status === "active" ? "success" : "warning"}>
                    {grant.status}
                  </Badge>
                  {grant.status === "active" && (
                    <button
                      type="button"
                      onClick={() => revokeMutation.mutate(grant.id)}
                      className="text-xs text-slate-500 hover:text-red-400"
                    >
                      Revoke
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-md border border-vault-800 bg-vault-950/50 px-3 py-2">
          <p className="flex items-center gap-2 text-xs text-slate-500">
            <Shield className="h-3.5 w-3.5" />
            Shares inherit organization retention and audit policies.
          </p>
        </section>
      </div>
    </Modal>
  );
}
