// Typed client for the engine API.

export type Json = any; // eslint-disable-line @typescript-eslint/no-explicit-any

export interface SourceSummary {
  id: string; title: string; kind: string; origin: string; status: string; created_at: number;
  stats: Record<string, number | null>; parse_notes: string[]; low_confidence_pages: number[];
}
export interface Element {
  id: string; source_id: string; ord: number; kind: string; level: number | null; text: string;
  page: number | null; section_path: string[]; media_path: string | null; confidence: number; meta: Json;
}
export interface Goal {
  purpose: string; audience_level: string; audience_description: string; time_budget_minutes: number;
  depth: string; specific_goals: string[]; exam_format: string | null; language: string; hands_on: boolean; notes: string;
}
export interface Unit {
  id: string; source_id: string; title: string; path: string[]; tokens: number; pages: number[];
  signals: Record<string, number>; role: string; knowledge_types: string[]; note: string; hints: string[];
}
export interface Profile {
  title: string; summary: string; subject_domain: string; genre: string; source_level: string; language: string;
  knowledge_mix: { type: string; weight: number; where: string }[]; assumed_prerequisites: string[];
  modalities: string[]; units: Unit[];
  suggested_goals: { purpose: string; title: string; description: string; audience_level: string; why_supported: string }[];
  cautions: string[];
}
export interface Concept {
  id: string; name: string; definition: string; knowledge_type: string; importance: number; aliases: string[];
  evidence: string[]; units: string[]; mentions: number; depth: number;
}
export interface Objective {
  id: string; module_id: string; statement: string; bloom: string; knowledge_type: string; concept_ids: string[];
  success_criteria: string[]; estimated_minutes: number; serves_goals: number[]; evidence: string[];
}
export interface Curriculum {
  course_title: string; learner_promise: string; objectives: Objective[];
  modules: { id: string; title: string; why: string; objective_ids: string[] }[];
  uncovered_goals: string[]; excluded: string[];
}
export interface Plan {
  objective_id: string; rationale: string; allowed: Record<string, string[]>;
  steps: { stage: string; activity_type: string; intent: string; targets_misconception: string; difficulty: number }[];
}
export interface Activity {
  id: string; course_id: string; objective_id: string; type: string; stage: string; ord: number; status: string;
  data: { title: string; instructions: string; evidence: string[]; key_claims?: string[]; difficulty: number;
          payload: Json; intent?: string; targets_misconception?: string; reserve?: boolean };
  verify: { checks: { claim: string; supported: string; note: string }[]; answer_key_correct: string;
            pedagogy_issues: string[]; serious_issues?: string[]; verdict: string } | null;
}
export interface Job {
  id: string; status: string; stage: string; progress: number; message: string; log: string[]; kind: string;
}
export interface Course {
  id: string; title: string; status: string; source_ids: string[];
  data: { goal: Goal; settings: { quality: string; auto_approve: boolean; scope_unit_ids: string[] | null } };
  profile: Profile | null; graph: { concepts: Concept[]; edges: { source: string; target: string; type: string; why: string }[] } | null;
  curriculum: Curriculum | null; plans: Record<string, Plan>; job: Job | null; activity_counts: Record<string, number>;
  sources: SourceSummary[];
}
export interface CatalogEntry {
  key: string; label: string; purpose: string; knowledge_types: string[]; requires: string[]; grading: string;
  minutes: number; enabled: boolean; needs: string; stages: string[];
}
export interface AttemptResult {
  score: number | null; correct: boolean | null; feedback?: string; met?: string[]; missing?: string[];
  misconception?: string; detail?: Json;
}

async function req<T>(method: string, url: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, headers: {} };
  if (body instanceof FormData) init.body = body;
  else if (body !== undefined) {
    init.body = JSON.stringify(body);
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  const r = await fetch(url, init);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail ?? msg; } catch { /* not json */ }
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return r.json();
}

