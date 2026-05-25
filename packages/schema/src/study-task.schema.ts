import { z } from "zod";
import type { Scenario, StudyTask, StudyTaskManifest } from "@openplazma/core";

const versionSchema = z.literal("0.1.0");
const providerSchema = z.literal("STATIC_FIXTURE");
const inspiredBySchema = z.literal("FAIR_MAST");

const sourceRefSchema = z.object({
  provider: providerSchema,
  sourceLabel: z.string().min(1),
  inspiredBy: inspiredBySchema.optional()
});

const staticFixtureTargetSchema = z.object({
  type: z.literal("static_fixture"),
  id: z.string().min(1),
  label: z.string().min(1)
});

const capabilitiesSchema = z.object({
  readData: z.literal(true),
  writeArtifacts: z.literal(true),
  runSimulation: z.literal(false),
  submitComputeJob: z.literal(false),
  readFacilityTelemetry: z.literal(false),
  controlFacility: z.literal(false)
});

const levelSchema = z.enum(["beginner", "intermediate", "advanced"]);

export const studyTaskSchema = z.object({
  kind: z.literal("openplazma.study_task"),
  version: versionSchema,
  taskId: z.string().min(1),
  scenarioId: z.string().min(1),
  title: z.string().min(1),
  summary: z.string().min(1),
  level: levelSchema,
  estimatedMinutes: z.number().int().positive(),
  source: sourceRefSchema,
  target: staticFixtureTargetSchema,
  capabilities: capabilitiesSchema,
  inputs: z.object({
    experimentContextPath: z.string().min(1),
    signalIds: z.array(z.string().min(1)).min(1)
  }),
  learningGoals: z.array(z.string().min(1)).min(1),
  prompts: z
    .array(
      z.object({
        promptId: z.string().min(1),
        type: z.enum(["observation", "hypothesis", "reflection"]),
        text: z.string().min(1)
      })
    )
    .min(1),
  suggestedMetrics: z
    .array(
      z.object({
        name: z.string().min(1),
        description: z.string().min(1)
      })
    )
    .min(1),
  requiredArtifacts: z.array(z.string().min(1)).min(1),
  notebookStarter: z.object({
    path: z.string().min(1)
  }),
  runStoreGuidance: z.object({
    campaign: z.string().min(1),
    runType: z.string().min(1)
  }),
  observatoryGuidance: z
    .object({
      suggestedComparison: z.string().min(1)
    })
    .optional(),
  limitations: z.array(z.string().min(1)).min(1)
});

export const scenarioSchema = z.object({
  kind: z.literal("openplazma.scenario"),
  version: versionSchema,
  scenarioId: z.string().min(1),
  title: z.string().min(1),
  summary: z.string().min(1),
  level: levelSchema,
  taskIds: z.array(z.string().min(1)).min(1),
  limitations: z.array(z.string().min(1)).min(1)
});

export const studyTaskManifestSchema = z.object({
  kind: z.literal("openplazma.study_task_manifest"),
  version: versionSchema,
  tasks: z
    .array(
      z.object({
        taskId: z.string().min(1),
        path: z.string().min(1),
        scenarioId: z.string().min(1)
      })
    )
    .min(1),
  inspiredBy: inspiredBySchema.optional()
});

export function parseStudyTask(input: unknown): StudyTask {
  return studyTaskSchema.parse(input) as StudyTask;
}

export function parseScenario(input: unknown): Scenario {
  return scenarioSchema.parse(input) as Scenario;
}

export function parseStudyTaskManifest(input: unknown): StudyTaskManifest {
  return studyTaskManifestSchema.parse(input) as StudyTaskManifest;
}
