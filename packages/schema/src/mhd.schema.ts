import { z } from "zod";
import type { MhdAnalysisBundle } from "@openplazma/core";

const versionSchema = z.literal("0.1.0");
const timeRangeSchema = z.tuple([z.number().finite(), z.number().finite()]);
const provenanceKindSchema = z.enum(["fixture", "measured", "derived", "synthetic"]);

const probeGeometrySchema = z.object({
  poloidalAngleRad: z.number().finite(),
  toroidalAngleRad: z.number().finite(),
  majorRadiusM: z.number().finite().positive(),
  minorRadiusM: z.number().finite().positive().optional()
});

const diagnosticChannelSchema = z.object({
  kind: z.literal("openplazma.diagnostic_channel"),
  version: versionSchema,
  channelId: z.string().min(1),
  label: z.string().min(1),
  signalId: z.string().min(1),
  diagnosticKind: z.enum(["magnetic_probe", "flux_loop"]),
  geometry: probeGeometrySchema
});

const diagnosticArraySchema = z.object({
  kind: z.literal("openplazma.diagnostic_array"),
  version: versionSchema,
  arrayId: z.string().min(1),
  label: z.string().min(1),
  arrayKind: z.enum(["mirnov_toroidal", "mirnov_poloidal"]),
  channels: z.array(diagnosticChannelSchema).min(1)
});

const phenomenonEventSchema = z.object({
  kind: z.literal("openplazma.phenomenon_event"),
  version: versionSchema,
  eventId: z.string().min(1),
  phenomenon: z.enum([
    "mode_onset",
    "rotation_slowdown",
    "mode_locking",
    "current_quench",
    "disruption",
    "elm_crash",
    "sawtooth_crash",
    "ntm_onset",
    "ntm_saturation",
    "radiative_collapse",
    "density_limit"
  ]),
  label: z.string().min(1),
  timeRange: timeRangeSchema,
  signalId: z.string().min(1).optional(),
  producedByInferenceId: z.string().min(1).optional(),
  evidenceReadoutIds: z.array(z.string().min(1)).optional(),
  notes: z.string().min(1).optional()
});

const tearingModeHypothesisSchema = z.object({
  poloidalModeNumber: z.number().int(),
  toroidalModeNumber: z.number().int(),
  amplitude: z.number().finite(),
  rotationFreqHz: z.number().finite(),
  phaseRad: z.number().finite(),
  timeRange: timeRangeSchema
});

const observationModelSchema = z.object({
  kind: z.literal("openplazma.observation_model"),
  version: versionSchema,
  modelId: z.string().min(1),
  label: z.string().min(1),
  modelType: z.literal("analytic_tearing_mode"),
  targetArrayId: z.string().min(1),
  hypothesis: tearingModeHypothesisSchema,
  producedSignalIds: z.array(z.string().min(1)),
  assumptions: z.array(z.string().min(1)),
  limitations: z.array(z.string().min(1))
});

const modeNumberEstimateSchema = z.object({
  toroidalModeNumber: z.number().int(),
  poloidalModeNumber: z.number().int().optional(),
  confidence: z.number().min(0).max(1),
  method: z.enum(["phase_fit_toroidal", "phase_fit_poloidal"]),
  islandWidthM: z.number().finite().nonnegative().optional()
});

const rotationTrackPointSchema = z.object({
  time: z.number().finite(),
  rotationFreqHz: z.number().finite(),
  amplitude: z.number().finite()
});

const mhdObservationStatementSchema = z.object({
  kind: z.literal("openplazma.mhd_observation_statement"),
  version: versionSchema,
  readoutId: z.string().min(1),
  readoutKind: z.enum([
    "phase_fit",
    "frequency_track",
    "threshold_crossing",
    "event_detection",
    "elm_detection",
    "model_readout",
    "manual_annotation",
    "unknown"
  ]),
  observable: z.enum([
    "magnetic_field",
    "electric_current",
    "loop_voltage",
    "radiation",
    "light_intensity",
    "stored_energy",
    "density",
    "motion",
    "unknown"
  ]),
  signalId: z.string().min(1).optional(),
  arrayId: z.string().min(1).optional(),
  observationModelId: z.string().min(1).optional(),
  inferenceId: z.string().min(1).optional(),
  eventId: z.string().min(1).optional(),
  method: z.string().min(1),
  status: z.enum(["detected", "not_detected", "candidate", "inconclusive", "unknown"]),
  timeRange: timeRangeSchema.optional(),
  value: z.number().finite().optional(),
  unit: z.string().min(1).optional(),
  assumptions: z.array(z.string().min(1)),
  limitations: z.array(z.string().min(1)).min(1),
  alternatives: z.array(z.string().min(1))
});

