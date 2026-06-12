import { z } from "zod";
import type {
  FusionConditionAssessment,
  InvestigationFixtureManifest,
  InvestigationPackage,
  InvestigationReport,
  InvestigationSession
} from "@openplazma/core";

const versionSchema = z.literal("0.1.0");
const isoDateTimeSchema = z.string().datetime({ offset: true });

const targetKindSchema = z.enum([
  "lab_plasma",
  "fusion_device",
  "atmospheric_light",
  "organism",
  "organism_interior",
  "artifact",
  "spacecraft",
  "stellar_object",
  "unknown"
]);

const candidateEnergySourceSchema = z.enum([
  "chemical_luminescence",
  "combustion",
  "electrical_discharge",
  "external_field",
  "plasma",
  "fusion",
  "metabolism",
  "radioactive_decay",
  "sensor_artifact",
  "reflection",
  "unknown"
]);

const measuredObservableSchema = z.enum([
  "visible_light",
  "infrared_light",
  "ultraviolet_light",
  "xray",
  "gamma_ray",
  "heat",
  "electric_current",
  "magnetic_field",
  "electric_field",
  "particle_flux",
  "neutron_flux",
  "neutrino_flux",
  "gravity",
  "pressure",
  "acoustic_wave",
  "motion",
  "composition",
  "density",
  "temperature",
  "unknown"
]);

const observationRegionSchema = z.object({
  regionId: z.string().min(1),
  label: z.string().min(1),
  description: z.string().min(1),
  parentRegionId: z.string().min(1).optional(),
  limitations: z.array(z.string().min(1)).min(1)
});

const investigationTargetSchema = z.object({
  kind: z.literal("openplazma.investigation_target"),
  version: versionSchema,
  targetId: z.string().min(1),
  targetKind: targetKindSchema,
  label: z.string().min(1),
  description: z.string().min(1),
  candidateEnergySources: z.array(candidateEnergySourceSchema).min(1),
  regions: z.array(observationRegionSchema).optional(),
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

const diagnosticCalibrationSchema = z.object({
  status: z.enum(["calibrated", "estimated", "uncalibrated", "unknown"]),
  responseKnown: z.boolean(),
  correctionApplied: z.boolean(),
  description: z.string().min(1),
  limitations: z.array(z.string().min(1)).min(1)
});

const diagnosticInstrumentRefSchema = z.object({
  instrumentKind: z.enum([
    "human_eye",
    "visible_camera",
    "infrared_camera",
    "ultraviolet_camera",
    "xray_detector",
    "spectrometer",
    "photodiode",
    "bolometer",
    "current_probe",
    "magnetic_probe",
    "electric_probe",
    "interferometer",
    "particle_detector",
    "neutron_detector",
    "gamma_detector",
    "neutrino_detector",
    "gravimeter",
    "accelerometer",
    "pressure_sensor",
    "microphone",
    "tomography_pipeline",
    "helioseismology_pipeline",
    "simulation_diagnostic",
    "unknown"
  ]),
  label: z.string().min(1),
  observables: z.array(measuredObservableSchema).min(1),
  calibration: diagnosticCalibrationSchema
});

const diagnosticArtifactSourceSchema = z.object({
  sourceKind: z.enum([
    "local_fixture",
    "public_snapshot",
    "derived_artifact",
    "human_report",
    "synthetic_fixture",
    "unknown"
  ]),
  label: z.string().min(1),
  uri: z.string().min(1).optional(),
  artifactIds: z.array(z.string().min(1)).optional(),
  signalIds: z.array(z.string().min(1)).optional(),
  sha256: z.string().regex(/^[a-f0-9]{64}$/).optional(),
  limitations: z.array(z.string().min(1)).min(1)
});

const diagnosticContributionSchema = z.object({
  contributionKind: z.enum([
    "thermal_emission",
    "plasma_emission",
    "fusion_product",
    "thermal_coupling",
    "photoelectric_coupling",
    "magnetic_coupling",
    "electric_coupling",
    "gravity_coupling",
    "pressure_coupling",
    "chemical_emission",
    "biological_emission",
    "background",
    "instrument_noise",
    "aliasing_artifact",
    "motion_artifact",
    "reconstruction_artifact",
    "unknown"
  ]),
  role: z.enum(["primary", "contaminant", "noise", "candidate", "unknown"]),
  status: z.enum(["measured", "inferred", "modeled", "unresolved", "rejected"]),
  description: z.string().min(1),
  limitations: z.array(z.string().min(1)).min(1)
});

const frequencyDomainSchema = z.enum([
  "electromagnetic_carrier",
  "intensity_modulation",
  "acoustic_modulation",
  "motion_modulation",
  "gravity_variation",
  "magnetic_variation",
  "electric_variation",
  "spatial_frequency",
  "unknown"
]);

const frequencyBandEstimateSchema = z
  .object({
    bandId: z.string().min(1),
    domain: frequencyDomainSchema,
    label: z.string().min(1),
    lowerFrequencyHz: z.number().finite().nonnegative().optional(),
    upperFrequencyHz: z.number().finite().positive().optional(),
    centerFrequencyHz: z.number().finite().positive().optional(),
    wavelengthMeters: z.number().finite().positive().optional(),
    quantity: z.string().min(1),
    unit: z.string().min(1).optional(),
    description: z.string().min(1),
    limitations: z.array(z.string().min(1)).min(1)
  })
  .superRefine((band, ctx) => {
    if (
      band.lowerFrequencyHz !== undefined &&
      band.upperFrequencyHz !== undefined &&
      band.upperFrequencyHz < band.lowerFrequencyHz
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "frequency band upper bound must be greater than or equal to lower bound",
        path: ["upperFrequencyHz"]
      });
    }
  });

