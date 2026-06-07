import { z } from "zod";
import type { ArtifactRecord, EventRecord, MetricRecord, RunManifest, RunRecord } from "@openplazma/core";

const isoDateTimeSchema = z.string().datetime({ offset: true });
const versionSchema = z.literal("0.1.0");
const providerSchema = z.enum(["STATIC_FIXTURE", "LOCAL_SIGNAL_FILE"]);
const inspiredBySchema = z.literal("FAIR_MAST");
const validationStatusSchema = z.literal("schema_validated");
const sha256Schema = z.string().regex(/^[a-f0-9]{64}$/);

const sourceRefSchema = z
  .object({
    provider: providerSchema,
    sourceLabel: z.string().min(1),
    inspiredBy: inspiredBySchema.optional(),
    uri: z.string().min(1).optional(),
    sha256: sha256Schema.optional(),
    validationStatus: validationStatusSchema.optional()
  })
  .superRefine((source, ctx) => {
    if (source.provider === "LOCAL_SIGNAL_FILE") {
      for (const field of ["uri", "sha256", "validationStatus"] as const) {
        if (source[field] === undefined) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "LOCAL_SIGNAL_FILE source requires uri, sha256, and validationStatus",
            path: [field]
          });
        }
      }
    }
  });

const capabilitiesSchema = z.object({
  readData: z.literal(true),
  writeArtifacts: z.literal(true),
  runSimulation: z.literal(false),
  submitComputeJob: z.literal(false),
  readFacilityTelemetry: z.literal(false),
  controlFacility: z.literal(false)
});

const metadataSchema = z.record(z.unknown());

const artifactPathSchema = z
  .string()
  .min(1)
  .refine((path) => path.startsWith("artifacts/"), "artifact path must live under artifacts/")
  .refine((path) => !path.includes(".."), "artifact path must not contain path traversal");

export const runRecordSchema = z.object({
  kind: z.literal("openplazma.run"),
  version: versionSchema,
  runId: z.string().regex(/^OPR-\d{8}-\d{6}$/),
  project: z.string().min(1),
  campaign: z.string().min(1),
  runType: z.string().min(1),
  status: z.enum(["running", "finished", "failed"]),
  createdAt: isoDateTimeSchema,
  updatedAt: isoDateTimeSchema,
  finishedAt: isoDateTimeSchema.nullish(),
  target: z.object({
    type: z.literal("local_run_store"),
    id: z.string().min(1),
    label: z.string().min(1)
  }),
  source: sourceRefSchema,
  capabilities: capabilitiesSchema,
  contextRef: z
    .object({
      artifactName: z.string().min(1),
      artifactType: z.string().min(1)
    })
    .nullable(),
  artifactCount: z.number().int().nonnegative(),
  metricCount: z.number().int().nonnegative(),
  limitations: z.array(z.string().min(1)).min(1)
});

export const metricRecordSchema = z.object({
  kind: z.literal("openplazma.metric"),
  version: versionSchema,
  runId: z.string().regex(/^OPR-\d{8}-\d{6}$/),
  name: z.string().min(1),
  value: z.union([z.string(), z.number().finite(), z.boolean(), z.null(), z.record(z.unknown()), z.array(z.unknown())]),
  step: z.number().int().nonnegative().nullable().optional(),
  createdAt: isoDateTimeSchema
});

export const artifactRecordSchema = z.object({
  kind: z.literal("openplazma.artifact"),
  version: versionSchema,
  artifactId: z.string().regex(/^OPA-\d{8}-\d{6}$/),
  runId: z.string().regex(/^OPR-\d{8}-\d{6}$/),
  name: z.string().min(1),
  type: z.string().min(1),
  path: artifactPathSchema,
  sha256: z.string().regex(/^[a-f0-9]{64}$/),
  createdAt: isoDateTimeSchema,
  metadata: metadataSchema
});

export const eventRecordSchema = z.object({
  kind: z.literal("openplazma.event"),
  version: versionSchema,
  runId: z.string().regex(/^OPR-\d{8}-\d{6}$/),
  eventType: z.enum(["run_started", "metric_logged", "artifact_logged", "run_finished", "run_failed"]),
  createdAt: isoDateTimeSchema,
  message: z.string().min(1),
  metadata: metadataSchema
});

export const runManifestSchema = z.object({
  kind: z.literal("openplazma.run_manifest"),
  version: versionSchema,
  runId: z.string().regex(/^OPR-\d{8}-\d{6}$/),
  createdAt: isoDateTimeSchema,
  updatedAt: isoDateTimeSchema,
  artifacts: z.array(artifactRecordSchema)
});

export function parseRunRecord(input: unknown): RunRecord {
  return runRecordSchema.parse(input) as RunRecord;
}

export function parseMetricRecord(input: unknown): MetricRecord {
  return metricRecordSchema.parse(input) as MetricRecord;
}

export function parseArtifactRecord(input: unknown): ArtifactRecord {
  return artifactRecordSchema.parse(input) as ArtifactRecord;
}

export function parseEventRecord(input: unknown): EventRecord {
  return eventRecordSchema.parse(input) as EventRecord;
}

export function parseRunManifest(input: unknown): RunManifest {
  return runManifestSchema.parse(input) as RunManifest;
}
