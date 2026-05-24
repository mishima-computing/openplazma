import { z } from "zod";
import type {
  ExperimentContext,
  FixtureManifest,
  ShotMetadata,
  SignalSeries,
  StudyRecord
} from "@openplazma/core";

const isoDateTimeSchema = z.string().datetime({ offset: true });
const versionSchema = z.literal("0.1.0");
const providerSchema = z.literal("STATIC_FIXTURE");
const inspiredBySchema = z.literal("FAIR_MAST");
const timeRangeSchema = z.tuple([z.number().finite(), z.number().finite()]);

const sourceRefSchema = z.object({
  provider: providerSchema,
  sourceLabel: z.string().min(1),
  inspiredBy: inspiredBySchema.optional()
});

const capabilitiesSchema = z.object({
  readData: z.literal(true),
  writeArtifacts: z.literal(true),
  runSimulation: z.literal(false),
  submitComputeJob: z.literal(false),
  readFacilityTelemetry: z.literal(false),
  controlFacility: z.literal(false)
});

const signalRefSchema = z.object({
  signalId: z.string().min(1),
  label: z.string().min(1).optional(),
  quantity: z.string().min(1).optional(),
  unit: z.string().min(1).optional()
});

const observationSchema = z.object({
  text: z.string().min(1),
  signalId: z.string().min(1).optional(),
  timeRange: timeRangeSchema.optional()
});

export const experimentContextSchema = z.object({
  kind: z.literal("openplazma.experiment_context"),
  version: versionSchema,
  contextId: z.string().min(1),
  projectId: z.string().min(1),
  datasetId: z.string().min(1),
  campaign: z.string().min(1).optional(),
  description: z.string().min(1),
  safetyClassification: z.literal("public-educational-fixture"),
  createdAt: isoDateTimeSchema,
  target: z.object({
    type: z.enum(["static_fixture", "local_run_store"]),
    id: z.string().min(1),
    label: z.string().min(1)
  }),
  source: sourceRefSchema,
  capabilities: capabilitiesSchema,
  shotRef: z.object({
    provider: providerSchema,
    shotId: z.string().min(1)
  }),
  signals: z.array(signalRefSchema).min(1),
  view: z
    .object({
      timeRange: timeRangeSchema.optional()
    })
    .optional(),
  observations: z.array(observationSchema),
  hypothesis: z.string().min(1).optional(),
  limitations: z.array(z.string().min(1)).min(1)
});

export const shotMetadataSchema = z.object({
  kind: z.literal("openplazma.shot_metadata"),
  version: versionSchema,
  shotId: z.string().min(1),
  displayName: z.string().min(1),
  sourceLabel: z.string().min(1),
  deviceName: z.string().min(1).optional(),
  recordedAt: isoDateTimeSchema,
  source: z.object({
    kind: z.enum(["fixture", "measured", "derived", "synthetic"]),
    provider: providerSchema,
    sourceLabel: z.string().min(1),
    inspiredBy: inspiredBySchema.optional(),
    uri: z.string().min(1),
    license: z.string().min(1)
  }),
  signalIds: z.array(z.string().min(1)).min(1),
  tags: z.array(z.string().min(1)),
  notes: z.string().min(1).optional()
});

export const signalSeriesSchema = z
  .object({
    kind: z.literal("openplazma.signal_series"),
    version: versionSchema,
    signalId: z.string().min(1),
    label: z.string().min(1),
    quantity: z.string().min(1),
    unit: z.string().min(1),
    timeUnit: z.literal("s"),
    time: z.array(z.number().finite()).min(1),
    values: z.array(z.number().finite()).min(1)
  })
  .superRefine((series, ctx) => {
    if (series.time.length !== series.values.length) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "time and values arrays must have matching lengths",
        path: ["values"]
      });
    }

    for (let index = 1; index < series.time.length; index += 1) {
      const previous = series.time[index - 1];
      const current = series.time[index];
      if (current === undefined || previous === undefined || current <= previous) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "time values must be strictly increasing",
          path: ["time", index]
        });
      }
    }
  });

export const studyRecordSchema = z
  .object({
    kind: z.literal("openplazma.study_record"),
    version: versionSchema,
    studyId: z.string().min(1),
    createdAt: isoDateTimeSchema,
    source: sourceRefSchema.extend({
      shotId: z.string().min(1)
    }),
    shotRef: z.object({
      provider: providerSchema,
      shotId: z.string().min(1)
    }),
    signalsViewed: z.array(signalRefSchema).min(1),
    observations: z.array(observationSchema),
    hypothesis: z.string().min(1).optional(),
    limitations: z.array(z.string().min(1)).min(1),
    context: experimentContextSchema,
    shot: shotMetadataSchema,
    signals: z.array(signalSeriesSchema).min(1)
  })
  .superRefine((record, ctx) => {
    const declaredSignalIds = new Set(record.shot.signalIds);
    const actualSignalIds = new Set(record.signals.map((signal) => signal.signalId));
    const viewedSignalIds = new Set(record.signalsViewed.map((signal) => signal.signalId));

    if (record.shotRef.provider !== record.shot.source.provider || record.shotRef.shotId !== record.shot.shotId) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "shotRef must match shot metadata",
        path: ["shotRef"]
      });
    }

    for (const signalId of declaredSignalIds) {
      if (!actualSignalIds.has(signalId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `shot metadata references missing signal '${signalId}'`,
          path: ["shot", "signalIds"]
        });
      }
    }

    for (const signal of record.signals) {
      if (!declaredSignalIds.has(signal.signalId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `signal '${signal.signalId}' is not declared in shot metadata`,
          path: ["signals"]
        });
      }
    }

    for (const signalId of viewedSignalIds) {
      if (!actualSignalIds.has(signalId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `viewed signal '${signalId}' is not included in signals`,
          path: ["signalsViewed"]
        });
      }
    }
  });

export const fixtureManifestSchema = z.object({
  kind: z.literal("openplazma.fixture_manifest"),
  version: versionSchema,
  provider: z.literal("STATIC_FIXTURE"),
  inspiredBy: inspiredBySchema.optional(),
  datasetId: z.string().min(1),
  shots: z
    .array(
      z.object({
        shotId: z.string().min(1),
        path: z.string().min(1)
      })
    )
    .min(1)
});

export function parseStudyRecord(input: unknown): StudyRecord {
  return studyRecordSchema.parse(input) as StudyRecord;
}

export function parseExperimentContext(input: unknown): ExperimentContext {
  return experimentContextSchema.parse(input) as ExperimentContext;
}

export function parseFixtureManifest(input: unknown): FixtureManifest {
  return fixtureManifestSchema.parse(input) as FixtureManifest;
}

export {
  artifactRecordSchema,
  eventRecordSchema,
  metricRecordSchema,
  parseArtifactRecord,
  parseEventRecord,
  parseMetricRecord,
  parseRunManifest,
  parseRunRecord,
  runManifestSchema,
  runRecordSchema
} from "./tracking.schema";
