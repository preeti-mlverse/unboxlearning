# How products deliver the "advanced" capabilities — and how this engine incorporates them

The engine is built so each of these is **one more renderer or service behind the same activity schema**,
chosen by the planner only when it genuinely helps a given kind of knowledge (see `ENGINE_DESIGN.md`).

---

## 1. 3D, AR and VR

**How others do it**
* **Asset libraries, not generation.** AstraXR, EON Reality, BioDigital, Labster etc. rely on large curated
  libraries of pre-built, expert-checked 3D models (glTF/USDZ/FBX). AI's job is to *classify the concept,
  find the right asset, and author the experience around it* (hotspots, guided tour, narration, quiz overlays).
* **Delivery:** web viewers (Google `<model-viewer>`, three.js, Babylon.js) with phone AR via Scene Viewer /
  AR Quick Look, and WebXR or Unity/Unreal builds for headsets.
* **Generative 3D** (Meshy, Tripo, Luma, Stability SF3D, Microsoft TRELLIS) is good for props and objects
  but not reliable for scientifically accurate structures (anatomy, molecules, machines) — used with review.

**Built (working; verified in the browser with a generated test model)**
* Studio → Sources → **3D models**: attach a `.glb`, give it a name/description/tags, and **click on the model to
  place labelled hotspots** (raycast via `<model-viewer>`).
* The planner offers `model_3d` ("Explore in 3D") for `structure`/`process` objectives whose concepts match an
  asset; the generator writes an intro, a **guided tour over the teacher's hotspots only** (it never invents
  coordinates) and questions answered by exploring.
* Learner renderer: rotate/zoom, numbered hotspots, guided tour with camera focus, and an **AR button on phones**
  (Scene Viewer / Quick Look / WebXR).
* Next: search a licensed model library from the studio; WebXR headset mode.

## 2. Generated video

**How others do it**
* **Narrated slide/animation video** (most "AI video explainers", including notebook-style video overviews):
  script → storyboard → programmatic rendering (Remotion, Manim for maths, Motion Canvas) + text-to-speech.
  Cheap, accurate, editable.
* **Avatar presenters:** Synthesia / HeyGen / D-ID APIs turn a script into a talking-head video.
* **Generative video models** (Sora, Veo, Runway, Kling): cinematic b-roll; poor at precise diagrams, labels
  and text; expensive. Used sparingly for "hook" moments.

**Built:** `video_lesson` ("Narrated explainer") — a storyboard of 4–8 scenes (title, bullets, animated flow,
code, comparison, quote, or a real figure from the source) played as an animated sequence with narration from
OpenAI TTS, falling back to the browser's voice; captions, scene navigation, pause/resume; editable like any activity.
**Next:** MP4 export (Remotion/ffmpeg), optional avatar-presenter scenes (HeyGen/Synthesia).

## 3. Simulations generated automatically

**How others do it**
* PhET, Labster, ExploreLearning: **hand-built** simulations (high quality, slow and costly to make).
* Mindsmith-style "software simulations": captured screens with click-through steps.
* LLM code generation of interactive HTML (the "artifact" approach) — fast, but correctness and security
  risks; serious products run it in a sandboxed iframe with review.

**How it plugs in here (two tiers)**
1. **Template simulations (built, safe):** the model fills *data* for engine-owned renderers — already
   `parameter_explorer` (variables + safe expressions + live chart), `distribution_sampler` (outcomes, optional
   temperature/softmax, live sampling histogram — probability, statistics, LLM sampling), `process_stepper`,
   `scenario`, `concept_map`. Next templates: state machine, queue/flow, probability sampler, network/graph, 2D physics
   (matter.js), map layers, data-table explorer. Validated deterministically (`structural_issues`).
2. **Custom code simulations (later):** model writes a self-contained HTML/JS sim → runs in a sandboxed
   iframe (no network, strict CSP) → automated harness checks it loads, has no console errors and respects
   invariants from the evidence → teacher review. Only for knowledge types that need it.

## 4. Voice and multiple languages

**How others do it**
* **Text-to-speech:** OpenAI TTS, ElevenLabs, Azure/Google; for Indian languages Google Cloud, Azure and
  Sarvam AI (Bulbul) have strong voices.
* **Speech-to-text:** Whisper / gpt-4o-transcribe; Sarvam Saarika and AI4Bharat IndicConformer for Indic.
* **Live voice tutors:** OpenAI Realtime API (WebRTC) or a speech-to-text → LLM → TTS loop.
* **Multilingual:** the good products keep **one canonical course** and store per-language renditions,
  with institution glossaries and human review for assessments. AI4Bharat IndicTrans2 is a strong open
  model for Indic translation.

**Built:** "Listen" on explanations and narrated explainers (provider TTS, browser-voice fallback), speak-to-tutor
(browser speech recognition), course generation in 20 languages, and a **translate-course job**: a per-language
glossary from the concept graph; every approved activity translated into its own schema with the same ids; a
structural guard that rejects translations which change answers, ids, numbers, code or citations; text answers
graded in the language the learner saw; a learner language switcher; a tutor that replies in that language.
Mastery is shared across languages.
**Next:** realtime voice tutor (OpenAI Realtime), Indic TTS/STT providers, per-language retrieval checks.

## 5. Checking teaching quality

**How others do it**
* Human review/approval workflows (Mindsmith, Coursebox, Nolej), style guides, SME sign-off.
* **Item analytics after launch** (classical test theory / IRT): difficulty (p-value), discrimination
  (point-biserial), distractor analysis — bad items are retired automatically.
* Rubric-based AI critics checking alignment (objective ↔ activity ↔ assessment), cognitive level, clarity,
  cognitive load, accessibility.

**Built:** deterministic structural checks with one automatic repair; a reviewer that checks every key claim and
answer key against the evidence **and** a pedagogy checklist (alignment to the objective, Bloom level vs stage,
one defensible answer, giveaways, distractor quality, reading level, inclusiveness); teacher approve / edit /
regenerate-with-instruction; nothing reaches learners unapproved; **post-launch item analytics** (p-value,
point-biserial discrimination, distractor use) flagging weak items once 8+ learners have answered.
**Next:** teacher-edit-rate tracking per activity type.

## 6. Proving that students learn more

**How others do it:** efficacy studies to recognised evidence standards (e.g. ESSA tiers, What Works
Clearinghouse): pre/post tests on *independent* assessments, delayed retention tests, randomised or matched
comparison groups, published results.

**Built:** Studio → **Evidence**: independent pre/post/delayed tests (import a QTI 2.x zip or JSON, or write them),
taken before/after the course and after a configurable delay, without feedback; optional random assignment to
*adaptive* vs *static* (same approved content in fixed order, no remediation/review/tutor); a report with pre/post
means, gain and 95% CI, normalised gain, retention and effect size (Cohen's d); CSV export.
**Next:** class-level randomisation and a pre-registered analysis-plan template.

The engine provides the infrastructure; the evidence comes from running pilots with it.
