import type { CapabilitySet, InspiredBySource, SourceRef, TargetRef } from "./index";
import type { StudyTaskLevel } from "./study-task";

export type StudyFlowSurface =
  | "lab"
  | "notebook"
  | "runstore"
  | "observatory"
  | "observatory_compare";

export interface StudyFlowStep {
  stepId: string;
  title: string;
  surface: StudyFlowSurface;
  instruction: string;
}

export interface StudyFlow {
  kind: "openplazma.study_flow";
  version: "0.1.0";
  flowId: string;
  title: string;
  summary: string;
  level: StudyTaskLevel;
  estimatedMinutes: number;
  scenarioId: string;
  taskIds: string[];
  source: SourceRef;
  target: TargetRef & {
    type: "static_fixture";
  };
  capabilities: CapabilitySet;
  steps: StudyFlowStep[];
  expectedArtifacts: string[];
  expectedMetrics: string[];
  completionChecklist: string[];
  limitations: string[];
}

export interface StudyFlowManifestEntry {
  flowId: string;
  path: string;
}

export interface StudyFlowManifest {
  kind: "openplazma.study_flow_manifest";
  version: "0.1.0";
  flows: StudyFlowManifestEntry[];
  inspiredBy?: InspiredBySource | undefined;
}