const frequencyPeakEstimateSchema = z.object({
  peakId: z.string().min(1),
  frequencyHz: z.number().finite().positive(),
  amplitude: z.number().finite().optional(),
  phaseRadians: z.number().finite().optional(),
  qualityFactor: z.number().finite().positive().optional(),
  signalToNoiseRatio: z.number().finite().optional(),
  interpretation: z.string().min(1).optional(),
  limitations: z.array(z.string().min(1)).min(1)
});

const frequencyAnalysisSchema = z
  .object({
    analysisId: z.string().min(1),
    domain: frequencyDomainSchema,
    method: z.enum([
      "fft",
      "stft",
      "wavelet",
      "periodogram",
      "lomb_scargle",
      "harmonic_fit",
      "spectral_line_fit",
      "tomographic_inversion",
      "unknown"
    ]),
    sourceQuantity: z.string().min(1),
    sampleRateHz: z.number().finite().positive().optional(),
    windowSeconds: z.number().finite().positive().optional(),
    frequencyResolutionHz: z.number().finite().positive().optional(),
    bands: z.array(frequencyBandEstimateSchema),
    peaks: z.array(frequencyPeakEstimateSchema),
    description: z.string().min(1),
    assumptions: z.array(z.string().min(1)),
    limitations: z.array(z.string().min(1)).min(1)
  })
  .superRefine((analysis, ctx) => {
    if (analysis.bands.length === 0 && analysis.peaks.length === 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "frequency analysis requires at least one band or peak",
        path: ["bands"]
      });
    }
  });

const diagnosticArtifactSchema = z.object({
  kind: z.literal("openplazma.diagnostic_artifact"),
  version: versionSchema,
  artifactId: z.string().min(1),
  artifactKind: z.enum([
    "signal_series",
    "spectrum",
    "image_frame",
    "thermal_map",
    "tomographic_volume",
    "field_map",
    "magnetogram",
    "particle_flux",
    "neutron_flux",
    "gamma_spectrum",
    "neutrino_flux",
    "gravity_trace",
    "pressure_trace",
    "acoustic_trace",
    "helioseismic_trace",
    "composition_profile",
    "event_log",
    "motion_track"
  ]),
  label: z.string().min(1),
  provenanceKind: z.enum(["measured", "derived", "synthetic", "testimony", "unknown"]),
  targetRegionId: z.string().min(1).optional(),
  instrument: diagnosticInstrumentRefSchema.optional(),
  contributions: z.array(diagnosticContributionSchema).optional(),
  frequencyAnalyses: z.array(frequencyAnalysisSchema).optional(),
  source: diagnosticArtifactSourceSchema.optional(),
  sourceUri: z.string().min(1).optional(),
  signalIds: z.array(z.string().min(1)).optional(),
  quantity: z.string().min(1).optional(),
  unit: z.string().min(1).optional(),
  description: z.string().min(1),
  limitations: z.array(z.string().min(1)).min(1)
});

