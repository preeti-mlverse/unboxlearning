"use client";
// "/" sends each person to their own home: creators to /create, learners to /learn, new workspace owners to setup.
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Loading } from "@/components/ui";
import { landing, useSession } from "@/lib/session";

export default function Home() {
  const { me, loading } = useSession();
  const router = useRouter();
  useEffect(() => {
    if (loading) return;
    router.replace(me ? landing(me) : "/login");
  }, [me, loading, router]);
  return <Loading label="Opening UnboxEd…" />;
}
