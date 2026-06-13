import { z } from "zod";
import type {
  ArtifactRecord,
  EventRecord,
  MetricRecord,
  RunManifest,
  RunRecord,
  RunStoreBackendDescriptor,
  RunStoreMetadata
} from "@openplazma/core";

const isoDateTimeSchema = z.string().datetime({ offset: true });
const versionSchema = z.literal("0.1.0");
const runIdSchema = z.string().regex(/^OPR-\d{8}(?:-\d{6,}|-[A-Za-z0-9_.-]+-[a-f0-9]{12})$/);
const artifactIdSchema = z.string().regex(/^OPA-\d{8}-\d{6,}$/);
const storeIdSchema = z.string().regex(/^OPS-[a-f0-9]{32}$/);
const safeIdentitySchema = z
  .string()
  .regex(/^[A-Za-z0-9_.-]+$/)
  .refine((value) => value !== "." && value !== "..", "identity must not be . or ..");
const providerSchema = z.enum(["STATIC_FIXTURE", "LOCAL_SIGNAL_FILE", "NOAA_SWPC"]);
const inspiredBySchema = z.literal("FAIR_MAST");
const validationStatusSchema = z.literal("schema_validated");
const sha256Schema = z.string().regex(/^[a-f0-9]{64}$/);

function isAtOrAfter(actual: string, minimum: string): boolean {
  return Date.parse(actual) >= Date.parse(minimum);
}

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
    if (source.provider === "LOCAL_SIGNAL_FILE" || source.provider === "NOAA_SWPC") {
      for (const field of ["uri", "sha256", "validationStatus"] as const) {
        if (source[field] === undefined) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `${source.provider} source requires uri, sha256, and validationStatus`,
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

const jsonValueSchema: z.ZodType<unknown> = z.lazy(() =>
  z.union([
    z.string(),
    z.number().finite(),
    z.boolean(),
    z.null(),
    z.array(jsonValueSchema),
    z.record(jsonValueSchema)
  ])
);

const metadataSchema = z.record(jsonValueSchema);

const artifactPathSchema = z
  .string()
  .min(1)
  .refine((path) => path.startsWith("artifacts/"), "artifact path must live under artifacts/")
  .refine((path) => !path.includes(".."), "artifact path must not contain path traversal");

export const artifactBlobRefSchema = z
  .object({
    kind: z.literal("openplazma.artifact_blob_ref"),
    version: versionSchema,
    algorithm: z.literal("sha256"),
    digest: sha256Schema,
    path: z.string().min(1),
    byteSize: z.number().int().nonnegative(),
    mediaType: z.string().min(1).optional()
  })
  .superRefine((blob, ctx) => {
    const expectedPath = `blobs/sha256/${blob.digest.slice(0, 2)}/${blob.digest}`;
    if (blob.path !== expectedPath) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "ArtifactBlobRef.path must match digest",
        path: ["path"]
      });
    }
  });

export const runRecordSchema = z
  .object({
    kind: z.literal("openplazma.run"),
    version: versionSchema,
    runId: runIdSchema,
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
    storeId: storeIdSchema.optional(),
    machineId: safeIdentitySchema.optional(),
    runGroupId: safeIdentitySchema.nullish(),
    partitionId: safeIdentitySchema.nullish(),
    contextRef: z
      .object({
        artifactName: z.string().min(1),
        artifactType: z.string().min(1)
      })
      .nullable(),
    artifactCount: z.number().int().nonnegative(),
    metricCount: z.number().int().nonnegative(),
    limitations: z.array(z.string().min(1)).min(1)
  })
  .superRefine((record, ctx) => {
    if (!isAtOrAfter(record.updatedAt, record.createdAt)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "RunRecord.updatedAt must be at or after createdAt",
        path: ["updatedAt"]
      });
    }
    if (record.finishedAt != null && !isAtOrAfter(record.finishedAt, record.updatedAt)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "RunRecord.finishedAt must be at or after updatedAt",
        path: ["finishedAt"]
      });
    }
    if (record.status === "running" && record.finishedAt != null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "running RunRecord must not include finishedAt",
        path: ["finishedAt"]
      });
    }
    if ((record.status === "finished" || record.status === "failed") && record.finishedAt == null) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "terminal RunRecord requires finishedAt",
        path: ["finishedAt"]
      });
    }
  });

export const metricRecordSchema = z.object({
  kind: z.literal("openplazma.metric"),
  version: versionSchema,
  runId: runIdSchema,
  name: z.string().min(1),
  value: jsonValueSchema,
  step: z.number().int().nonnegative().nullable().optional(),
  createdAt: isoDateTimeSchema
});

