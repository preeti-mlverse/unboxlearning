// Accounts: the signed-in user, log-in / sign-up / log-out, and route guards.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { setAccountLearner } from "./micro/mapi";

export interface User { id: string; email: string; name: string; phone: string; role: string; org: string; language: string; is_educator: boolean }

async function call<T>(method: string, url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, { method, credentials: "same-origin", headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Something went wrong. Please try again.");
  return data as T;
}

export const authApi = {
  me: () => call<{ user: User | null }>("GET", "/api/auth/me"),
  login: (id: string, password: string, remember: boolean) => call<{ user: User }>("POST", "/api/auth/login", { id, password, remember }),
  signup: (body: Record<string, string>) => call<{ user: User }>("POST", "/api/auth/signup", body),
  logout: () => call<{ ok: boolean }>("POST", "/api/auth/logout"),
  reset: (email: string) => call<{ message: string }>("POST", "/api/auth/reset", { email }),
  dashboard: () => call<Dashboard>("GET", "/api/dashboard"),
  claim: (cid: string) => call<{ ok: boolean }>("POST", `/api/courses/${cid}/claim`),
};

export interface CourseCard {
  id: string; title: string; tagline: string; status: string; outline: string | null; cover: string | null; modules: number; cards: number;
  published: boolean; learners: number; updated_at: number;
  progress?: { modules_done: number; modules_total: number; percent: number; xp: number; last_day: string | null } | null;
}
export interface Dashboard { user: User; my_courses?: CourseCard[]; unclaimed?: CourseCard[]; learning: CourseCard[]; available: CourseCard[] }

interface AuthState { user: User | null; ready: boolean; setUser: (u: User | null) => void; logout: () => Promise<void> }
const Ctx = createContext<AuthState>({ user: null, ready: false, setUser: () => {}, logout: async () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const setUser = (u: User | null) => { setAccountLearner(u ? { id: u.id, name: u.name } : null); setUserState(u); };
  useEffect(() => { authApi.me().then((r) => setUser(r.user)).catch(() => setUser(null)).finally(() => setReady(true)); }, []);
  const logout = async () => { await authApi.logout().catch(() => {}); setUser(null); };
  // wait for the session check so pages know who is signed in from their first render
  if (!ready) return <main className="m-page"><div className="m-loading" /></main>;
  return <Ctx.Provider value={{ user, ready, setUser, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);

export function RequireEducator({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const loc = useLocation();
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(loc.pathname)}`} replace />;
  if (!user.is_educator) {
    return (
      <main className="m-page narrow">
        <div className="m-empty">Creating courses needs an educator account. You're signed in as a learner.<br />
          <a href="/dashboard">Go to your dashboard</a></div>
      </main>
    );
  }
  return <>{children}</>;
}