const inferenceSchema = z.object({
  kind: z.literal("openplazma.inference"),
  version: versionSchema,
  inferenceId: z.string().min(1),
  label: z.string().min(1),
  method: z.literal("magnetic_mode_phase_fit"),
  sourceArrayId: z.string().min(1),
  evidenceReadoutIds: z.array(z.string().min(1)),
  modeEstimate: modeNumberEstimateSchema,
  rotationTrack: z.array(rotationTrackPointSchema),
  lockingDetected: z.boolean(),
  lockTimeRange: timeRangeSchema.optional(),
  assumptions: z.array(z.string().min(1)),
  limitations: z.array(z.string().min(1)),
  alternatives: z.array(z.string().min(1))
});

const evidenceLinkSchema = z.object({
  kind: z.literal("openplazma.evidence_link"),
  version: versionSchema,
  verdict: z.enum(["support", "contradict", "inconclusive"]),
  signalId: z.string().min(1).optional(),
  arrayId: z.string().min(1).optional(),
  readoutId: z.string().min(1).optional(),
  inferenceId: z.string().min(1).optional(),
  eventId: z.string().min(1).optional(),
  method: z.string().min(1),
  timeRange: timeRangeSchema,
  rationale: z.string().min(1),
  assumptions: z.array(z.string().min(1)),
  limitations: z.array(z.string().min(1)).min(1),
  alternatives: z.array(z.string().min(1))
});

const claimSchema = z.object({
  kind: z.literal("openplazma.claim"),
  version: versionSchema,
  claimId: z.string().min(1),
  statement: z.string().min(1),
  observationModelId: z.string().min(1).optional(),
  inferenceId: z.string().min(1).optional(),
  elmAnalysisId: z.string().min(1).optional(),
  eventIds: z.array(z.string().min(1)).optional(),
  evidence: z.array(evidenceLinkSchema)
});

const elmCrashSchema = z.object({
  time: z.number().finite(),
  amplitude: z.number().finite()
});

const elmAnalysisSchema = z.object({
  kind: z.literal("openplazma.elm_analysis"),
  version: versionSchema,
  analysisId: z.string().min(1),
  label: z.string().min(1),
  sourceSignalId: z.string().min(1),
  crashes: z.array(elmCrashSchema),
  elmFrequencyHz: z.number().finite().nonnegative(),
  regularity: z.number().min(0).max(1),
  classification: z.enum(["type_I", "type_III", "unknown"]),
  assumptions: z.array(z.string().min(1)),
  limitations: z.array(z.string().min(1))
});

