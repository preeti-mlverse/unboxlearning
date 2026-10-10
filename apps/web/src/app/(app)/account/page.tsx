"use client";
import { useState } from "react";

import { Alert, Button, Card, Input, PageHeader, Select } from "@/components/ui";
import { ApiError, patch, post } from "@/lib/api";
import { password as passwordRule } from "@/lib/forms";
import { useSession } from "@/lib/session";

const LANGS: [string, string][] = [["en", "English"], ["hi", "हिन्दी Hindi"], ["ta", "தமிழ் Tamil"], ["te", "తెలుగు Telugu"],
  ["bn", "বাংলা Bengali"], ["mr", "मराठी Marathi"], ["es", "Español"], ["fr", "Français"], ["ar", "العربية Arabic"]];
const ROLE_LABEL: Record<string, string> = { org_admin: "Admin", creator: "Creator", learner: "Learner" };

export default function AccountPage() {
  const { me, reload, logout } = useSession();
  const [name, setName] = useState(me?.profile.display_name ?? "");
  const [language, setLanguage] = useState(me?.profile.preferred_language ?? "en");
  const [profileMsg, setProfileMsg] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [pw, setPw] = useState({ current: "", next: "" });
  const [pwMsg, setPwMsg] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  if (!me) return null;

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    setBusy("profile");
    try {
      await patch("/users/me", { display_name: name, preferred_language: language });
      await reload();
      setProfileMsg({ tone: "good", text: "Saved." });
    } catch (err) {
      setProfileMsg({ tone: "bad", text: err instanceof ApiError ? Object.values(err.fields)[0] ?? err.message : "Something went wrong." });
    } finally { setBusy(null); }
  }

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    const r = passwordRule.safeParse(pw.next);
    if (!r.success) { setPwMsg({ tone: "bad", text: `New password: ${r.error.issues[0].message}` }); return; }
    setBusy("pw");
    try {
      await post("/auth/change-password", { current_password: pw.current, new_password: pw.next });
      setPw({ current: "", next: "" });
      setPwMsg({ tone: "good", text: "Password changed." });
    } catch (err) {
      setPwMsg({ tone: "bad", text: err instanceof ApiError ? err.message : "Something went wrong." });
    } finally { setBusy(null); }
  }

  return (
    <>
      <PageHeader eyebrow="Account" title="Your profile" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="grid content-start gap-4">
          <h2 className="text-xl font-extrabold">Profile</h2>
          {profileMsg && <Alert tone={profileMsg.tone}>{profileMsg.text}</Alert>}
          <form onSubmit={saveProfile} className="grid gap-4">
            <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
            <Input label="Email" value={me.email} disabled hint={me.email_verified ? "Confirmed ✓" : "Not confirmed yet. Check your inbox for the link."} />
            {me.phone && <Input label="Mobile" value={`+91 ${me.phone}`} disabled />}
            <Select label="Preferred language" value={language} onChange={(e) => setLanguage(e.target.value)}>
              {LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </Select>
            <Button type="submit" variant="violet" busy={busy === "profile"}>Save profile</Button>
          </form>
        </Card>
        <div className="grid content-start gap-6">
          <Card className="grid gap-4">
            <h2 className="text-xl font-extrabold">Password</h2>
            {pwMsg && <Alert tone={pwMsg.tone}>{pwMsg.text}</Alert>}
            <form onSubmit={changePassword} className="grid gap-4">
              <Input label="Current password" type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} />
              <Input label="New password" type="password" autoComplete="new-password" value={pw.next} hint="At least 8 characters, with letters and numbers."
                     onChange={(e) => setPw({ ...pw, next: e.target.value })} />
              <Button type="submit" variant="ghost" busy={busy === "pw"}>Change password</Button>
            </form>
          </Card>
          <Card className="grid gap-3">
            <h2 className="text-xl font-extrabold">Workspaces</h2>
            {me.memberships.length === 0 ? <p className="text-muted">You&apos;re learning on your own. Courses you join appear in My learning.</p> : (
              <ul className="grid gap-2">
                {me.memberships.map((m) => (
                  <li key={m.organization_id} className="flex flex-wrap items-center justify-between gap-2">
                    <b>{m.organization_name}</b>
                    <span className="flex gap-1">{m.roles.map((r) => <span key={r} className="rounded-full bg-lavender px-2 py-0.5 font-mono text-xs uppercase text-violet">{ROLE_LABEL[r] ?? r}</span>)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card className="grid gap-3">
            <h2 className="text-xl font-extrabold">Sessions</h2>
            <div className="flex flex-wrap gap-2">
              <Button variant="ghost" onClick={logout}>Log out</Button>
              <Button variant="danger" busy={busy === "all"} onClick={async () => { setBusy("all"); await post("/auth/logout-everywhere"); location.assign("/login?bye=1"); }}>
                Log out on every device
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
