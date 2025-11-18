import { useEffect, useState } from "react";

/**
 * Returns a debounced copy of `value` that updates after `delayMs` of inactivity.
 */
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(handle);
  }, [value, delayMs]);

  return debounced;
}

/**
 * Debounced callback — invokes `fn` only after `delayMs` without new calls.
 */
export function useDebouncedCallback<T extends (...args: never[]) => void>(
  fn: T,
  delayMs = 300,
): T {
  const [timeoutId, setTimeoutId] = useState<number | null>(null);

  function debounced(...args: Parameters<T>) {
    if (timeoutId !== null) window.clearTimeout(timeoutId);
    const id = window.setTimeout(() => fn(...args), delayMs);
    setTimeoutId(id);
  }

  return debounced as T;
}