const observationStatementSchema = z.object({
  kind: z.literal("openplazma.observation_statement"),
  version: versionSchema,
  readoutId: z.string().min(1),
  artifactId: z.string().min(1),
  signalId: z.string().min(1).optional(),
  targetRegionId: z.string().min(1).optional(),
  observable: measuredObservableSchema,
  readoutKind: z.enum([
    "raw_sample",
    "summary_statistic",
    "frequency_band",
    "frequency_peak",
    "spectral_feature",
    "image_feature",
    "thermal_feature",
    "field_feature",
    "particle_count",
    "absence_statement",
    "human_report",
    "model_readout",
    "unknown"
  ]),
  method: z.string().min(1),
  selector: z.string().min(1).optional(),
  timeRange: z.tuple([z.number().finite(), z.number().finite()]).optional(),
  value: z.number().finite().optional(),
  textValue: z.string().min(1).optional(),
  unit: z.string().min(1).optional(),
  status: z.enum(["detected", "not_detected", "candidate", "inconclusive", "unknown"]),
  uncertainty: z.string().min(1).optional(),
  assumptions: z.array(z.string().min(1)),
  limitations: z.array(z.string().min(1)).min(1),
  alternatives: z.array(z.string().min(1))
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
    "composition",
    "ionization_fraction",
    "confinement_mechanism",
    "confinement_geometry",
    "plasma_volume",
    "energy_input",
    "alpha_heating",
    "ash_fraction",
    "gravity",
    "magnetic_field",
    "electric_field",
    "impurity_fraction",
    "radiative_loss",
    "bremsstrahlung_loss",
    "line_radiation_loss",
    "heat_loss",
    "thermal_conduction_loss",
    "particle_loss",
    "neutral_density",
    "material_interaction",
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
  evidenceReadoutIds: z.array(z.string().min(1)).optional(),
  assumptions: z.array(z.string().min(1)),
  limitations: z.array(z.string().min(1)),
  alternatives: z.array(z.string().min(1)).optional()
});

export const fusionConditionAssessmentSchema = z
  .object({
    kind: z.literal("openplazma.fusion_condition_assessment"),
    version: versionSchema,
    assessmentId: z.string().min(1),
    fusionStatus: fusionStatusSchema,
    conditionMode: conditionModeSchema,
    reactionCandidates: z
      .array(z.enum(["proton_proton_chain", "cno_cycle", "d_t", "d_d", "d_he3", "p_b11", "advanced_aneutronic", "unknown"]))
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
  evidenceReadoutIds: z.array(z.string().min(1)).optional(),
  method: z.string().min(1).optional(),
  assumptions: z.array(z.string().min(1)),
  limitations: z.array(z.string().min(1)),
  alternatives: z.array(z.string().min(1)).optional()
});

function normalizedStatement(statement: string): string {
  return statement.toLowerCase().replace(/\s+/g, " ").trim();
}

function readsAsPositiveIdentityClaim(claim: z.infer<typeof investigationClaimSchema>): boolean {
  if (claim.status !== "support") {
    return false;
  }
  const statement = normalizedStatement(claim.statement);
  const negativeMarkers = [
    "does not support",
    "unsupported",
    "untested",
    "not proof",
    "not prove",
    "cannot identify",
    "cannot prove",
    "insufficient",
    "remains untested"
  ];
  if (negativeMarkers.some((marker) => statement.includes(marker))) {
    return false;
  }
  if (statement.includes("prove") || statement.includes("proof")) {
    return true;
  }
  if (statement.includes(" is plasma") || statement.includes(" is fusion") || statement.includes("fusion is occurring")) {
    return true;
  }
  return claim.claimType === "plasma_presence" || claim.claimType === "source_identity";
}

