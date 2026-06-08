import type { DataProvenanceKind } from "./index";

/**
 * MHD mode-analysis contracts.
 *
 * These types descend the "Future Concepts" of docs/observation-model.md into
 * concrete, read-only contracts for post-ignition plasma dynamics: a multi-channel
 * magnetic diagnostic array (Mirnov coils), a forward ObservationModel for a
 * rotating tearing mode, the inverse Inference that recovers its mode numbers and
 * rotation, and the Claim/EvidenceLink chain that ties a statement to evidence.
 *
 * Nothing here implies facility control or live telemetry. Forward models are
 * analytic, in-process computations producing synthetic/derived signals only.
 */

export interface ProbeGeometry {
  /** Poloidal angle of the probe around the plasma cross-section, radians. */
  poloidalAngleRad: number;
  /** Toroidal angle of the probe around the machine, radians. */
  toroidalAngleRad: number;
  /** Major radius of the probe location, metres. */
  majorRadiusM: number;
  /** Minor radius of the probe location, metres. */
  minorRadiusM?: number | undefined;
}

export type DiagnosticKind = "magnetic_probe" | "flux_loop";

export interface DiagnosticChannel {
  kind: "openplazma.diagnostic_channel";
  version: "0.1.0";
  channelId: string;
  label: string;
  /** References a SignalSeries.signalId carried in the same StudyRecord. */
  signalId: string;
  diagnosticKind: DiagnosticKind;
  geometry: ProbeGeometry;
}

export type DiagnosticArrayKind = "mirnov_toroidal" | "mirnov_poloidal";

export interface DiagnosticArray {
  kind: "openplazma.diagnostic_array";
  version: "0.1.0";
  arrayId: string;
  label: string;
  arrayKind: DiagnosticArrayKind;
  channels: DiagnosticChannel[];
}

export type PhenomenonKind =
  | "mode_onset"
  | "rotation_slowdown"
  | "mode_locking"
  | "current_quench"
  | "disruption"
  | "elm_crash"
  | "sawtooth_crash"
  | "ntm_onset"
  | "ntm_saturation"
  | "radiative_collapse"
  | "density_limit";

export interface PhenomenonEvent {
  kind: "openplazma.phenomenon_event";
  version: "0.1.0";
  eventId: string;
  phenomenon: PhenomenonKind;
  label: string;
  timeRange: [number, number];
  signalId?: string | undefined;
  notes?: string | undefined;
}

export interface TearingModeHypothesis {
  /** Poloidal mode number m. */
  poloidalModeNumber: number;
  /** Toroidal mode number n. */
  toroidalModeNumber: number;
  /** Fluctuation amplitude, arbitrary units. */
  amplitude: number;
  /** Mode rotation frequency, Hz. */
  rotationFreqHz: number;
  /** Reference phase offset, radians. */
  phaseRad: number;
  timeRange: [number, number];
}

export type ObservationModelType = "analytic_tearing_mode";

export interface ObservationModel {
  kind: "openplazma.observation_model";
  version: "0.1.0";
  modelId: string;
  label: string;
  modelType: ObservationModelType;
  targetArrayId: string;
  hypothesis: TearingModeHypothesis;
  /** SignalSeries.signalId values of the synthetic forward-model signals. */
  producedSignalIds: string[];
  assumptions: string[];
  limitations: string[];
}

export type ModeEstimateMethod = "phase_fit_toroidal" | "phase_fit_poloidal";

export interface ModeNumberEstimate {
  toroidalModeNumber: number;
  poloidalModeNumber?: number | undefined;
  /** 0..1 confidence derived from the phase-fit residual. */
  confidence: number;
  method: ModeEstimateMethod;
  /** Estimated magnetic-island width in metres (e.g. for NTMs). */
  islandWidthM?: number | undefined;
}

export interface RotationTrackPoint {
  time: number;
  rotationFreqHz: number;
  amplitude: number;
}

export type InferenceMethod = "magnetic_mode_phase_fit";

export interface Inference {
  kind: "openplazma.inference";
  version: "0.1.0";
  inferenceId: string;
  label: string;
  method: InferenceMethod;
  sourceArrayId: string;
  modeEstimate: ModeNumberEstimate;
  rotationTrack: RotationTrackPoint[];
  lockingDetected: boolean;
  lockTimeRange?: [number, number] | undefined;
  assumptions: string[];
  limitations: string[];
}

export type EvidenceVerdict = "support" | "contradict" | "inconclusive";

export interface EvidenceLink {
  kind: "openplazma.evidence_link";
  version: "0.1.0";
  verdict: EvidenceVerdict;
  signalId?: string | undefined;
  arrayId?: string | undefined;
  timeRange: [number, number];
  rationale: string;
}

export interface Claim {
  kind: "openplazma.claim";
  version: "0.1.0";
  claimId: string;
  statement: string;
  /** Backing artifacts; a claim references at least one of these. */
  observationModelId?: string | undefined;
  inferenceId?: string | undefined;
  elmAnalysisId?: string | undefined;
  /** PhenomenonEvent.eventId values this claim rests on. */
  eventIds?: string[] | undefined;
  evidence: EvidenceLink[];
}

export interface ElmCrash {
  /** Time of the ELM crash, seconds. */
  time: number;
  /** Crash amplitude in the source signal's units. */
  amplitude: number;
}

export type ElmClassification = "type_I" | "type_III" | "unknown";

/**
 * Edge-localised mode (ELM) summary inferred from a recycling-light or
 * divertor signal: the detected crashes, their repetition frequency, how
 * regular they are, and a coarse classification.
 */
export interface ElmAnalysis {
  kind: "openplazma.elm_analysis";
  version: "0.1.0";
  analysisId: string;
  label: string;
  /** SignalSeries.signalId the crashes were detected on (e.g. D-alpha). */
  sourceSignalId: string;
  crashes: ElmCrash[];
  elmFrequencyHz: number;
  /** 0..1, where 1 is perfectly periodic crash spacing. */
  regularity: number;
  classification: ElmClassification;
  assumptions: string[];
  limitations: string[];
}

export interface MhdAnalysisBundle {
  kind: "openplazma.mhd_analysis_bundle";
  version: "0.1.0";
  arrays: DiagnosticArray[];
  events: PhenomenonEvent[];
  observationModels: ObservationModel[];
  inferences: Inference[];
  claims: Claim[];
  provenanceKind: DataProvenanceKind;
  elmAnalyses?: ElmAnalysis[] | undefined;
}
