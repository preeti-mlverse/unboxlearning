# Learning Transformation Engine

Turns trusted content — PDF, Word, PowerPoint, web pages, whole docs sites, Markdown/text, YouTube,
audio/video, images — into an **adaptive, evidence-backed course**, shaped by *what kind of knowledge the
content holds* and *what the learner is trying to achieve*.

* Design: [`docs/ENGINE_DESIGN.md`](docs/ENGINE_DESIGN.md)
* 3D/AR/VR, video, simulations, voice, multilingual, quality and efficacy: [`docs/ADVANCED_CAPABILITIES.md`](docs/ADVANCED_CAPABILITIES.md)

## Run it

```bash
# 1. once
python -m pip install fastapi uvicorn python-multipart pydantic openai anthropic pymupdf python-docx python-pptx \
    httpx beautifulsoup4 lxml trafilatura youtube-transcript-api python-dotenv numpy markdown
npm --prefix web install

# 2. add your key: copy .env.example to .env and set OPENAI_API_KEY (+ model names your account has)
python -m engine.cli models          # verifies the key, lists models, runs a test call

# 3. start (two terminals)
python -m uvicorn engine.api:app --port 8030
npm --prefix web run dev             # http://localhost:5190
```

Without a key the engine runs on an **offline mock provider** (schema-valid placeholder text) so every
screen and flow can be exercised. `python -m engine.cli gallery` seeds a course with one activity of every type.
For a single-server deployment, `npm --prefix web run build` and the API serves the app at http://localhost:8030.

## How it works

```
ingest → profile → (teacher picks goal + scope) → extract → concept graph → curriculum → plan → generate → validate/verify → review → learn
```

| Stage | Module | What it produces |
|---|---|---|
| Ingest | `engine/ingest/` | Elements (heading, paragraph, code, table, figure, equation, transcript…) with page/slide/timestamp and confidence; OCR/vision and speech-to-text fallbacks |
| Index | `engine/index.py` | Structure-aware chunks; hybrid retrieval (BM25 + embeddings, rank fusion); learning units |
| Profile | `engine/profile.py` | Genre, knowledge-type mix, unit roles (core/supporting/reference/boilerplate), suggested goals, cautions |
| Knowledge | `engine/knowledge.py` | Per-unit concepts, relations, objectives, misconceptions, procedures, formulas, events, figures → merged prerequisite graph → goal-shaped curriculum |
| Pedagogy | `engine/planner.py` | Lesson per objective: activate → model → practise → check → transfer, activity types chosen by knowledge type × goal × evidence × renderer capability, with rationale |
| Activities | `engine/activities.py`, `engine/generate.py` | 26 typed activity schemas; evidence-bound generation; structural validation with auto-repair; evidence verification |
| Learner | `engine/learner.py`, `engine/tutor.py` | Grading (auto / rubric / dialogue), BKT-style mastery, spaced review, remediation, Socratic source-grounded tutor, roleplay |
| Evidence & interop | `engine/analytics.py`, `evidence.py`, `export.py`, `translate.py`, `estimate.py` | Item analysis, pre/post experiments, QTI and bundles, translation, cost estimates |
| API / UI | `engine/api.py`, `web/` | Studio (setup, path, lessons review, knowledge graph, sources, learner analytics, AI usage) and learner app |

Activity types (26): explanation, narrated explainer (animated storyboard + voice), worked example, code
walkthrough, multiple choice, short answer, ordering, matching, sort-into-groups, fill-the-gaps, flashcards,
predict-then-see, find-the-bug, decision scenario, timeline, compare table, process stepper, parameter explorer and
distribution sampler (safe generated simulations), calculation, concept map, case study, teach-back, roleplay,
label-the-diagram (vision), explore-in-3D (teacher-attached models with hotspots, AR on phones).

Also built: pre-build cost estimate; AI status (e.g. "no credits") shown in the UI; reserve remediation items;
course translation with shared mastery; item analytics; independent pre/post/delayed tests with an optional
adaptive-vs-static experiment; QTI 2.1 export; portable course bundles (export/import).

## Tests

```bash
python -m pytest tests -q
npm --prefix web run typecheck
```
