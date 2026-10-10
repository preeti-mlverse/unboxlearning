"use client";
// Small data hooks: load something from the API, expose loading/error, and reload on demand.
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, get } from "./api";

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const tick = useRef(0);

  const load = useCallback(async (quiet = false) => {
    if (!path) return;
    const mine = ++tick.current;
    if (!quiet) setLoading(true);
    try {
      const d = await get<T>(path);
      if (mine === tick.current) { setData(d); setError(null); }
    } catch (e) {
      if (mine === tick.current) setError(e instanceof ApiError ? e : new ApiError(0, "ERROR", String(e)));
    } finally {
      if (mine === tick.current) setLoading(false);
    }
  }, [path]);

  useEffect(() => { load(); }, [load]);
  return { data, error, loading, reload: load, setData };
}

/** Poll while `active` is true (e.g. a document is still processing). */
export function usePoll(fn: () => void, active: boolean, ms = 2000) {
  useEffect(() => {
    if (!active) return;
    const id = setInterval(fn, ms);
    return () => clearInterval(id);
  }, [fn, active, ms]);
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  const units: [number, string][] = [[60, "minute"], [3600, "hour"], [86400, "day"], [2592000, "month"], [31536000, "year"]];
  let label = "";
  for (let i = units.length - 1; i >= 0; i--) {
    if (s >= units[i][0]) { const n = Math.floor(s / units[i][0]); label = `${n} ${units[i][1]}${n === 1 ? "" : "s"} ago`; break; }
  }
  return label;
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
