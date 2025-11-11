"use client";

import { searchSuggestions } from "@/lib/api/search";
import { cn } from "@/lib/utils";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { Loader2, Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  className?: string;
}

export function SearchBar({
  value,
  onChange,
  onSubmit,
  placeholder = "Search documents, folders, workflows…",
  autoFocus = false,
  className,
}: SearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const debounced = useDebouncedValue(value, 300);

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  useEffect(() => {
    if (debounced.trim().length < 2) {
      setSuggestions([]);
      return;
    }
    let cancelled = false;
    setLoadingSuggestions(true);
    searchSuggestions(debounced)
      .then((items) => {
        if (!cancelled) setSuggestions(items);
      })
      .catch(() => {
        if (!cancelled) setSuggestions([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingSuggestions(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debounced]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setShowSuggestions(false);
    onSubmit(value.trim());
  }

  function selectSuggestion(suggestion: string) {
    onChange(suggestion);
    onSubmit(suggestion);
    setShowSuggestions(false);
  }

  return (
    <form onSubmit={handleSubmit} className={cn("relative", className)}>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input
          ref={inputRef}
          type="search"
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setShowSuggestions(true);
          }}
          onFocus={() => setShowSuggestions(true)}
          placeholder={placeholder}
          className="w-full rounded-lg border border-vault-700 bg-vault-950 py-3 pl-10 pr-10 text-sm text-slate-100 placeholder:text-slate-600 focus:border-teal-700 focus:outline-none focus:ring-1 focus:ring-teal-700/50"
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {showSuggestions && (suggestions.length > 0 || loadingSuggestions) && (
        <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-vault-700 bg-vault-900 shadow-xl">
          {loadingSuggestions && (
            <li className="flex items-center gap-2 px-4 py-2 text-xs text-slate-500">
              <Loader2 className="h-3 w-3 animate-spin" />
              Loading suggestions…
            </li>
          )}
          {suggestions.map((s) => (
            <li key={s}>
              <button
                type="button"
                onClick={() => selectSuggestion(s)}
                className="flex w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-vault-800 hover:text-teal-300"
              >
                {s}
              </button>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
