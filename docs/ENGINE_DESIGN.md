# Learning Transformation Engine — design

The engine turns **any trusted source** (PDF, Word, PowerPoint, web page, docs site, plain text,
Markdown, YouTube, audio/video, images) into an **adaptive, evidence-backed learning experience**,
shaped by **what kind of knowledge the content holds** and **what the learner is trying to achieve**.

It is deliberately *not* "summarise this PDF into a course". Every stage produces an explicit,
inspectable artefact that a teacher can review before a learner sees it.

```
SOURCES ──► INGEST ──► PROFILE ──► EXTRACT ──► CURRICULUM ──► PLAN ──► GENERATE ──► VERIFY ──► REVIEW ──► LEARN ──► MASTERY
            elements   what is     concepts    objectives     how to    activities   evidence   teacher     tutor +     per-objective
            + evidence  this?      graph       for the goal   teach it  (typed JSON) check      approval    renderers   state + review
```

## 1. Evidence first

Every source becomes a list of **elements** (heading, paragraph, list item, code, table, figure,
equation, quote, slide, transcript segment) with page / slide / timestamp, section path and a parse
confidence. Everything generated later points back to element ids. That is what makes
"click a question → see exactly where it came from" possible, and what lets the verifier reject
claims the source does not support.

Parsing uses progressive fallback: native text → layout heuristics (fonts, TOC, repeated
header/footer removal) → vision model for scanned or image-only pages → speech-to-text for media.
Low-confidence pages are surfaced, never silently converted.

## 2. Content intelligence: profile before generating

Documents mix kinds of knowledge, and **each kind is learned differently**. The profiler combines
cheap deterministic signals (code ratio, formula density, dates, numbered steps, tables, figures,
question density, dialogue) with a model read of the outline and samples to decide:

* **Genre** — textbook chapter, technical/API docs, research paper, encyclopedic article,
  how-to / SOP / manual, policy / legal / compliance, narrative / history / literature,
  lecture / slide deck, transcript, question bank / exam paper, data report, business case.
* **Knowledge-type mix** (per section, then per concept):

| Knowledge type | What it looks like | How it is best learned | Renderers used |
|---|---|---|---|
| `fact` | names, terms, definitions, values | retrieval + spacing | flashcards, matching, cloze, mcq |
| `concept` | categories with defining features | examples vs non-examples, contrast | categorize, compare table, mcq |
| `principle` | cause→effect, rules, trade-offs | predict → observe → explain | predict, parameter explorer, scenario |
| `process` | how a system works over stages | step-through, sequence, "what happens next" | process stepper, ordering, diagram labels |
| `procedure` | how to *do* a task | worked example → faded practice → apply | worked example, ordering, scenario, code task |
| `structure` | parts and where they are | label, locate, explore | diagram hotspots, 3D viewer (asset) |
| `chronology` | events, causes over time | timeline, cause chains, perspectives | timeline, ordering, roleplay |
| `argument` | cases, positions, judgement | analyse, decide, defend | case study, branching scenario, debate, rubric answer |
| `quantitative` | formulas, calculations | worked example → numeric variants | worked example, numeric problem, parameter explorer |
| `code` | APIs, snippets, configuration | read → predict → fix → write | code walkthrough, predict output, find the bug, config chooser |
| `language` | vocabulary, grammar, usage | recall, produce, hear | flashcards, cloze, pronunciation (voice) |
| `data` | charts, tables, statistics | read, interpret, question | table/chart questions |

The profiler also marks what is **core** vs **reference/boilerplate** (references, "see also",
changelogs, navigation) so time and money are spent on what is worth learning.

## 3. Goals shape the outcome

The same source produces different experiences for different goals. A course is
`sources + goal`. The goal model:

* **purpose** — `understand`, `apply` (build/do), `exam_prep`, `certification` / compliance,
  `revision`, `onboarding`, `teach_others`