function checkReadoutRefs(
  readoutIds: Set<string>,
  ids: string[] | undefined,
  path: Array<string | number>,
  ctx: z.RefinementCtx
): void {
  for (const readoutId of ids ?? []) {
    if (!readoutIds.has(readoutId)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `references unknown mediated readout '${readoutId}'`,
        path
      });
    }
  }
}

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
    artifacts: z.array(diagnosticArtifactSchema),
    observations: z.array(observationStatementSchema).optional(),
    fusionAssessment: fusionConditionAssessmentSchema,
    claims: z.array(investigationClaimSchema),
    limitations: z.array(z.string().min(1)).min(1)
  })
  .superRefine((pack, ctx) => {
    const artifactIds = new Set<string>();
    const artifactById = new Map<string, (typeof pack.artifacts)[number]>();
    const readoutIds = new Set<string>();
    const readoutById = new Map<string, NonNullable<typeof pack.observations>[number]>();
    const regionIds = new Set((pack.target.regions ?? []).map((region) => region.regionId));
    for (const [index, region] of (pack.target.regions ?? []).entries()) {
      if (region.parentRegionId !== undefined && !regionIds.has(region.parentRegionId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `observation region '${region.regionId}' references unknown parent region '${region.parentRegionId}'`,
          path: ["target", "regions", index, "parentRegionId"]
        });
      }
    }
    for (const [index, artifact] of pack.artifacts.entries()) {
      if (artifactIds.has(artifact.artifactId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `duplicate diagnostic artifact id '${artifact.artifactId}'`,
          path: ["artifacts", index, "artifactId"]
        });
      }
      artifactIds.add(artifact.artifactId);
      artifactById.set(artifact.artifactId, artifact);
      if (artifact.targetRegionId !== undefined && !regionIds.has(artifact.targetRegionId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `diagnostic artifact '${artifact.artifactId}' references unknown target region '${artifact.targetRegionId}'`,
          path: ["artifacts", index, "targetRegionId"]
        });
      }
    }
    for (const [index, readout] of (pack.observations ?? []).entries()) {
      if (readoutIds.has(readout.readoutId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `duplicate mediated readout id '${readout.readoutId}'`,
          path: ["observations", index, "readoutId"]
        });
      }
      readoutIds.add(readout.readoutId);
      readoutById.set(readout.readoutId, readout);
      if (!artifactIds.has(readout.artifactId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `mediated readout '${readout.readoutId}' references unknown diagnostic artifact '${readout.artifactId}'`,
          path: ["observations", index, "artifactId"]
        });
      }
      if (readout.targetRegionId !== undefined && !regionIds.has(readout.targetRegionId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `mediated readout '${readout.readoutId}' references unknown target region '${readout.targetRegionId}'`,
          path: ["observations", index, "targetRegionId"]
        });
      }
      const artifact = artifactById.get(readout.artifactId);
      if (artifact?.signalIds !== undefined && readout.signalId !== undefined && !artifact.signalIds.includes(readout.signalId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `mediated readout '${readout.readoutId}' references signal '${readout.signalId}' outside artifact '${readout.artifactId}'`,
          path: ["observations", index, "signalId"]
        });
      }
    }
    for (const [index, estimate] of pack.fusionAssessment.observedOrInferredConditions.entries()) {
      checkArtifactRefs(
        artifactIds,
        estimate.evidenceArtifactIds,
        ["fusionAssessment", "observedOrInferredConditions", index, "evidenceArtifactIds"],
        ctx
      );
      checkReadoutRefs(
        readoutIds,
        estimate.evidenceReadoutIds,
        ["fusionAssessment", "observedOrInferredConditions", index, "evidenceReadoutIds"],
        ctx
      );
      if (
        ["measured", "inferred", "bounded", "contradicted"].includes(estimate.status) &&
        (estimate.evidenceReadoutIds ?? []).length === 0
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "observed or inferred fusion conditions require mediated readout evidence",
          path: ["fusionAssessment", "observedOrInferredConditions", index, "evidenceReadoutIds"]
        });
      }
      if (["measured", "inferred", "bounded", "contradicted"].includes(estimate.status) && estimate.method === undefined) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "observed or inferred fusion conditions require a method",
          path: ["fusionAssessment", "observedOrInferredConditions", index, "method"]
        });
      }
      if (["measured", "inferred", "bounded", "contradicted"].includes(estimate.status) && estimate.alternatives === undefined) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "observed or inferred fusion conditions require alternatives",
          path: ["fusionAssessment", "observedOrInferredConditions", index, "alternatives"]
        });
      }
    }
    for (const [index, estimate] of pack.fusionAssessment.requiredConditions.entries()) {
      checkArtifactRefs(
        artifactIds,
        estimate.evidenceArtifactIds,
        ["fusionAssessment", "requiredConditions", index, "evidenceArtifactIds"],
        ctx
      );
      checkReadoutRefs(
        readoutIds,
        estimate.evidenceReadoutIds,
        ["fusionAssessment", "requiredConditions", index, "evidenceReadoutIds"],
        ctx
      );
    }
    for (const [index, claim] of pack.claims.entries()) {
      checkArtifactRefs(artifactIds, claim.evidenceArtifactIds, ["claims", index, "evidenceArtifactIds"], ctx);
      checkReadoutRefs(readoutIds, claim.evidenceReadoutIds, ["claims", index, "evidenceReadoutIds"], ctx);
      if (["support", "contradict"].includes(claim.status) && (claim.evidenceReadoutIds ?? []).length === 0) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `claim '${claim.claimId}' requires mediated readout evidence`,
          path: ["claims", index, "evidenceReadoutIds"]
        });
      }
      if (["support", "contradict"].includes(claim.status) && claim.method === undefined) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `claim '${claim.claimId}' requires an interpretation method`,
          path: ["claims", index, "method"]
        });
      }
      if (["support", "contradict"].includes(claim.status) && claim.alternatives === undefined) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `claim '${claim.claimId}' requires alternatives`,
          path: ["claims", index, "alternatives"]
        });
      }
      const statement = normalizedStatement(claim.statement);
      if (
        /(\bno\b|\bnot\b).*(observed|detected).*(therefore|so).*(absent|no fusion|not fusion)/.test(statement) ||
        /no .* (observed|detected).*therefore/.test(statement)
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "absence-only reasoning cannot establish absence without diagnostic adequacy",
          path: ["claims", index, "statement"]
        });
      }
      if (readsAsPositiveIdentityClaim(claim)) {
        const readouts = (claim.evidenceReadoutIds ?? []).map((readoutId) => readoutById.get(readoutId)).filter((value) => value !== undefined);
        const evidenceArtifacts = new Set<string>(claim.evidenceArtifactIds);
        for (const readout of readouts) {
          evidenceArtifacts.add(readout.artifactId);
        }
        const artifacts = [...evidenceArtifacts].map((artifactId) => artifactById.get(artifactId)).filter((value) => value !== undefined);
        const allHumanEye = artifacts.length > 0 && artifacts.every((artifact) => artifact.instrument?.instrumentKind === "human_eye");
        const allVisibleOnly =
          readouts.length > 0 &&
          readouts.every((readout) => readout.observable === "visible_light") &&
          artifacts.every((artifact) => (artifact.instrument?.observables ?? ["visible_light"]).every((observable) => observable === "visible_light"));
        const allSynthetic =
          artifacts.length > 0 &&
          artifacts.every(
            (artifact) => artifact.provenanceKind === "synthetic" || artifact.instrument?.instrumentKind === "simulation_diagnostic"
          );
        if (allHumanEye) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "human-eye evidence alone cannot support a positive plasma, fusion, or source-identity claim",
            path: ["claims", index, "evidenceReadoutIds"]
          });
        }
        if (allSynthetic || statement.includes("simulation observed")) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "simulation output cannot be treated as direct observation of a physical phenomenon",
            path: ["claims", index, "evidenceReadoutIds"]
          });
        }
        if (allVisibleOnly) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "visible light alone cannot support a positive plasma, fusion, or source-identity claim",
            path: ["claims", index, "evidenceReadoutIds"]
          });
        }
      }
    }
  });

