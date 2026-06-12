export type InvestigationTargetKind =
  | "atmospheric_light"
  | "organism"
  | "artifact"
  | "spacecraft"
  | "stellar_object"
  | "unknown";

export type CandidateEnergySource =
  | "chemical_luminescence"
  | "combustion"
  | "electrical_discharge"
  | "plasma"
  | "fusion"
  | "sensor_artifact"
  | "reflection"
  | "unknown";

export interface InvestigationTarget {
  kind: "openplazma.investigation_target";
  version: "0.1.0";
  targetId: string;
  targetKind: InvestigationTargetKind;
  label: string;
  description: string;
  candidateEnergySources: CandidateEnergySource[];
  limitations: string[];
}

export type InvestigationQuestionKind =
  | "energy_source_classification"
  | "is_plasma"
  | "is_fusion"
  | "fusion_conditions"
  | "plasma_maintenance";

export interface InvestigationQuestion {
  questionId: string;
  questionKind: InvestigationQuestionKind;
  text: string;
}

export type DiagnosticArtifactKind =
  | "signal_series"
  | "spectrum"
  | "image_frame"
  | "field_map"
  | "particle_flux"
  | "gravity_trace"
  | "event_log"
  | "motion_track";

export type ArtifactProvenanceKind = "measured" | "derived" | "synthetic" | "testimony" | "unknown";

export interface DiagnosticArtifact {
  kind: "openplazma.diagnostic_artifact";
  version: "0.1.0";
  artifactId: string;
  artifactKind: DiagnosticArtifactKind;
  label: string;
  provenanceKind: ArtifactProvenanceKind;
  sourceUri?: string | undefined;
  signalIds?: string[] | undefined;
  quantity?: string | undefined;
  unit?: string | undefined;
  description: string;
  limitations: string[];
}

export type FusionStatus =
  | "not_assessed"
  | "unknown"
  | "unsupported"
  | "contradicted"
  | "plausible"
  | "supported";

export type FusionConditionMode =
  | "not_applicable"
  | "unknown"
  | "forward_from_observations"
  | "inverse_from_fusion_condition";

export type FusionReactionCandidate =
  | "proton_proton_chain"
  | "cno_cycle"
  | "d_t"
  | "d_d"
  | "d_he3"
  | "p_b11"
  | "unknown";

export type FusionConditionParameter =
  | "ion_temperature"
  | "electron_temperature"
  | "density"
  | "pressure"
  | "confinement_time"
  | "triple_product"
  | "fuel_mix"
  | "gravity"
  | "magnetic_field"
  | "electric_field"
  | "impurity_fraction"
  | "radiative_loss"
  | "heat_loss"
  | "particle_loss"
  | "plasma_rotation"
  | "turbulence_level";

export type ConditionEstimateStatus =
  | "measured"
  | "inferred"
  | "required"
  | "bounded"
  | "unknown"
  | "contradicted";

export type ConditionLogicalRole = "necessary" | "supporting" | "contradicting" | "unknown";

export interface FusionConditionEstimate {
  parameter: FusionConditionParameter;
  status: ConditionEstimateStatus;
  logicalRole: ConditionLogicalRole;
  value?: number | undefined;
  lowerBound?: number | undefined;
  upperBound?: number | undefined;
  unit?: string | undefined;
  method?: string | undefined;
  evidenceArtifactIds: string[];
  assumptions: string[];
  limitations: string[];
}

export interface FusionConditionAssessment {
  kind: "openplazma.fusion_condition_assessment";
  version: "0.1.0";
  assessmentId: string;
  fusionStatus: FusionStatus;
  conditionMode: FusionConditionMode;
  reactionCandidates: FusionReactionCandidate[];
  observedOrInferredConditions: FusionConditionEstimate[];
  requiredConditions: FusionConditionEstimate[];
  unknowns: string[];
  assumptions: string[];
  limitations: string[];
}

export type InvestigationClaimType =
  | "plasma_presence"
  | "fusion_status"
  | "fusion_conditions"
  | "plasma_maintenance"
  | "source_identity";

export type InvestigationClaimStatus = "support" | "contradict" | "inconclusive" | "untested";

export interface InvestigationClaim {
  kind: "openplazma.investigation_claim";
  version: "0.1.0";
  claimId: string;
  claimType: InvestigationClaimType;
  statement: string;
  status: InvestigationClaimStatus;
  evidenceArtifactIds: string[];
  assumptions: string[];
  limitations: string[];
}

export interface InvestigationPackage {
  kind: "openplazma.investigation_package";
  version: "0.1.0";
  packageId: string;
  title: string;
  target: InvestigationTarget;
  questions: InvestigationQuestion[];
  artifacts: DiagnosticArtifact[];
  fusionAssessment: FusionConditionAssessment;
  claims: InvestigationClaim[];
  limitations: string[];
}
