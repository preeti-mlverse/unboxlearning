import Link from "next/link";

import { Logo } from "@/components/ui";

import { SITE_URL as SITE } from "@/lib/config";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <aside className="relative hidden overflow-hidden bg-uv p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div aria-hidden className="cube-field pointer-events-none absolute inset-0 opacity-[0.08]" />
        <div aria-hidden className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(124,193,202,.22),transparent_40%),radial-gradient(circle_at_80%_75%,rgba(230,95,69,.25),transparent_42%)]" />
        <a href={SITE} className="relative w-fit"><Logo light size={38} /></a>
        <div className="relative grid gap-5">
          <p className="eyebrow text-[#A99EF0]">The knowledge-to-learning engine</p>
          <p className="font-display text-5xl font-extrabold leading-[1.02]">
            Any knowledge <span className="text-mustard">in.</span><br />Real learning <span className="text-coral">out.</span>
          </p>
          <p className="max-w-md text-lg text-[#D9D2FF]">Turn what people know into experiences other people can understand.</p>
        </div>
        <p className="relative text-sm text-[#A99EF0]">
          <a className="hover:text-white" href={`${SITE}/privacy/`}>Privacy</a> · <a className="hover:text-white" href={`${SITE}/terms/`}>Terms</a>
        </p>
      </aside>
      <main className="flex flex-col px-4 py-6 sm:px-8">
        <div className="mb-6 lg:hidden"><Link href="/login"><Logo size={32} /></Link></div>
        <div className="m-auto w-full max-w-md py-6">{children}</div>
      </main>
    </div>
  );
}