* **audience** — level (novice → expert) and a free-text description
* **time budget** and **depth** (overview / standard / deep)
* **specific goals** — free text such as "be able to deploy an agent with human approval steps";
  these are interpreted into objective weights and must each map to objectives (unmapped goals are
  reported as *not covered by the sources* rather than invented)
* **exam format** (for `exam_prep`), **language**, **hands-on** preference

After profiling, the engine **suggests goals** that the content can genuinely support, so a
teacher can pick instead of inventing them.

| Purpose | What changes |
|---|---|
| understand | explanation + concept-contrast heavy; transfer questions at the end |
| apply | worked examples, faded practice, scenarios, code/config tasks; fewer recall items |
| exam_prep | exam-format questions, timed checks, heavy retrieval + spacing, weak-area targeting |
| certification | explicit mastery thresholds, every objective assessed, audit trail |
| revision | flashcards, summaries, rapid mixed quizzes; minimal new explanation |
| onboarding | procedures and decisions in the learner's role context; scenarios |
| teach_others | explain-it-back prompts, misconceptions, analogies |

## 4. Knowledge model

Per section the extractor emits concepts (with definition, knowledge type, importance, evidence),
relations (`prerequisite`, `part_of`, `example_of`, `contrasts_with`, `causes`, `used_for`),
candidate objectives, misconceptions (with correction and evidence), worked examples, procedures,
formulas (with variables and units), timeline events and useful figures. A consolidation pass merges
duplicates across sections and forms a prerequisite graph (cycles broken, order computed).

## 5. Curriculum and pedagogy

The curriculum designer selects and orders **objectives** that fit the goal and time budget. Each
objective carries a knowledge type, Bloom level, concepts, success criteria and evidence.

The planner then designs a **lesson per objective** in stages taken from the research base
(activation, modelling, scaffolded practice, retrieval, feedback, transfer, spacing):

`activate → explain/model → practise (hint ladder) → check → transfer`, with later `retrieve`
reviews scheduled by the mastery engine.

Eligibility is **rule-based first** (knowledge type × goal × available evidence such as a figure,
code or formula × renderer capabilities), and the model chooses and justifies within the eligible
set. The rationale is stored and shown to the teacher.

## 6. Activities and renderers

Every activity is typed JSON validated against a schema, carries evidence ids, a difficulty,
the objective id and a review status. The web app has one renderer per type; adding a type means
adding a schema, a generator instruction, a grader and a renderer — nothing else changes.

Generated **simulations are data, not code**: a *parameter explorer* is a set of variables with
ranges plus output expressions in a restricted math grammar that the client evaluates safely; a
*process stepper* is a list of states and transitions. No generated code is ever executed.

Capabilities that need assets or providers (3D models, generated video, voice) are registered
renderers that are only planned when the asset/provider exists — the plan never promises what
cannot be rendered.

## 7. Trust

* Generation receives only the evidence it is allowed to use and must cite element ids.
* A verifier checks each activity's key claims/answers against the cited evidence
  (`verified`, `flagged` with reason).
* Uploaded content is treated as untrusted data: instructions inside sources are never followed.
* Nothing reaches learners without `approved` status (a course setting can auto-approve for
  personal use).

## 8. Learner model

Per learner × objective: Bayesian-knowledge-tracing style mastery (prior, learn, slip, guess,
adjusted for difficulty and hints used), attempt history, next review date (spaced intervals that
grow with success). Transparent — the teacher can see why the engine thinks a learner needs help.

## 9. Tutor

Hybrid retrieval (keyword + embeddings, reciprocal-rank fusion) restricted to the course's sources,
aware of the learner's mastery and current activity. Default policy is Socratic: question → nudge
→ concept reminder → partial step → worked step, and it never reveals answers of graded items. It
says so when the sources do not cover a question.

## 10. Providers

A provider-neutral gateway with three tiers (`fast`, `standard`, `premium`) plus embeddings,
configured in `.env`. OpenAI is primary; Anthropic is supported; a `mock` provider lets the whole
pipeline and UI run without a key for development.
