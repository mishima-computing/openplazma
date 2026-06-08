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
    "disruption"
  ]),
  label: z.string().min(1),
  timeRange: timeRangeSchema,
  signalId: z.string().min(1).optional(),
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
  method: z.enum(["phase_fit_toroidal", "phase_fit_poloidal"])
});

const rotationTrackPointSchema = z.object({
  time: z.number().finite(),
  rotationFreqHz: z.number().finite(),
  amplitude: z.number().finite()
});

const inferenceSchema = z.object({
  kind: z.literal("openplazma.inference"),
  version: versionSchema,
  inferenceId: z.string().min(1),
  label: z.string().min(1),
  method: z.literal("magnetic_mode_phase_fit"),
  sourceArrayId: z.string().min(1),
  modeEstimate: modeNumberEstimateSchema,
  rotationTrack: z.array(rotationTrackPointSchema),
  lockingDetected: z.boolean(),
  lockTimeRange: timeRangeSchema.optional(),
  assumptions: z.array(z.string().min(1)),
  limitations: z.array(z.string().min(1))
});

const evidenceLinkSchema = z.object({
  kind: z.literal("openplazma.evidence_link"),
  version: versionSchema,
  verdict: z.enum(["support", "contradict", "inconclusive"]),
  signalId: z.string().min(1).optional(),
  arrayId: z.string().min(1).optional(),
  timeRange: timeRangeSchema,
  rationale: z.string().min(1)
});

const claimSchema = z.object({
  kind: z.literal("openplazma.claim"),
  version: versionSchema,
  claimId: z.string().min(1),
  statement: z.string().min(1),
  observationModelId: z.string().min(1),
  inferenceId: z.string().min(1).optional(),
  evidence: z.array(evidenceLinkSchema)
});

export const mhdAnalysisBundleSchema = z
  .object({
    kind: z.literal("openplazma.mhd_analysis_bundle"),
    version: versionSchema,
    arrays: z.array(diagnosticArraySchema).min(1),
    events: z.array(phenomenonEventSchema),
    observationModels: z.array(observationModelSchema).min(1),
    inferences: z.array(inferenceSchema),
    claims: z.array(claimSchema),
    provenanceKind: provenanceKindSchema
  })
  .superRefine((bundle, ctx) => {
    const arrayIds = new Set(bundle.arrays.map((array) => array.arrayId));
    const modelIds = new Set(bundle.observationModels.map((model) => model.modelId));
    const inferenceIds = new Set(bundle.inferences.map((inference) => inference.inferenceId));

    for (const model of bundle.observationModels) {
      if (!arrayIds.has(model.targetArrayId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `observation model '${model.modelId}' targets unknown array '${model.targetArrayId}'`,
          path: ["observationModels"]
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
    }

    for (const claim of bundle.claims) {
      if (!modelIds.has(claim.observationModelId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `claim '${claim.claimId}' references unknown observation model '${claim.observationModelId}'`,
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
        if (link.arrayId !== undefined && !arrayIds.has(link.arrayId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `claim '${claim.claimId}' evidence references unknown array '${link.arrayId}'`,
            path: ["claims"]
          });
        }
      }
    }
  });

export function parseMhdAnalysisBundle(input: unknown): MhdAnalysisBundle {
  return mhdAnalysisBundleSchema.parse(input) as MhdAnalysisBundle;
}
