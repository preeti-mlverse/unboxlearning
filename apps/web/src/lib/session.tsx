"use client";
// Who is signed in, which workspace they're working in, and log-out. The API is the authority: this context only
// mirrors /users/me so the UI can decide what to show.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { Me, Membership } from "@shared/index";

import { api, ApiError, post } from "./api";

type Session = {
  me: Me | null;
  loading: boolean;
  reload: () => Promise<Me | null>;
  logout: () => Promise<void>;
  workspace: Membership | null;
  setWorkspace: (orgId: string) => void;
  creatorWorkspaces: Membership[];
};

const Ctx = createContext<Session | null>(null);
const KEY = "ub.workspace";

function readKey(): string | null {
  try { return localStorage.getItem(KEY); } catch { return null; }
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [orgId, setOrgId] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const m = await api<Me>("/users/me", { noRedirect: true });
      setMe(m);
      return m;
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setMe(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { setOrgId(readKey()); reload(); }, [reload]);

  const creatorWorkspaces = useMemo(() => (me?.memberships ?? []).filter((m) => m.roles.includes("creator")), [me]);
  const workspace = useMemo(() => {
    const all = me?.memberships ?? [];
    return all.find((m) => m.organization_id === orgId) ?? creatorWorkspaces[0] ?? all[0] ?? null;
  }, [me, orgId, creatorWorkspaces]);

  const setWorkspace = useCallback((id: string) => {
    setOrgId(id);
    try { localStorage.setItem(KEY, id); } catch { /* private mode: keep it for this tab only */ }
  }, []);

  const logout = useCallback(async () => {
    try { await post("/auth/logout"); } catch { /* already gone */ }
    setMe(null);
    location.assign("/login?bye=1");
  }, []);

  return <Ctx.Provider value={{ me, loading, reload, logout, workspace, setWorkspace, creatorWorkspaces }}>{children}</Ctx.Provider>;
}

export function useSession(): Session {
  const s = useContext(Ctx);
  if (!s) throw new Error("useSession must be used inside SessionProvider");
  return s;
}

export const HOME: Record<Me["home"], string> = { create: "/create", learn: "/learn", onboarding: "/onboarding", admin: "/admin" };
