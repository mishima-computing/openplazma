export type InvestigationTargetKind =
  | "lab_plasma"
  | "fusion_device"
  | "atmospheric_light"
  | "organism"
  | "organism_interior"
  | "artifact"
  | "spacecraft"
  | "stellar_object"
  | "unknown";

export type CandidateEnergySource =
  | "chemical_luminescence"
  | "combustion"
  | "electrical_discharge"
  | "external_field"
  | "plasma"
  | "fusion"
  | "metabolism"
  | "radioactive_decay"
  | "sensor_artifact"
  | "reflection"
  | "unknown";

export interface ObservationRegion {
  regionId: string;
  label: string;
  description: string;
  parentRegionId?: string | undefined;
  limitations: string[];
}

export interface InvestigationTarget {
  kind: "openplazma.investigation_target";
  version: "0.1.0";
  targetId: string;
  targetKind: InvestigationTargetKind;
  label: string;
  description: string;
  candidateEnergySources: CandidateEnergySource[];
  regions?: ObservationRegion[] | undefined;
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
  | "thermal_map"
  | "tomographic_volume"
  | "field_map"
  | "magnetogram"
  | "particle_flux"
  | "neutron_flux"
  | "gamma_spectrum"
  | "neutrino_flux"
  | "gravity_trace"
  | "pressure_trace"
  | "acoustic_trace"
  | "helioseismic_trace"
  | "composition_profile"
  | "event_log"
  | "motion_track";

export type ArtifactProvenanceKind = "measured" | "derived" | "synthetic" | "testimony" | "unknown";

export type DiagnosticInstrumentKind =
  | "human_eye"
  | "visible_camera"
  | "infrared_camera"
  | "ultraviolet_camera"
  | "xray_detector"
  | "spectrometer"
  | "photodiode"
  | "bolometer"
  | "current_probe"
  | "magnetic_probe"
  | "electric_probe"
  | "interferometer"
  | "particle_detector"
  | "neutron_detector"
  | "gamma_detector"
  | "neutrino_detector"
  | "gravimeter"
  | "accelerometer"
  | "pressure_sensor"
  | "microphone"
  | "tomography_pipeline"
  | "helioseismology_pipeline"
  | "simulation_diagnostic"
  | "unknown";

export type MeasuredObservable =
  | "visible_light"
  | "infrared_light"
  | "ultraviolet_light"
  | "xray"
  | "gamma_ray"
  | "heat"
  | "electric_current"
  | "magnetic_field"
  | "electric_field"
  | "particle_flux"
  | "neutron_flux"
  | "neutrino_flux"
  | "gravity"
  | "pressure"
  | "acoustic_wave"
  | "motion"
  | "composition"
  | "density"
  | "temperature"
  | "unknown";

export type DiagnosticContributionKind =
  | "thermal_emission"
  | "plasma_emission"
  | "fusion_product"
  | "thermal_coupling"
  | "photoelectric_coupling"
  | "magnetic_coupling"
  | "electric_coupling"
  | "gravity_coupling"
  | "pressure_coupling"
  | "chemical_emission"
  | "biological_emission"
  | "background"
  | "instrument_noise"
  | "aliasing_artifact"
  | "motion_artifact"
  | "reconstruction_artifact"
  | "unknown";

export type ContributionRole = "primary" | "contaminant" | "noise" | "candidate" | "unknown";
export type ContributionStatus = "measured" | "inferred" | "modeled" | "unresolved" | "rejected";
export type CalibrationStatus = "calibrated" | "estimated" | "uncalibrated" | "unknown";

export interface DiagnosticContribution {
  contributionKind: DiagnosticContributionKind;
  role: ContributionRole;
  status: ContributionStatus;
  description: string;
  limitations: string[];
}

export interface DiagnosticCalibration {
  status: CalibrationStatus;
  responseKnown: boolean;
  correctionApplied: boolean;
  description: string;
  limitations: string[];
}

export interface DiagnosticInstrumentRef {
  instrumentKind: DiagnosticInstrumentKind;
  label: string;
  observables: MeasuredObservable[];
  calibration: DiagnosticCalibration;
}

export type DiagnosticArtifactSourceKind =
  | "local_fixture"
  | "public_snapshot"
  | "derived_artifact"
  | "human_report"
  | "synthetic_fixture"
  | "unknown";

export interface DiagnosticArtifactSource {
  sourceKind: DiagnosticArtifactSourceKind;
  label: string;
  uri?: string | undefined;
  artifactIds?: string[] | undefined;
  signalIds?: string[] | undefined;
  sha256?: string | undefined;
  limitations: string[];
}

export type FrequencyDomain =
  | "electromagnetic_carrier"
  | "intensity_modulation"
  | "acoustic_modulation"
  | "motion_modulation"
  | "gravity_variation"
  | "magnetic_variation"
  | "electric_variation"
  | "spatial_frequency"
  | "unknown";

export type FrequencyAnalysisMethod =
  | "fft"
  | "stft"
  | "wavelet"
  | "periodogram"
  | "lomb_scargle"
  | "harmonic_fit"
  | "spectral_line_fit"
  | "tomographic_inversion"
  | "unknown";

export interface FrequencyBandEstimate {
  bandId: string;
  domain: FrequencyDomain;
  label: string;
  lowerFrequencyHz?: number | undefined;
  upperFrequencyHz?: number | undefined;
  centerFrequencyHz?: number | undefined;
  wavelengthMeters?: number | undefined;
  quantity: string;
  unit?: string | undefined;
  description: string;
  limitations: string[];
}

export interface FrequencyPeakEstimate {
  peakId: string;
  frequencyHz: number;
  amplitude?: number | undefined;
  phaseRadians?: number | undefined;
  qualityFactor?: number | undefined;
  signalToNoiseRatio?: number | undefined;
  interpretation?: string | undefined;
  limitations: string[];
}

export interface FrequencyAnalysis {
  analysisId: string;
  domain: FrequencyDomain;
  method: FrequencyAnalysisMethod;
  sourceQuantity: string;
  sampleRateHz?: number | undefined;
  windowSeconds?: number | undefined;
  frequencyResolutionHz?: number | undefined;
  bands: FrequencyBandEstimate[];
  peaks: FrequencyPeakEstimate[];
  description: string;
  assumptions: string[];
  limitations: string[];
}

export interface DiagnosticArtifact {
  kind: "openplazma.diagnostic_artifact";
  version: "0.1.0";
  artifactId: string;
  artifactKind: DiagnosticArtifactKind;
  label: string;
  provenanceKind: ArtifactProvenanceKind;
  targetRegionId?: string | undefined;
  instrument?: DiagnosticInstrumentRef | undefined;
  contributions?: DiagnosticContribution[] | undefined;
  frequencyAnalyses?: FrequencyAnalysis[] | undefined;
  source?: DiagnosticArtifactSource | undefined;
  sourceUri?: string | undefined;
  signalIds?: string[] | undefined;
  quantity?: string | undefined;
  unit?: string | undefined;
  description: string;
  limitations: string[];
}

export type ObservationReadoutKind =
  | "raw_sample"
  | "summary_statistic"
  | "frequency_band"
  | "frequency_peak"
  | "spectral_feature"
  | "image_feature"
  | "thermal_feature"
  | "field_feature"
  | "particle_count"
  | "absence_statement"
  | "human_report"
  | "model_readout"
  | "unknown";

export type ObservationStatementStatus = "detected" | "not_detected" | "candidate" | "inconclusive" | "unknown";

export interface ObservationStatement {
  kind: "openplazma.observation_statement";
  version: "0.1.0";
  readoutId: string;
  artifactId: string;
  signalId?: string | undefined;
  targetRegionId?: string | undefined;
  observable: MeasuredObservable;
  readoutKind: ObservationReadoutKind;
  method: string;
  selector?: string | undefined;
  timeRange?: [number, number] | undefined;
  value?: number | undefined;
  textValue?: string | undefined;
  unit?: string | undefined;
  status: ObservationStatementStatus;
  uncertainty?: string | undefined;
  assumptions: string[];
  limitations: string[];
  alternatives: string[];
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
  | "advanced_aneutronic"
  | "unknown";

export type FusionConditionParameter =
  | "ion_temperature"
  | "electron_temperature"
  | "density"
  | "pressure"
  | "confinement_time"
  | "triple_product"
  | "fuel_mix"
  | "composition"
  | "ionization_fraction"
  | "confinement_mechanism"
  | "confinement_geometry"
  | "plasma_volume"
  | "energy_input"
  | "alpha_heating"
  | "ash_fraction"
  | "gravity"
  | "magnetic_field"
  | "electric_field"
  | "impurity_fraction"
  | "radiative_loss"
  | "bremsstrahlung_loss"
  | "line_radiation_loss"
  | "heat_loss"
  | "thermal_conduction_loss"
  | "particle_loss"
  | "neutral_density"
  | "material_interaction"
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
  evidenceReadoutIds?: string[] | undefined;
  assumptions: string[];
  limitations: string[];
  alternatives?: string[] | undefined;
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
  evidenceReadoutIds?: string[] | undefined;
  method?: string | undefined;
  assumptions: string[];
  limitations: string[];
  alternatives?: string[] | undefined;
}

export interface InvestigationPackage {
  kind: "openplazma.investigation_package";
  version: "0.1.0";
  packageId: string;
  title: string;
  target: InvestigationTarget;
  questions: InvestigationQuestion[];
  artifacts: DiagnosticArtifact[];
  observations?: ObservationStatement[] | undefined;
  fusionAssessment: FusionConditionAssessment;
  claims: InvestigationClaim[];
  limitations: string[];
}

export interface InvestigationReport {
  kind: "openplazma.investigation_report";
  version: "0.1.0";
  reportId: string;
  packageId: string;
  createdAt: string;
  claims: InvestigationClaim[];
  assumptions: string[];
  limitations: string[];
  nextObservations: string[];
}

export type InvestigationSessionStatus = "collecting_evidence" | "ready_for_report" | "reported";

export interface InvestigationSession {
  kind: "openplazma.investigation_session";
  version: "0.1.0";
  sessionId: string;
  createdAt: string;
  updatedAt: string;
  status: InvestigationSessionStatus;
  package: InvestigationPackage;
  requiredObservables: MeasuredObservable[];
  reports: InvestigationReport[];
  limitations: string[];
}

export interface InvestigationFixtureManifest {
  kind: "openplazma.investigation_fixture_manifest";
  version: "0.1.0";
  provider: "STATIC_FIXTURE";
  datasetId: string;
  packages: InvestigationPackageMetadata[];
}

export interface InvestigationPackageMetadata {
  packageId: string;
  title: string;
  path: string;
}

export interface InvestigationDataSource {
  listInvestigationPackages(): Promise<InvestigationPackageMetadata[]>;
  getInvestigationPackage(packageId: string): Promise<InvestigationPackage | null>;
}
