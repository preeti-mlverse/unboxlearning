import { LinkButton } from "@/components/ui";

export const metadata = { title: "Not allowed" };

export default function UnauthorizedPage() {
  return (
    <div className="grid gap-5">
      <span className="text-5xl" aria-hidden>🔒</span>
      <h1 className="text-4xl font-extrabold">You don&apos;t have access to this</h1>
      <p className="text-muted">This page belongs to a workspace or role you&apos;re not part of. If you think you should have access,
        ask the person who manages the workspace.</p>
      <div className="flex flex-wrap gap-3">
        <LinkButton href="/" variant="violet">Go to my home</LinkButton>
        <LinkButton href="/login" variant="ghost">Log in as someone else</LinkButton>
      </div>
    </div>
  );
}