export const investigationFixtureManifestSchema = z
  .object({
    kind: z.literal("openplazma.investigation_fixture_manifest"),
    version: versionSchema,
    provider: z.literal("STATIC_FIXTURE"),
    datasetId: z.string().min(1),
    packages: z
      .array(
        z.object({
          packageId: z.string().min(1),
          title: z.string().min(1),
          path: z.string().min(1)
        })
      )
      .min(1)
  })
  .superRefine((manifest, ctx) => {
    const seen = new Set<string>();
    for (const [index, entry] of manifest.packages.entries()) {
      if (seen.has(entry.packageId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `duplicate investigation package id '${entry.packageId}'`,
          path: ["packages", index, "packageId"]
        });
      }
      seen.add(entry.packageId);
    }
  });

export const investigationReportSchema = z.object({
  kind: z.literal("openplazma.investigation_report"),
  version: versionSchema,
  reportId: z.string().min(1),
  packageId: z.string().min(1),
  createdAt: isoDateTimeSchema,
  claims: z.array(investigationClaimSchema).min(1),
  assumptions: z.array(z.string().min(1)),
  limitations: z.array(z.string().min(1)).min(1),
  nextObservations: z.array(z.string().min(1))
});

export const investigationSessionSchema = z
  .object({
    kind: z.literal("openplazma.investigation_session"),
    version: versionSchema,
    sessionId: z.string().min(1),
    createdAt: isoDateTimeSchema,
    updatedAt: isoDateTimeSchema,
    status: z.enum(["collecting_evidence", "ready_for_report", "reported"]),
    package: investigationPackageSchema,
    requiredObservables: z.array(measuredObservableSchema),
    reports: z.array(investigationReportSchema),
    limitations: z.array(z.string().min(1)).min(1)
  })
  .superRefine((session, ctx) => {
    if (session.status === "reported" && session.reports.length === 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "reported investigation sessions require at least one report",
        path: ["reports"]
      });
    }
    const sessionArtifactIds = new Set(session.package.artifacts.map((artifact) => artifact.artifactId));
    const sessionReadoutIds = new Set((session.package.observations ?? []).map((readout) => readout.readoutId));
    for (const [index, report] of session.reports.entries()) {
      if (report.packageId !== session.package.packageId) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "session report packageId must match the session package",
          path: ["reports", index, "packageId"]
        });
      }
      for (const [claimIndex, claim] of report.claims.entries()) {
        checkArtifactRefs(
          sessionArtifactIds,
          claim.evidenceArtifactIds,
          ["reports", index, "claims", claimIndex, "evidenceArtifactIds"],
          ctx
        );
        checkReadoutRefs(
          sessionReadoutIds,
          claim.evidenceReadoutIds,
          ["reports", index, "claims", claimIndex, "evidenceReadoutIds"],
          ctx
        );
      }
    }
  });

export function parseFusionConditionAssessment(input: unknown): FusionConditionAssessment {
  return fusionConditionAssessmentSchema.parse(input) as FusionConditionAssessment;
}

export function parseInvestigationPackage(input: unknown): InvestigationPackage {
  return investigationPackageSchema.parse(input) as InvestigationPackage;
}

export function parseInvestigationFixtureManifest(input: unknown): InvestigationFixtureManifest {
  return investigationFixtureManifestSchema.parse(input) as InvestigationFixtureManifest;
}

export function parseInvestigationReport(input: unknown): InvestigationReport {
  return investigationReportSchema.parse(input) as InvestigationReport;
}

export function parseInvestigationSession(input: unknown): InvestigationSession {
  return investigationSessionSchema.parse(input) as InvestigationSession;
}