export const artifactRecordSchema = z.object({
  kind: z.literal("openplazma.artifact"),
  version: versionSchema,
  artifactId: artifactIdSchema,
  runId: runIdSchema,
  name: z.string().min(1),
  type: z.string().min(1),
  path: artifactPathSchema,
  sha256: z.string().regex(/^[a-f0-9]{64}$/),
  byteSize: z.number().int().nonnegative().optional(),
  blobRef: artifactBlobRefSchema.optional(),
  createdAt: isoDateTimeSchema,
  metadata: metadataSchema
});

export const eventRecordSchema = z.object({
  kind: z.literal("openplazma.event"),
  version: versionSchema,
  runId: runIdSchema,
  eventType: z.enum(["run_started", "metric_logged", "artifact_logged", "run_finished", "run_failed"]),
  machineId: safeIdentitySchema.optional(),
  createdAt: isoDateTimeSchema,
  message: z.string().min(1),
  metadata: metadataSchema
});

export const runManifestSchema = z
  .object({
    kind: z.literal("openplazma.run_manifest"),
    version: versionSchema,
    runId: runIdSchema,
    createdAt: isoDateTimeSchema,
    updatedAt: isoDateTimeSchema,
    artifacts: z.array(artifactRecordSchema)
  })
  .superRefine((manifest, ctx) => {
    if (!isAtOrAfter(manifest.updatedAt, manifest.createdAt)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "RunManifest.updatedAt must be at or after createdAt",
        path: ["updatedAt"]
      });
    }
    const artifactIds = new Set<string>();
    const artifactPaths = new Set<string>();
    manifest.artifacts.forEach((artifact, index) => {
      if (!isAtOrAfter(artifact.createdAt, manifest.createdAt)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "ArtifactRecord.createdAt must be at or after RunManifest.createdAt",
          path: ["artifacts", index, "createdAt"]
        });
      }
      if (!isAtOrAfter(manifest.updatedAt, artifact.createdAt)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "RunManifest.updatedAt must be at or after ArtifactRecord.createdAt",
          path: ["updatedAt"]
        });
      }
      if (artifactIds.has(artifact.artifactId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "duplicate artifact id in RunManifest",
          path: ["artifacts", index, "artifactId"]
        });
      }
      if (artifactPaths.has(artifact.path)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "duplicate artifact path in RunManifest",
          path: ["artifacts", index, "path"]
        });
      }
      artifactIds.add(artifact.artifactId);
      artifactPaths.add(artifact.path);
    });
  });

export const runStoreObservatoryDescriptorSchema = z.object({
  observatoryId: safeIdentitySchema,
  label: z.string().min(1),
  dataScope: z.enum(["local_snapshot", "public_snapshot", "unknown"]),
  liveFetch: z.literal(false),
  remoteTelemetry: z.literal(false),
  limitations: z.array(z.string().min(1)).min(1)
});

export const runStoreBackendDescriptorSchema = z.object({
  backendKind: z.string().min(1),
  accessMode: z.enum(["read_write_artifacts", "read_only_snapshot"]),
  rootUri: z.string().min(1).optional(),
  observatory: runStoreObservatoryDescriptorSchema.optional(),
  liveFetch: z.literal(false),
  remoteTelemetry: z.literal(false),
  controlPlane: z.literal(false),
  description: z.string().min(1),
  limitations: z.array(z.string().min(1)).min(1)
});

export const runStoreMetadataSchema = z
  .object({
    kind: z.literal("openplazma.run_store"),
    version: versionSchema,
    layoutVersion: z.string().min(1),
    storeId: storeIdSchema,
    backendKind: z.string().min(1),
    backend: runStoreBackendDescriptorSchema.optional(),
    createdAt: isoDateTimeSchema,
    machineId: safeIdentitySchema.optional(),
    limitations: z.array(z.string().min(1)).optional()
  })
  .superRefine((metadata, ctx) => {
    if (metadata.backend !== undefined && metadata.backend.backendKind !== metadata.backendKind) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "RunStore backend descriptor kind must match backendKind",
        path: ["backend", "backendKind"]
      });
    }
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

export function parseRunStoreMetadata(input: unknown): RunStoreMetadata {
  return runStoreMetadataSchema.parse(input) as RunStoreMetadata;
}

export function parseRunStoreBackendDescriptor(input: unknown): RunStoreBackendDescriptor {
  return runStoreBackendDescriptorSchema.parse(input) as RunStoreBackendDescriptor;
}
