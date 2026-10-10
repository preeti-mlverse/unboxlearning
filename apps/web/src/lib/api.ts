// The one way the app talks to the API. Requests go to /api/* on this origin (forwarded to FastAPI), carry the
// HttpOnly session cookies, and come back either as data or as an ApiError with a code and a plain message.
// An expired access token is refreshed once, transparently; if that fails the person is sent to /session-expired.
import type { ApiErrorBody } from "@shared/index";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string,
              public details?: Record<string, unknown>, public requestId?: string | null) {
    super(message);
  }
  /** Field-level messages from validation errors, keyed by field name. */
  get fields(): Record<string, string> {
    return (this.details?.fields as Record<string, string>) ?? {};
  }
  get problems(): string[] {
    return (this.details?.problems as string[]) ?? [];
  }
}

const BASE = "/api";
let refreshing: Promise<boolean> | null = null;

async function refresh(): Promise<boolean> {
  refreshing ??= fetch(`${BASE}/auth/refresh`, { method: "POST", credentials: "include" })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => setTimeout(() => (refreshing = null), 0));
  return refreshing;
}

type Options = { method?: string; body?: unknown; form?: FormData; signal?: AbortSignal; noRedirect?: boolean };

export async function api<T>(path: string, opts: Options = {}, retried = false): Promise<T> {
  const init: RequestInit = { method: opts.method ?? (opts.body || opts.form ? "POST" : "GET"), credentials: "include",
                              signal: opts.signal, headers: { Accept: "application/json" } };
  if (opts.form) init.body = opts.form;
  else if (opts.body !== undefined) {
    init.body = JSON.stringify(opts.body);
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError(0, "NETWORK", "We couldn't reach UnboxEd. Check your connection and try again.");
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (res.ok) return data as T;
  const err = (data as ApiErrorBody | null)?.error;
  const code = err?.code ?? "ERROR";
  if (res.status === 401 && !retried && (code === "SESSION_EXPIRED" || code === "UNAUTHENTICATED")
      && !path.startsWith("/auth/")) {
    if (await refresh()) return api<T>(path, opts, true);
    if (!opts.noRedirect && typeof window !== "undefined") {
      const next = encodeURIComponent(location.pathname + location.search);
      location.assign(code === "SESSION_EXPIRED" ? `/session-expired?next=${next}` : `/login?next=${next}`);
    }
  }
  throw new ApiError(res.status, code, err?.message ?? "Something went wrong. Please try again.", err?.details,
                     err?.request_id);
}

export const get = <T>(path: string, signal?: AbortSignal) => api<T>(path, { signal });
export const post = <T>(path: string, body?: unknown) => api<T>(path, { method: "POST", body: body ?? {} });
export const put = <T>(path: string, body?: unknown) => api<T>(path, { method: "PUT", body });
export const patch = <T>(path: string, body?: unknown) => api<T>(path, { method: "PATCH", body });
export const del = (path: string) => api<void>(path, { method: "DELETE" });

/** Turn an API-relative path (e.g. a signed /files/... path) into one the browser can load. */
export const apiUrl = (path: string) => `${BASE}${path}`;
