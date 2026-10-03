"""Domain vocabulary and the structured-output schemas the models must fill.

Schemas used with structured outputs avoid free-form dicts so they work in strict mode.
"""
from typing import Literal

from pydantic import BaseModel, Field

KnowledgeType = Literal["fact", "concept", "principle", "process", "procedure", "structure", "chronology",
                        "argument", "quantitative", "code", "language", "data"]
Genre = Literal["textbook", "technical_docs", "research_paper", "encyclopedic", "how_to_manual", "policy_legal",
                "narrative_history", "literature", "lecture_slides", "transcript", "question_bank", "data_report",
                "business_case", "other"]
Purpose = Literal["understand", "apply", "exam_prep", "certification", "revision", "onboarding", "teach_others"]
Level = Literal["novice", "beginner", "intermediate", "advanced", "expert"]
Bloom = Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
Stage = Literal["activate", "model", "practice", "check", "transfer"]
RelationType = Literal["prerequisite", "part_of", "example_of", "contrasts_with", "causes", "used_for", "related"]

KNOWLEDGE_TYPES = list(KnowledgeType.__args__)
PURPOSES = list(Purpose.__args__)


# --------------------------------------------------------------------------- goal (user input)

class Goal(BaseModel):
    purpose: Purpose = "understand"
    audience_level: Level = "beginner"
    audience_description: str = ""
    time_budget_minutes: int = 60
    depth: Literal["overview", "standard", "deep"] = "standard"
    specific_goals: list[str] = []
    exam_format: str | None = None
    language: str = "en"
    hands_on: bool = True
    notes: str = ""


# --------------------------------------------------------------------------- profile

class KnowledgeWeight(BaseModel):
    type: KnowledgeType
    weight: float = Field(description="share of the learnable content, 0..1; all weights sum to ~1")
    where: str = Field(description="which parts of the source carry this kind of knowledge")


class UnitAssessment(BaseModel):
    unit_id: str
    role: Literal["core", "supporting", "reference", "boilerplate"]
    knowledge_types: list[KnowledgeType]
    note: str


class SuggestedGoal(BaseModel):
    purpose: Purpose
    title: str = Field(description="learner-facing, e.g. 'Build and deploy your first research agent'")
    description: str
    audience_level: Level
    why_supported: str = Field(description="what in the source makes this goal achievable")


class ContentProfile(BaseModel):
    title: str
    summary: str
    subject_domain: str
    genre: Genre
    source_level: Level = Field(description="level the source itself assumes")
    language: str
    knowledge_mix: list[KnowledgeWeight]
    assumed_prerequisites: list[str]
    modalities: list[str] = Field(description="e.g. code, formulas, diagrams, tables, timelines, dialogue")
    units: list[UnitAssessment]
    suggested_goals: list[SuggestedGoal]
    cautions: list[str] = Field(description="risks: outdated, opinionated, fragmentary, low parse quality, ...")


# --------------------------------------------------------------------------- extraction (per unit)

class ExConcept(BaseModel):
    name: str
    definition: str
    knowledge_type: KnowledgeType
    importance: int = Field(description="1 = peripheral, 2 = useful, 3 = central")
    aliases: list[str]
    evidence: list[str] = Field(description="element ids like e12")


class ExRelation(BaseModel):
    source: str
    target: str
    type: RelationType
    evidence: list[str]


class ExObjective(BaseModel):
    statement: str = Field(description="'Learner can ...' with an observable verb")
    bloom: Bloom
    knowledge_type: KnowledgeType
    concepts: list[str]
    evidence: list[str]


class ExMisconception(BaseModel):
    concept: str
    misconception: str
    correction: str
    evidence: list[str]


class ExExample(BaseModel):
    title: str
    kind: Literal["code", "calculation", "scenario", "demonstration", "case", "analogy"]
    evidence: list[str]


class ExStep(BaseModel):
    text: str
    evidence: list[str]


class ExProcedure(BaseModel):
    name: str
    goal: str
    steps: list[ExStep]


class ExVariable(BaseModel):
    symbol: str
    meaning: str
    unit: str


class ExFormula(BaseModel):
    name: str
    expression: str
    variables: list[ExVariable]
    evidence: list[str]


class ExEvent(BaseModel):
    when: str
    what: str
    significance: str
    evidence: list[str]


class ExFigure(BaseModel):
    element_id: str
    shows: str


class UnitKnowledge(BaseModel):
    summary: str
    learning_value: Literal["high", "medium", "low", "none"]
    knowledge_types: list[KnowledgeType]
    concepts: list[ExConcept]
    relations: list[ExRelation]
    objectives: list[ExObjective]
    misconceptions: list[ExMisconception]
    worked_examples: list[ExExample]
    procedures: list[ExProcedure]
    formulas: list[ExFormula]
    events: list[ExEvent]
    figures: list[ExFigure]


# --------------------------------------------------------------------------- graph consolidation

class ConceptMerge(BaseModel):
    keep: str
    merge: list[str]


class GraphEdge(BaseModel):
    source: str = Field(description="concept id")
    target: str = Field(description="concept id")
    type: RelationType
    why: str


class ConceptGraphOut(BaseModel):
    merges: list[ConceptMerge]
    edges: list[GraphEdge]


# --------------------------------------------------------------------------- curriculum

class ObjectiveOut(BaseModel):
    statement: str
    bloom: Bloom
    knowledge_type: KnowledgeType
    concept_ids: list[str]
    candidate_ids: list[str] = Field(description="ids of the candidate objectives this one is built from")
    success_criteria: list[str]
    estimated_minutes: int
    serves_goals: list[int] = Field(description="indexes of the learner's specific goals this objective serves")


class ModuleOut(BaseModel):
    title: str
    why: str
    objectives: list[ObjectiveOut]


class CurriculumOut(BaseModel):
    course_title: str
    learner_promise: str = Field(description="one sentence: what the learner will be able to do")
    modules: list[ModuleOut]
    uncovered_goals: list[str] = Field(description="specific goals the sources cannot support")
    excluded: list[str] = Field(description="what was deliberately left out and why")


# --------------------------------------------------------------------------- verification

class ClaimCheck(BaseModel):
    claim: str
    supported: Literal["yes", "partly", "no"]
    note: str


class VerifyOut(BaseModel):
    checks: list[ClaimCheck]
    answer_key_correct: Literal["yes", "no", "not_applicable"]
    serious_issues: list[str] = Field(description="must-fix problems only: wrong or unanswerable item, more than one "
                                                  "defensible answer, answer visible before responding, factual error, "
                                                  "content that does not practise the objective at all")
    pedagogy_issues: list[str] = Field(description="minor improvement suggestions (wording, scaffolding, examples)")


class RubricGrade(BaseModel):
    score: float = Field(description="0..1")
    met: list[str]
    missing: list[str]
    feedback: str = Field(description="second person, specific, encouraging, no full model answer")
    misconception: str = Field(description="likely misconception shown, or empty")


class TutorReply(BaseModel):
    reply: str = Field(description="markdown; cite sources inline like [e12]")
    move: Literal["question", "nudge", "reminder", "partial", "worked", "answer", "not_in_sources", "off_topic"]
    citations: list[str]
    followup_question: str
