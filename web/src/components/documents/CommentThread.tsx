"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { cn, formatRelative } from "@/lib/utils";
import type { Comment } from "@/lib/types";
import { MessageSquare, MoreHorizontal, Reply, Send, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

interface CommentThreadProps {
  comments: Comment[];
  currentUserId?: string;
  onSubmit?: (body: string, parentId?: string | null) => Promise<void> | void;
  onDelete?: (commentId: string) => Promise<void> | void;
  isLoading?: boolean;
  className?: string;
}

function CommentItem({
  comment,
  depth,
  currentUserId,
  onReply,
  onDelete,
}: {
  comment: Comment;
  depth: number;
  currentUserId?: string;
  onReply: (id: string) => void;
  onDelete?: (id: string) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const isAuthor = currentUserId === comment.author_id;

  return (
    <article
      className={cn(
        "group rounded-md border border-vault-800 bg-vault-900/40 p-4",
        depth > 0 && "ml-6 mt-3 border-l-2 border-l-teal-900/50",
      )}
    >
      <header className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs text-slate-500">
          Author{" "}
          <span className="font-mono text-slate-400">{comment.author_id.slice(0, 8)}</span>
          {isAuthor && <span className="ml-2 text-teal-500">(you)</span>}
        </p>
        <div className="flex items-center gap-2">
          <time className="text-xs text-slate-600">{formatRelative(comment.created_at)}</time>
          {isAuthor && onDelete && (
            <div className="relative">
              <button
                type="button"
                onClick={() => setMenuOpen((o) => !o)}
                className="rounded p-1 text-slate-600 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-vault-800 hover:text-slate-300"
              >
                <MoreHorizontal className="h-3.5 w-3.5" />
              </button>
              {menuOpen && (
                <div className="absolute right-0 z-10 mt-1 w-32 rounded-md border border-vault-700 bg-vault-900 py-1 shadow-lg">
                  <button
                    type="button"
                    onClick={() => {
                      onDelete(comment.id);
                      setMenuOpen(false);
                    }}
                    className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-red-400 hover:bg-vault-800"
                  >
                    <Trash2 className="h-3 w-3" />
                    Delete
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </header>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200">{comment.body}</p>
      {comment.mentions.length > 0 && (
        <p className="mt-2 text-xs text-teal-500/80">
          {comment.mentions.length} mention{comment.mentions.length !== 1 ? "s" : ""}
        </p>
      )}
      {comment.edited_at && (
        <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-600">Edited</p>
      )}
      <footer className="mt-3">
        <button
          type="button"
          onClick={() => onReply(comment.id)}
          className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-teal-300"
        >
          <Reply className="h-3 w-3" />
          Reply
        </button>
      </footer>
    </article>
  );
}

export function CommentThread({
  comments,
  currentUserId,
  onSubmit,
  onDelete,
  isLoading = false,
  className,
}: CommentThreadProps) {
  const [draft, setDraft] = useState("");
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [sortNewest, setSortNewest] = useState(true);

  const roots = useMemo(() => {
    const filtered = comments.filter((c) => !c.parent_id && !c.deleted_at);
    return [...filtered].sort((a, b) =>
      sortNewest
        ? new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        : new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    );
  }, [comments, sortNewest]);

  const repliesByParent = useMemo(() => {
    const map = new Map<string, Comment[]>();
    for (const c of comments) {
      if (!c.parent_id || c.deleted_at) continue;
      const list = map.get(c.parent_id) ?? [];
      list.push(c);
      map.set(c.parent_id, list);
    }
    return map;
  }, [comments]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim() || !onSubmit) return;
    setSubmitting(true);
    try {
      await onSubmit(draft.trim(), replyTo);
      setDraft("");
      setReplyTo(null);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className={cn("space-y-4", className)}>
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-serif text-lg text-slate-200">
          <MessageSquare className="h-5 w-5 text-teal-500" />
          Comments
          <span className="text-sm font-normal text-slate-500">({comments.length})</span>
        </h3>
        <button
          type="button"
          onClick={() => setSortNewest((v) => !v)}
          className="text-xs text-slate-500 hover:text-teal-300"
        >
          Sort {sortNewest ? "newest" : "oldest"}
        </button>
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading comments…</p>}

      {!isLoading && roots.length === 0 && (
        <p className="rounded-lg border border-dashed border-vault-700 px-4 py-8 text-center text-sm text-slate-500">
          No comments yet. Start the conversation below.
        </p>
      )}

      <div className="space-y-4">
        {roots.map((comment) => (
          <div key={comment.id}>
            <CommentItem
              comment={comment}
              depth={0}
              currentUserId={currentUserId}
              onReply={setReplyTo}
              onDelete={onDelete}
            />
            {(repliesByParent.get(comment.id) ?? []).map((reply) => (
              <CommentItem
                key={reply.id}
                comment={reply}
                depth={1}
                currentUserId={currentUserId}
                onReply={setReplyTo}
                onDelete={onDelete}
              />
            ))}
          </div>
        ))}
      </div>

      {onSubmit && (
        <form onSubmit={handleSubmit} className="rounded-lg border border-vault-700 bg-vault-900/50 p-4">
          {replyTo && (
            <p className="mb-2 text-xs text-teal-400">
              Replying to thread ·{" "}
              <button type="button" className="underline" onClick={() => setReplyTo(null)}>
                cancel
              </button>
            </p>
          )}
          <Input
            label="Add comment"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Write a comment… Use @[Name](user-id) for mentions"
          />
          <div className="mt-3 flex justify-end">
            <Button type="submit" disabled={!draft.trim()} isLoading={submitting}>
              <Send className="h-4 w-4" />
              Post
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}
