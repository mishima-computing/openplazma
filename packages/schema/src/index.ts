import { z } from "zod";
import type {
  ExperimentContext,
  FixtureManifest,
  ShotMetadata,
  SignalSeries,
  StudyRecord
} from "@openplazma/core";

const isoDateTimeSchema = z.string().datetime({ offset: true });

export const experimentContextSchema: z.ZodType<ExperimentContext> = z.object({
  projectId: z.string().min(1),
  datasetId: z.string().min(1),
  facility: z.string().min(1),
  campaign: z.string().min(1).optional(),
  description: z.string().min(1),
  safetyClassification: z.literal("public-educational-fixture"),
  createdAt: isoDateTimeSchema
});

export const shotMetadataSchema: z.ZodType<ShotMetadata> = z.object({
  shotId: z.string().min(1),
  displayName: z.string().min(1),
  deviceName: z.string().min(1),
  recordedAt: isoDateTimeSchema,
  source: z.object({
    kind: z.enum(["fixture", "measured", "derived", "synthetic"]),
    provider: z.enum(["STATIC_FIXTURE", "FAIR_MAST"]),
    inspiredBy: z.literal("FAIR_MAST").optional(),
    uri: z.string().min(1),
    license: z.string().min(1)
  }),
  signalIds: z.array(z.string().min(1)).min(1),
  tags: z.array(z.string().min(1)),
  notes: z.string().min(1).optional()
});

export const signalSeriesSchema: z.ZodType<SignalSeries> = z
  .object({
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

export const studyRecordSchema: z.ZodType<StudyRecord> = z
  .object({
    schemaVersion: z.literal("0.1.0"),
    context: experimentContextSchema,
    shot: shotMetadataSchema,
    signals: z.array(signalSeriesSchema).min(1)
  })
  .superRefine((record, ctx) => {
    const declaredSignalIds = new Set(record.shot.signalIds);
    const actualSignalIds = new Set(record.signals.map((signal) => signal.signalId));

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
  });

export const fixtureManifestSchema: z.ZodType<FixtureManifest> = z.object({
  schemaVersion: z.literal("0.1.0"),
  provider: z.literal("STATIC_FIXTURE"),
  inspiredBy: z.literal("FAIR_MAST").optional(),
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
  return studyRecordSchema.parse(input);
}

export function parseExperimentContext(input: unknown): ExperimentContext {
  return experimentContextSchema.parse(input);
}

export function parseFixtureManifest(input: unknown): FixtureManifest {
  return fixtureManifestSchema.parse(input);
}
