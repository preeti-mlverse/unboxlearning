"use client";
import { useEffect, useState } from "react";
import type { Member, Organization } from "@shared/index";

import { Alert, Button, Card, ErrorState, Input, Loading, PageHeader, Select } from "@/components/ui";
import { ApiError, patch } from "@/lib/api";
import { timeAgo, useApi } from "@/lib/hooks";
import { useSession } from "@/lib/session";

const ROLE_LABEL: Record<string, string> = { org_admin: "Admin", creator: "Creator", learner: "Learner" };
const TYPES: [string, string][] = [["independent_creator", "Independent educator or creator"], ["school", "School"],
  ["university", "College or university"], ["ngo", "NGO or public program"], ["company", "Company or organization"]];

export default function SettingsPage() {
  const { workspace, reload } = useSession();
  const org = workspace?.organization_id;
  const isAdmin = workspace?.roles.includes("org_admin");
  const details = useApi<Organization>(org ? `/organizations/${org}` : null);
  const members = useApi<Member[]>(org && isAdmin ? `/organizations/${org}/members` : null);
  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [msg, setMsg] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (details.data) { setName(details.data.name); setType(details.data.type); } }, [details.data]);

  if (!workspace) return null;
  if (details.loading) return <Loading />;
  if (details.error) return <ErrorState error={details.error} />;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await patch(`/organizations/${org}`, { name, type });
      await reload();
      setMsg({ tone: "good", text: "Saved." });
    } catch (err) {
      setMsg({ tone: "bad", text: err instanceof ApiError ? err.message : "Something went wrong." });
    } finally { setBusy(false); }
  }

  return (
    <>
      <PageHeader eyebrow="Workspace" title="Settings" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="grid content-start gap-4">
          <h2 className="text-xl font-extrabold">Workspace details</h2>
          {msg && <Alert tone={msg.tone}>{msg.text}</Alert>}
          {isAdmin ? (
            <form onSubmit={save} className="grid gap-4">
              <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} />
              <Select label="Type" value={type} onChange={(e) => setType(e.target.value)}>
                {TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </Select>
              <p className="font-mono text-xs text-muted">Address: {details.data?.slug}</p>
              <Button type="submit" variant="violet" busy={busy}>Save</Button>
            </form>
          ) : <p className="text-muted">Only workspace admins can change these details.</p>}
        </Card>
        <Card className="grid content-start gap-4">
          <h2 className="text-xl font-extrabold">People</h2>
          {!isAdmin ? <p className="text-muted">Only workspace admins can see the member list.</p> : members.loading ? <Loading /> : (
            <ul className="grid gap-3">
              {members.data?.map((m) => (
                <li key={m.user_id} className="flex flex-wrap items-center justify-between gap-2">
                  <span className="grid"><b>{m.display_name}</b><span className="text-sm text-muted">{m.email}</span></span>
                  <span className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
                    {m.roles.map((r) => <span key={r} className="rounded-full bg-lavender px-2 py-0.5 font-mono uppercase text-violet">{ROLE_LABEL[r] ?? r}</span>)}
                    joined {timeAgo(m.joined_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="text-sm text-muted">Inviting colleagues and learners to a workspace comes next. For now, learners join published courses themselves.</p>
        </Card>
      </div>
    </>
  );
}
