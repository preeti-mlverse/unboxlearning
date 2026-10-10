"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { post } from "@/lib/api";
import { useSession } from "@/lib/session";

import { Alert, Button, Loading, Logo, cx } from "./ui";

type Item = { href: string; label: string; icon: string; exact?: boolean };

const CREATE: Item[] = [
  { href: "/create", label: "Dashboard", icon: "◧", exact: true },
  { href: "/create/courses", label: "Courses", icon: "▤" },
  { href: "/create/documents", label: "Documents", icon: "⎘" },
  { href: "/create/settings", label: "Settings", icon: "⚙" },
];
const LEARN: Item[] = [
  { href: "/learn", label: "My learning", icon: "★", exact: true },
  { href: "/learn/catalog", label: "Find a course", icon: "⌕" },
  { href: "/learn/progress", label: "Progress", icon: "↗" },
];

function NavLink({ item, onNavigate }: { item: Item; onNavigate: () => void }) {
  const path = usePathname();
  const active = item.exact ? path === item.href : path === item.href || path.startsWith(item.href + "/");
  return (
    <Link href={item.href} onClick={onNavigate} aria-current={active ? "page" : undefined}
          className={cx("flex items-center gap-3 rounded-xl px-3 py-2 text-[15px] font-semibold transition",
                        active ? "bg-white/12 text-white shadow-[inset_3px_0_0_var(--mustard)]" : "text-[#CFC7FF] hover:bg-white/6 hover:text-white")}>
      <span aria-hidden className="w-4 text-center opacity-80">{item.icon}</span>{item.label}
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me, loading, logout, workspace, setWorkspace, creatorWorkspaces } = useSession();
  const router = useRouter();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const [resent, setResent] = useState(false);

  useEffect(() => {
    if (!loading && !me) router.replace(`/login?next=${encodeURIComponent(path)}`);
  }, [loading, me, router, path]);

  if (loading || !me) return <Loading label="Opening UnboxEd…" />;
  const isCreator = creatorWorkspaces.length > 0;
  const close = () => setOpen(false);

  const sidebar = (
    <nav aria-label="Main" className="flex h-full flex-col gap-6 overflow-y-auto p-4">
      <Link href="/" onClick={close} className="px-2"><Logo light size={32} /></Link>
      {creatorWorkspaces.length > 1 && (
        <label className="grid gap-1 px-2 text-xs font-bold uppercase tracking-wider text-[#A99EF0]">
          Workspace
          <select value={workspace?.organization_id} onChange={(e) => setWorkspace(e.target.value)}
                  className="rounded-lg border border-white/20 bg-uv-2 px-2 py-1.5 text-sm font-semibold normal-case tracking-normal text-white">
            {creatorWorkspaces.map((w) => <option key={w.organization_id} value={w.organization_id}>{w.organization_name}</option>)}
          </select>
        </label>
      )}
      {isCreator ? (
        <div className="grid gap-1">
          <p className="eyebrow px-3 pb-1 text-[#A99EF0]">Create{creatorWorkspaces.length === 1 ? ` · ${workspace?.organization_name}` : ""}</p>
          {CREATE.map((i) => <NavLink key={i.href} item={i} onNavigate={close} />)}
        </div>
      ) : me.home === "onboarding" ? (
        <div className="grid gap-1"><NavLink item={{ href: "/onboarding", label: "Set up your workspace", icon: "✦" }} onNavigate={close} /></div>
      ) : null}
      <div className="grid gap-1">
        <p className="eyebrow px-3 pb-1 text-[#A99EF0]">Learn</p>
        {LEARN.map((i) => <NavLink key={i.href} item={i} onNavigate={close} />)}
      </div>
      {me.is_platform_admin && (
        <div className="grid gap-1">
          <p className="eyebrow px-3 pb-1 text-[#A99EF0]">Platform</p>
          <NavLink item={{ href: "/admin", label: "Admin", icon: "⛭" }} onNavigate={close} />
        </div>
      )}
      <div className="mt-auto grid gap-1 border-t border-white/10 pt-4">
        <NavLink item={{ href: "/account", label: me.profile.display_name, icon: "●" }} onNavigate={close} />
        <button onClick={logout} className="flex items-center gap-3 rounded-xl px-3 py-2 text-left text-[15px] font-semibold text-[#CFC7FF] hover:bg-white/6 hover:text-white">
          <span aria-hidden className="w-4 text-center">⏻</span>Log out
        </button>
      </div>
    </nav>
  );

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[250px_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-dvh bg-uv lg:block">{sidebar}</aside>
      <header className="sticky top-0 z-30 flex items-center justify-between bg-uv px-4 py-3 lg:hidden">
        <Link href="/"><Logo light size={28} /></Link>
        <button onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="mobile-nav"
                className="rounded-xl border-2 border-white/30 px-3 py-1.5 text-sm font-bold text-white">{open ? "Close" : "Menu"}</button>
      </header>
      {open && <div id="mobile-nav" className="fixed inset-x-0 bottom-0 top-[56px] z-20 bg-uv lg:hidden">{sidebar}</div>}
      <main id="main" className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
        {!me.email_verified && (
          <div className="mb-6">
            <Alert tone="warn" title="Confirm your email"
                   action={resent ? <span className="text-sm font-bold">Sent. Check your inbox.</span>
                                  : <Button size="sm" variant="ghost" onClick={async () => { await post("/auth/resend-verification"); setResent(true); }}>Resend link</Button>}>
              We sent a link to <b>{me.email}</b>. Confirming it lets us reach you about your account.
            </Alert>
          </div>
        )}
        {children}
      </main>
    </div>
  );
}