export const api = {
  health: () => req<Json>("GET", "/api/health"),
  healthCheck: () => req<{ state: string; message: string }>("POST", "/api/health/check"),
  estimate: (id: string) => req<Json>("GET", `/api/courses/${id}/estimate`),
  catalog: () => req<CatalogEntry[]>("GET", "/api/catalog"),
  usage: (courseId?: string) => req<Json[]>("GET", `/api/usage${courseId ? `?course_id=${courseId}` : ""}`),
  sources: () => req<SourceSummary[]>("GET", "/api/sources"),
  source: (id: string, offset = 0) => req<SourceSummary & { elements: Element[]; total: number }>("GET", `/api/sources/${id}?offset=${offset}&limit=600`),
  element: (id: string) => req<{ element: Element; context: Element[]; source: { id: string; title: string; kind: string; origin: string } }>("GET", `/api/elements/${id}`),
  upload: (files: File[]) => { const f = new FormData(); files.forEach((x) => f.append("files", x)); return req<SourceSummary[]>("POST", "/api/sources/upload", f); },
  addUrl: (url: string, crawl: boolean, max_pages = 30) => req<SourceSummary>("POST", "/api/sources/url", { url, crawl, max_pages }),
  addText: (text: string, title: string) => req<SourceSummary>("POST", "/api/sources/text", { text, title }),
  courses: () => req<Json[]>("GET", "/api/courses"),
  course: (id: string) => req<Course>("GET", `/api/courses/${id}`),
  createCourse: (source_ids: string[], title = "Untitled course", settings?: Json) => req<Course>("POST", "/api/courses", { title, source_ids, settings }),
  patchCourse: (id: string, patch: Json) => req<Course>("PATCH", `/api/courses/${id}`, patch),
  analyse: (id: string) => req<{ job_id: string }>("POST", `/api/courses/${id}/analyse`),
  build: (id: string) => req<{ job_id: string }>("POST", `/api/courses/${id}/build`),
  job: (id: string) => req<Job | null>("GET", `/api/courses/${id}/job`),
  activities: (id: string) => req<Activity[]>("GET", `/api/courses/${id}/activities`),
  patchActivity: (id: string, patch: Json) => req<Activity>("PATCH", `/api/activities/${id}`, patch),
  regenerate: (cid: string, aid: string, instruction: string, type?: string) => req<Activity>("POST", `/api/courses/${cid}/activities/${aid}/regenerate`, { instruction, type }),
  approveAll: (cid: string, includeFlagged = false) => req<{ approved: number }>("POST", `/api/courses/${cid}/approve_all?include_flagged=${includeFlagged}`),
  learner: (name: string) => req<{ id: string; name: string }>("POST", "/api/learners", { name }),
  next: (cid: string, lid: string, lang?: string) => req<{ mode: string; objective_id: string | null; activity: Activity | null; needs_help?: string[]; assessment?: Json; arm?: string }>("GET", `/api/courses/${cid}/learn/${lid}/next${lang ? `?lang=${lang}` : ""}`),
  learnCurriculum: (cid: string, lang?: string) => req<{ curriculum: Curriculum | null; languages: string[] }>("GET", `/api/courses/${cid}/learn/curriculum${lang ? `?lang=${lang}` : ""}`),
  translate: (cid: string, lang: string) => req<{ job_id: string }>("POST", `/api/courses/${cid}/translate`, { lang }),
  progress: (cid: string, lid: string) => req<{ threshold: number; objectives: { objective_id: string; statement: string; module_id: string; p: number; attempts: number; state: string }[] }>("GET", `/api/courses/${cid}/learn/${lid}/progress`),
  learnActivity: (cid: string, aid: string) => req<Activity>("GET", `/api/courses/${cid}/learn/activity/${aid}`),
  attempt: (aid: string, learner_id: string, response: Json, hints = 0, lang?: string) => req<{ result: AttemptResult; mastery: Json; solution: Json }>("POST", `/api/activities/${aid}/attempt`, { learner_id, response, hints, lang }),
  tutor: (cid: string, body: Json) => req<{ reply: string; move: string; citations: string[]; followup_question: string }>("POST", `/api/courses/${cid}/tutor`, body),
  roleplay: (aid: string, history: Json[], message: string) => req<{ reply: string; goal_progress: number; criteria_met: string[]; finished: boolean; coach_note: string }>("POST", `/api/activities/${aid}/roleplay`, { history, message }),
  tts: (text: string) => req<{ url: string }>("POST", "/api/tts", { text }),
  items: (cid: string) => req<Json[]>("GET", `/api/courses/${cid}/items`),
  dashboard: (cid: string) => req<Json>("GET", `/api/courses/${cid}/dashboard`),
  unitKnowledge: (cid: string, uid: string) => req<Json>("GET", `/api/courses/${cid}/unit_knowledge/${uid}`),
};

export const PURPOSES: Record<string, { label: string; blurb: string }> = {
  understand: { label: "Understand", blurb: "Build a solid conceptual grasp" },
  apply: { label: "Apply / build", blurb: "Be able to do it: worked examples, practice, scenarios" },
  exam_prep: { label: "Exam prep", blurb: "Exam-style questions, retrieval and weak-spot focus" },
  certification: { label: "Certification", blurb: "Every critical point assessed to a threshold" },
  revision: { label: "Quick revision", blurb: "Compact recall of what matters" },
  onboarding: { label: "Onboarding", blurb: "What someone in the role needs, in context" },
  teach_others: { label: "Teach others", blurb: "Explain it well, anticipate misconceptions" },
};

export const LANGUAGES: [string, string][] = [["en", "English"], ["hi", "हिन्दी Hindi"], ["ta", "தமிழ் Tamil"], ["te", "తెలుగు Telugu"],
  ["bn", "বাংলা Bengali"], ["mr", "मराठी Marathi"], ["kn", "ಕನ್ನಡ Kannada"], ["ml", "മലയാളം Malayalam"], ["gu", "ગુજરાતી Gujarati"],
  ["pa", "ਪੰਜਾਬੀ Punjabi"], ["ur", "اردو Urdu"], ["ar", "العربية Arabic"], ["es", "Español"], ["fr", "Français"], ["de", "Deutsch"],
  ["pt", "Português"], ["ja", "日本語"], ["zh", "中文"], ["id", "Bahasa Indonesia"], ["sw", "Kiswahili"]];

export const KT_LABEL: Record<string, string> = {
  fact: "Facts & terms", concept: "Concepts", principle: "Principles", process: "Processes", procedure: "Procedures",
  structure: "Structures", chronology: "Chronology", argument: "Arguments & cases", quantitative: "Quantitative",
  code: "Code & APIs", language: "Language", data: "Data & charts",
};
