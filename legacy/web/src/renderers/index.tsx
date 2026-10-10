import type { ComponentType } from "react";
import { CodeWalkthrough, Explainer, Flashcards, WorkedExample } from "./basic";
import { Categorize, Matching, Ordering, Timeline } from "./arrange";
import { CompareTable, ConceptMap, MCQ, Predict, ProcessStepper } from "./choice";
import { DiagramLabel, FindTheBug, Roleplay, Scenario } from "./interactive";
import { ParameterExplorer } from "./sim";
import { VideoLesson } from "./video";
import { Model3D } from "./model3d";
import { DistributionSampler } from "./sampler";
import { CaseStudy, Cloze, NumericProblem, ShortAnswer, TeachBack } from "./text";
import type { RProps } from "./common";

export type { RProps } from "./common";

export const RENDERERS: Record<string, ComponentType<RProps>> = {
  explainer: Explainer, worked_example: WorkedExample, code_walkthrough: CodeWalkthrough, flashcards: Flashcards,
  mcq: MCQ, predict: Predict, compare_table: CompareTable, process_stepper: ProcessStepper, concept_map: ConceptMap,
  ordering: Ordering, timeline: Timeline, matching: Matching, categorize: Categorize,
  cloze: Cloze, short_answer: ShortAnswer, teach_back: TeachBack, case_study: CaseStudy, numeric_problem: NumericProblem,
  parameter_explorer: ParameterExplorer, scenario: Scenario, roleplay: Roleplay, find_the_bug: FindTheBug,
  diagram_label: DiagramLabel, video_lesson: VideoLesson, model_3d: Model3D, distribution_sampler: DistributionSampler,
};
