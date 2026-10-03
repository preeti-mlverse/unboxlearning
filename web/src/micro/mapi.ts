// Client for the micro-learning API.
import type { Json } from "../api";

export type VisualKind = "none" | "illustration" | "flow" | "cycle" | "compare" | "hierarchy" | "timeline" | "code" | "formula" | "figure";
export interface Visual { kind: VisualKind; prompt: string; items: string[]; code: string; figure_id: string; media?: string | null }
export interface Opt { text: string; correct: boolean; why: string }
export interface Card {
  kind: "hook" | "concept" | "example" | "check" | "true_false" | "sort" | "reorder" | "match" | "odd_one_out" | "fill_blank" | "apply" | "recap";
  title: string; text: string; narration: string; visual: Visual; options: Opt[]; pairs: { left: string; right: string }[];
  buckets: string[]; bucket_items: { text: string; bucket: string }[]; steps: string[];
  statements: { text: string; is_true: boolean; why: string }[]; blank_sentence: string; blank_answers: string[];
  question: string; model_answer: string; sources: string[];
}
export interface Module {
  id: string; title: string; goal: string; big_idea?: string; minutes: number; cards: Card[];
  flashcards: { front: string; back: string }[]; flags?: Record<string, string[]>; rule_issues?: string[];
}
export interface Blueprint { course_title: string; tagline: string; learner_promise: string; cover_media?: string; modules: Module[]; skipped: string[]; status: string }
export interface JourneyModule { id: string; title: string; goal: string; minutes: number; cards: number; cover: string | null; state: "done" | "current" | "locked" | "review"; score: number | null; mastery: number; mastered: boolean }
export interface Journey { title: string; tagline: string; promise: string; cover: string | null; modules: JourneyModule[]; xp: number; streak: number; deck_due: number }

async function req<T>(method: string, url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, { method, headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined });
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail ?? msg; } catch { /* not json */ }
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return r.json();
}

export const mapi = {
  get: (cid: string) => req<{ course: Json; profile: Json; blueprint: Blueprint | null; modules: Module[]; job: Json;
    sources: { id: string; title: string; kind: string }[]; concepts: Record<string, string> }>("GET", `/api/micro/${cid}`),
  build: (cid: string) => req<{ job_id: string }>("POST", `/api/micro/${cid}/build`),
  plan: (cid: string) => req<{ job_id: string }>("POST", `/api/micro/${cid}/plan`),
  generate: (cid: string) => req<{ job_id: string }>("POST", `/api/micro/${cid}/generate`),
  putOutline: (cid: string, body: Json) => req<Blueprint>("PUT", `/api/micro/${cid}/outline`, body),
  putCard: (cid: string, mid: string, i: number, card: Card) => req<Card>("PUT", `/api/micro/${cid}/modules/${mid}/cards/${i}`, { card }),
  regen: (cid: string, mid: string, i: number, instruction: string) => req<Card>("POST", `/api/micro/${cid}/modules/${mid}/cards/${i}/regenerate`, { instruction }),
  redraw: (cid: string, mid: string, i: number) => req<Card>("POST", `/api/micro/${cid}/modules/${mid}/cards/${i}/redraw`),
  publish: (cid: string, published: boolean) => req<Json>("POST", `/api/micro/${cid}/publish`, { published }),
  journey: (cid: string, lid: string) => req<Journey>("GET", `/api/micro/${cid}/journey/${lid}`),
  module: (cid: string, mid: string) => req<Module>("GET", `/api/micro/${cid}/modules/${mid}`),
  progress: (cid: string, body: Json) => req<{ xp: number; gained: number }>("POST", `/api/micro/${cid}/progress`, body),
  complete: (cid: string, mid: string, learner_id: string) => req<{ score: number | null; xp: number; mastery: number; streak: number }>("POST", `/api/micro/${cid}/modules/${mid}/complete`, { learner_id }),
  feedback: (cid: string, mid: string, i: number, learner_id: string, answer: string) => req<{ score: number; feedback: string; better_answer: string }>("POST", `/api/micro/${cid}/modules/${mid}/cards/${i}/feedback`, { learner_id, answer }),
  deck: (cid: string, lid: string, all = false) => req<{ key: string; module: string; front: string; back: string }[]>("GET", `/api/micro/${cid}/deck/${lid}${all ? "?all=true" : ""}`),
  rate: (cid: string, learner_id: string, key: string, rating: string) => req<Json>("POST", `/api/micro/${cid}/deck/rate`, { learner_id, key, rating }),
};

export function useLearner(cid: string) {
  const key = `learner:${cid}`;
  const read = () => { try { return JSON.parse(localStorage.getItem(key) ?? "null") as { id: string; name: string } | null; } catch { return null; } };
  const save = (l: { id: string; name: string } | null) => { try { if (l) localStorage.setItem(key, JSON.stringify(l)); else localStorage.removeItem(key); } catch { /* ignore */ } };
  return { read, save };
}