export const mhdAnalysisBundleSchema = z
  .object({
    kind: z.literal("openplazma.mhd_analysis_bundle"),
    version: versionSchema,
    arrays: z.array(diagnosticArraySchema),
    events: z.array(phenomenonEventSchema),
    observationModels: z.array(observationModelSchema),
    inferences: z.array(inferenceSchema),
    readouts: z.array(mhdObservationStatementSchema).optional(),
    claims: z.array(claimSchema),
    provenanceKind: provenanceKindSchema,
    elmAnalyses: z.array(elmAnalysisSchema).optional()
  })
  .superRefine((bundle, ctx) => {
    const arrayIds = new Set(bundle.arrays.map((array) => array.arrayId));
    const modelIds = new Set(bundle.observationModels.map((model) => model.modelId));
    const inferenceIds = new Set(bundle.inferences.map((inference) => inference.inferenceId));
    const elmIds = new Set((bundle.elmAnalyses ?? []).map((elm) => elm.analysisId));
    const eventIds = new Set(bundle.events.map((event) => event.eventId));
    const readoutIds = new Set<string>();

    const isEmpty =
      bundle.arrays.length === 0 &&
      bundle.observationModels.length === 0 &&
      bundle.inferences.length === 0 &&
      bundle.events.length === 0 &&
      bundle.claims.length === 0 &&
      (bundle.readouts ?? []).length === 0 &&
      (bundle.elmAnalyses ?? []).length === 0;
    if (isEmpty) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "an MHD analysis bundle must contain at least one array, model, inference, ELM analysis, event, or claim",
        path: []
      });
    }

    for (const model of bundle.observationModels) {
      if (!arrayIds.has(model.targetArrayId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `observation model '${model.modelId}' targets unknown array '${model.targetArrayId}'`,
          path: ["observationModels"]
        });
      }
    }

    for (const [index, readout] of (bundle.readouts ?? []).entries()) {
      if (readoutIds.has(readout.readoutId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `duplicate mediated MHD readout id '${readout.readoutId}'`,
          path: ["readouts", index, "readoutId"]
        });
      }
      readoutIds.add(readout.readoutId);
      if (readout.arrayId !== undefined && !arrayIds.has(readout.arrayId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `mediated MHD readout '${readout.readoutId}' references unknown array '${readout.arrayId}'`,
          path: ["readouts", index, "arrayId"]
        });
      }
      if (readout.observationModelId !== undefined && !modelIds.has(readout.observationModelId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `mediated MHD readout '${readout.readoutId}' references unknown observation model '${readout.observationModelId}'`,
          path: ["readouts", index, "observationModelId"]
        });
      }
      if (readout.inferenceId !== undefined && !inferenceIds.has(readout.inferenceId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `mediated MHD readout '${readout.readoutId}' references unknown inference '${readout.inferenceId}'`,
          path: ["readouts", index, "inferenceId"]
        });
      }
      if (readout.eventId !== undefined && !eventIds.has(readout.eventId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `mediated MHD readout '${readout.readoutId}' references unknown event '${readout.eventId}'`,
          path: ["readouts", index, "eventId"]
        });
      }
    }

    for (const inference of bundle.inferences) {
      if (!arrayIds.has(inference.sourceArrayId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `inference '${inference.inferenceId}' references unknown array '${inference.sourceArrayId}'`,
          path: ["inferences"]
        });
      }
      if (inference.evidenceReadoutIds.length === 0) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `inference '${inference.inferenceId}' requires mediated readout evidence`,
          path: ["inferences"]
        });
      }
      for (const readoutId of inference.evidenceReadoutIds) {
        if (!readoutIds.has(readoutId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `inference '${inference.inferenceId}' references unknown mediated readout '${readoutId}'`,
            path: ["inferences"]
          });
        }
      }
    }

    for (const event of bundle.events) {
      if (event.producedByInferenceId !== undefined && !inferenceIds.has(event.producedByInferenceId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `phenomenon event '${event.eventId}' references unknown inference '${event.producedByInferenceId}'`,
          path: ["events"]
        });
      }
      for (const readoutId of event.evidenceReadoutIds ?? []) {
        if (!readoutIds.has(readoutId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `phenomenon event '${event.eventId}' references unknown mediated readout '${readoutId}'`,
            path: ["events"]
          });
        }
      }
      if (event.producedByInferenceId === undefined && (event.evidenceReadoutIds ?? []).length === 0) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `phenomenon event '${event.eventId}' must be produced by inference or cite mediated readout evidence`,
          path: ["events"]
        });
      }
    }

    for (const claim of bundle.claims) {
      if (
        claim.observationModelId === undefined &&
        claim.inferenceId === undefined &&
        claim.elmAnalysisId === undefined &&
        (claim.eventIds ?? []).length === 0
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `claim '${claim.claimId}' must reference an observation model, inference, ELM analysis, or events`,
          path: ["claims"]
        });
      }
      if (claim.evidence.length === 0) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `claim '${claim.claimId}' requires evidence`,
          path: ["claims"]
        });
      }
      for (const eventId of claim.eventIds ?? []) {
        if (!eventIds.has(eventId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `claim '${claim.claimId}' references unknown event '${eventId}'`,
            path: ["claims"]
          });
        }
      }
      if (claim.observationModelId !== undefined && !modelIds.has(claim.observationModelId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `claim '${claim.claimId}' references unknown observation model '${claim.observationModelId}'`,
          path: ["claims"]
        });
      }
      if (claim.elmAnalysisId !== undefined && !elmIds.has(claim.elmAnalysisId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `claim '${claim.claimId}' references unknown ELM analysis '${claim.elmAnalysisId}'`,
          path: ["claims"]
        });
      }
      if (claim.inferenceId !== undefined && !inferenceIds.has(claim.inferenceId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `claim '${claim.claimId}' references unknown inference '${claim.inferenceId}'`,
          path: ["claims"]
        });
      }
      for (const link of claim.evidence) {
        const hasMediatedReference = link.readoutId !== undefined || link.inferenceId !== undefined;
        if (
          link.signalId === undefined &&
          link.arrayId === undefined &&
          link.readoutId === undefined &&
          link.inferenceId === undefined &&
          link.eventId === undefined
        ) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `claim '${claim.claimId}' evidence must reference a signal, array, readout, inference, or event`,
            path: ["claims"]
          });
        }
        if (link.arrayId !== undefined && !arrayIds.has(link.arrayId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `claim '${claim.claimId}' evidence references unknown array '${link.arrayId}'`,
            path: ["claims"]
          });
        }
        if (link.readoutId !== undefined && !readoutIds.has(link.readoutId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `claim '${claim.claimId}' evidence references unknown mediated readout '${link.readoutId}'`,
            path: ["claims"]
          });
        }
        if (link.inferenceId !== undefined && !inferenceIds.has(link.inferenceId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `claim '${claim.claimId}' evidence references unknown inference '${link.inferenceId}'`,
            path: ["claims"]
          });
        }
        if (link.eventId !== undefined && !eventIds.has(link.eventId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `claim '${claim.claimId}' evidence references unknown event '${link.eventId}'`,
            path: ["claims"]
          });
        }
        if (link.eventId !== undefined && !hasMediatedReference) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `claim '${claim.claimId}' cannot use bare event evidence`,
            path: ["claims"]
          });
        }
        if (!hasMediatedReference) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `claim '${claim.claimId}' evidence must reference a mediated readout or inference`,
            path: ["claims"]
          });
        }
      }
    }
  });

export function parseMhdAnalysisBundle(input: unknown): MhdAnalysisBundle {
  return mhdAnalysisBundleSchema.parse(input) as MhdAnalysisBundle;
}
