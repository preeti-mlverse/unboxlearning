"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Organization } from "@shared/index";

import { Alert, Button, Card, Input, PageHeader, Select } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { useSession } from "@/lib/session";

const TYPES: [string, string][] = [["independent_creator", "Just me (independent educator or creator)"], ["school", "School"],
  ["university", "College or university"], ["ngo", "NGO or public program"], ["company", "Company or organization"]];
const FROM_INTENT: Record<string, string> = { school: "school", ngo: "ngo", organization: "company", educator: "independent_creator" };

export default function OnboardingPage() {
  const { me, reload, setWorkspace } = useSession();
  const router = useRouter();
  const [name, setName] = useState("");
  const [type, setType] = useState(FROM_INTENT[me?.profile.signup_intent ?? ""] ?? "independent_creator");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (name.trim().length < 2) { setError("Give your workspace a name."); return; }
    setBusy(true);
    try {
      const org = await post<Organization>("/organizations", { name, type });
      setWorkspace(org.id);
      await reload();
      router.replace("/create?welcome=1");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <PageHeader eyebrow="One quick step" title="Create your workspace">
        A workspace holds your courses and documents. Everyone you add later works inside it, and nothing in it is
        visible to other workspaces.
      </PageHeader>
      <Card>
        <form onSubmit={submit} noValidate className="grid gap-4">
          {error && <Alert tone="bad">{error}</Alert>}
          <Input label="Workspace name" placeholder="e.g. Green Valley School, Acme Training" value={name}
                 onChange={(e) => setName(e.target.value)} autoFocus />
          <Select label="What kind of workspace is it?" value={type} onChange={(e) => setType(e.target.value)}>
            {TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
          <Button type="submit" variant="primary" size="lg" busy={busy}>Create workspace</Button>
        </form>
      </Card>
    </div>
  );
}
