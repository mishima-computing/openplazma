import { z } from "zod";
import type { FusionConditionAssessment, InvestigationPackage } from "@openplazma/core";

const versionSchema = z.literal("0.1.0");

const targetKindSchema = z.enum([
  "atmospheric_light",
  "organism",
  "artifact",
  "spacecraft",
  "stellar_object",
  "unknown"
]);

const candidateEnergySourceSchema = z.enum([
  "chemical_luminescence",
  "combustion",
  "electrical_discharge",
  "plasma",
  "fusion",
  "sensor_artifact",
  "reflection",
  "unknown"
]);

const investigationTargetSchema = z.object({
  kind: z.literal("openplazma.investigation_target"),
  version: versionSchema,
  targetId: z.string().min(1),
  targetKind: targetKindSchema,
  label: z.string().min(1),
  description: z.string().min(1),
  candidateEnergySources: z.array(candidateEnergySourceSchema).min(1),
  limitations: z.array(z.string().min(1)).min(1)
});

const investigationQuestionSchema = z.object({
  questionId: z.string().min(1),
  questionKind: z.enum([
    "energy_source_classification",
    "is_plasma",
    "is_fusion",
    "fusion_conditions",
    "plasma_maintenance"
  ]),
  text: z.string().min(1)
});

const diagnosticArtifactSchema = z.object({
  kind: z.literal("openplazma.diagnostic_artifact"),
  version: versionSchema,
  artifactId: z.string().min(1),
  artifactKind: z.enum([
    "signal_series",
    "spectrum",
    "image_frame",
    "field_map",
    "particle_flux",
    "gravity_trace",
    "event_log",
    "motion_track"
  ]),
  label: z.string().min(1),
  provenanceKind: z.enum(["measured", "derived", "synthetic", "testimony", "unknown"]),
  sourceUri: z.string().min(1).optional(),
  signalIds: z.array(z.string().min(1)).optional(),
  quantity: z.string().min(1).optional(),
  unit: z.string().min(1).optional(),
  description: z.string().min(1),
  limitations: z.array(z.string().min(1)).min(1)
});

const fusionStatusSchema = z.enum([
  "not_assessed",
  "unknown",
  "unsupported",
  "contradicted",
  "plausible",
  "supported"
]);

const conditionModeSchema = z.enum([
  "not_applicable",
  "unknown",
  "forward_from_observations",
  "inverse_from_fusion_condition"
]);

const conditionEstimateSchema = z.object({
  parameter: z.enum([
    "ion_temperature",
    "electron_temperature",
    "density",
    "pressure",
    "confinement_time",
    "triple_product",
    "fuel_mix",
    "gravity",
    "magnetic_field",
    "electric_field",
    "impurity_fraction",
    "radiative_loss",
    "heat_loss",
    "particle_loss",
    "plasma_rotation",
    "turbulence_level"
  ]),
  status: z.enum(["measured", "inferred", "required", "bounded", "unknown", "contradicted"]),
  logicalRole: z.enum(["necessary", "supporting", "contradicting", "unknown"]),
  value: z.number().finite().optional(),
  lowerBound: z.number().finite().optional(),
  upperBound: z.number().finite().optional(),
  unit: z.string().min(1).optional(),
  method: z.string().min(1).optional(),
  evidenceArtifactIds: z.array(z.string().min(1)),
  assumptions: z.array(z.string().min(1)),
  limitations: z.array(z.string().min(1))
});

export const fusionConditionAssessmentSchema = z
  .object({
    kind: z.literal("openplazma.fusion_condition_assessment"),
    version: versionSchema,
    assessmentId: z.string().min(1),
    fusionStatus: fusionStatusSchema,
    conditionMode: conditionModeSchema,
    reactionCandidates: z
      .array(z.enum(["proton_proton_chain", "cno_cycle", "d_t", "d_d", "d_he3", "p_b11", "unknown"]))
      .min(1),
    observedOrInferredConditions: z.array(conditionEstimateSchema),
    requiredConditions: z.array(conditionEstimateSchema),
    unknowns: z.array(z.string().min(1)),
    assumptions: z.array(z.string().min(1)),
    limitations: z.array(z.string().min(1)).min(1)
  })
  .superRefine((assessment, ctx) => {
    if (assessment.conditionMode === "inverse_from_fusion_condition" && assessment.requiredConditions.length === 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "inverse fusion-condition assessment requires at least one required condition",
        path: ["requiredConditions"]
      });
    }

    for (const [index, condition] of assessment.requiredConditions.entries()) {
      if (condition.logicalRole !== "necessary") {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "required fusion conditions must be marked as necessary, not sufficient",
          path: ["requiredConditions", index, "logicalRole"]
        });
      }
    }

    if (
      ["plausible", "supported"].includes(assessment.fusionStatus) &&
      assessment.conditionMode === "not_applicable"
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "plausible or supported fusion status must keep condition assessment open",
        path: ["conditionMode"]
      });
    }
  });

const investigationClaimSchema = z.object({
  kind: z.literal("openplazma.investigation_claim"),
  version: versionSchema,
  claimId: z.string().min(1),
  claimType: z.enum([
    "plasma_presence",
    "fusion_status",
    "fusion_conditions",
    "plasma_maintenance",
    "source_identity"
  ]),
  statement: z.string().min(1),
  status: z.enum(["support", "contradict", "inconclusive", "untested"]),
  evidenceArtifactIds: z.array(z.string().min(1)),
  assumptions: z.array(z.string().min(1)),
  limitations: z.array(z.string().min(1))
});

function checkArtifactRefs(
  artifactIds: Set<string>,
  ids: string[],
  path: Array<string | number>,
  ctx: z.RefinementCtx
): void {
  for (const artifactId of ids) {
    if (!artifactIds.has(artifactId)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `references unknown diagnostic artifact '${artifactId}'`,
        path
      });
    }
  }
}

export const investigationPackageSchema = z
  .object({
    kind: z.literal("openplazma.investigation_package"),
    version: versionSchema,
    packageId: z.string().min(1),
    title: z.string().min(1),
    target: investigationTargetSchema,
    questions: z.array(investigationQuestionSchema).min(1),
    artifacts: z.array(diagnosticArtifactSchema).min(1),
    fusionAssessment: fusionConditionAssessmentSchema,
    claims: z.array(investigationClaimSchema),
    limitations: z.array(z.string().min(1)).min(1)
  })
  .superRefine((pack, ctx) => {
    const artifactIds = new Set(pack.artifacts.map((artifact) => artifact.artifactId));
    for (const [index, estimate] of pack.fusionAssessment.observedOrInferredConditions.entries()) {
      checkArtifactRefs(
        artifactIds,
        estimate.evidenceArtifactIds,
        ["fusionAssessment", "observedOrInferredConditions", index, "evidenceArtifactIds"],
        ctx
      );
    }
    for (const [index, estimate] of pack.fusionAssessment.requiredConditions.entries()) {
      checkArtifactRefs(
        artifactIds,
        estimate.evidenceArtifactIds,
        ["fusionAssessment", "requiredConditions", index, "evidenceArtifactIds"],
        ctx
      );
    }
    for (const [index, claim] of pack.claims.entries()) {
      checkArtifactRefs(artifactIds, claim.evidenceArtifactIds, ["claims", index, "evidenceArtifactIds"], ctx);
    }
  });

export function parseFusionConditionAssessment(input: unknown): FusionConditionAssessment {
  return fusionConditionAssessmentSchema.parse(input) as FusionConditionAssessment;
}

export function parseInvestigationPackage(input: unknown): InvestigationPackage {
  return investigationPackageSchema.parse(input) as InvestigationPackage;
}
