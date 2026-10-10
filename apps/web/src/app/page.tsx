"use client";
// "/" sends each person to their own home: creators to /create, learners to /learn, new workspace owners to setup.
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Loading } from "@/components/ui";
import { HOME, useSession } from "@/lib/session";

export default function Home() {
  const { me, loading } = useSession();
  const router = useRouter();
  useEffect(() => {
    if (loading) return;
    router.replace(me ? HOME[me.home] : "/login");
  }, [me, loading, router]);
  return <Loading label="Opening UnboxEd…" />;
}
