import type { CapabilitySet, InspiredBySource, SourceRef, TargetRef } from "./index";

export type StudyTaskLevel = "beginner" | "intermediate" | "advanced";
export type StudyTaskPromptType = "observation" | "hypothesis" | "reflection";

export interface StudyTaskPrompt {
  promptId: string;
  type: StudyTaskPromptType;
  text: string;
}

export interface SuggestedMetric {
  name: string;
  description: string;
}

export interface StudyTask {
  kind: "openplazma.study_task";
  version: "0.1.0";
  taskId: string;
  scenarioId: string;
  title: string;
  summary: string;
  level: StudyTaskLevel;
  estimatedMinutes: number;
  source: SourceRef;
  target: TargetRef & {
    type: "static_fixture";
  };
  capabilities: CapabilitySet;
  inputs: {
    experimentContextPath: string;
    signalIds: string[];
  };
  learningGoals: string[];
  prompts: StudyTaskPrompt[];
  suggestedMetrics: SuggestedMetric[];
  requiredArtifacts: string[];
  notebookStarter: {
    path: string;
  };
  runStoreGuidance: {
    campaign: string;
    runType: string;
  };
  observatoryGuidance?: {
    suggestedComparison: string;
  } | undefined;
  limitations: string[];
}

export interface Scenario {
  kind: "openplazma.scenario";
  version: "0.1.0";
  scenarioId: string;
  title: string;
  summary: string;
  level: StudyTaskLevel;
  taskIds: string[];
  limitations: string[];
}

export interface StudyTaskManifestEntry {
  taskId: string;
  path: string;
  scenarioId: string;
}

export interface StudyTaskManifest {
  kind: "openplazma.study_task_manifest";
  version: "0.1.0";
  tasks: StudyTaskManifestEntry[];
  inspiredBy?: InspiredBySource | undefined;
}
