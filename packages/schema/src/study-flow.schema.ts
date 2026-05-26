import { z } from "zod";
import type { StudyFlow, StudyFlowManifest } from "@openplazma/core";

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
const surfaceSchema = z.enum(["lab", "notebook", "runstore", "observatory", "observatory_compare"]);

export const studyFlowSchema = z.object({
  kind: z.literal("openplazma.study_flow"),
  version: versionSchema,
  flowId: z.string().min(1),
  title: z.string().min(1),
  summary: z.string().min(1),
  level: levelSchema,
  estimatedMinutes: z.number().int().positive(),
  scenarioId: z.string().min(1),
  taskIds: z.array(z.string().min(1)).min(1),
  source: sourceRefSchema,
  target: staticFixtureTargetSchema,
  capabilities: capabilitiesSchema,
  steps: z
    .array(
      z.object({
        stepId: z.string().min(1),
        title: z.string().min(1),
        surface: surfaceSchema,
        instruction: z.string().min(1)
      })
    )
    .min(1),
  expectedArtifacts: z.array(z.string().min(1)).min(1),
  expectedMetrics: z.array(z.string().min(1)).min(1),
  completionChecklist: z.array(z.string().min(1)).min(1),
  limitations: z.array(z.string().min(1)).min(1)
});

export const studyFlowManifestSchema = z.object({
  kind: z.literal("openplazma.study_flow_manifest"),
  version: versionSchema,
  flows: z
    .array(
      z.object({
        flowId: z.string().min(1),
        path: z.string().min(1)
      })
    )
    .min(1),
  inspiredBy: inspiredBySchema.optional()
});

export function parseStudyFlow(input: unknown): StudyFlow {
  return studyFlowSchema.parse(input) as StudyFlow;
}

export function parseStudyFlowManifest(input: unknown): StudyFlowManifest {
  return studyFlowManifestSchema.parse(input) as StudyFlowManifest;
}
