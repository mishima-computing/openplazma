import type { MhdAnalysisBundle } from "./mhd";

export type DataProvenanceKind = "fixture" | "measured" | "derived" | "synthetic";
export type DataProvider = "STATIC_FIXTURE" | "LOCAL_SIGNAL_FILE";
export type InspiredBySource = "FAIR_MAST";
export type SourceValidationStatus = "schema_validated";
export type TargetType = "static_fixture" | "local_run_store";

export interface TargetRef {
  type: TargetType;
  id: string;
  label: string;
}

export interface SourceRef {
  provider: DataProvider;
  sourceLabel: string;
  inspiredBy?: InspiredBySource | undefined;
  uri?: string | undefined;
  sha256?: string | undefined;
  validationStatus?: SourceValidationStatus | undefined;
}

export interface CapabilitySet {
  readData: true;
  writeArtifacts: true;
  runSimulation: false;
  submitComputeJob: false;
  readFacilityTelemetry: false;
  controlFacility: false;
}

export interface SignalRef {
  signalId: string;
  label?: string | undefined;
  quantity?: string | undefined;
  unit?: string | undefined;
}

export interface Observation {
  text: string;
  signalId?: string | undefined;
  timeRange?: [number, number] | undefined;
}

export interface ExperimentContext {
  kind: "openplazma.experiment_context";
  version: "0.1.0";
  contextId: string;
  projectId: string;
  datasetId: string;
  campaign?: string | undefined;
  description: string;
  safetyClassification: "public-educational-fixture" | "read-only-local-signal";
  createdAt: string;
  target: TargetRef;
  source: SourceRef;
  capabilities: CapabilitySet;
  shotRef: {
    provider: DataProvider;
    shotId: string;
  };
  signals: SignalRef[];
  view?: {
    timeRange?: [number, number] | undefined;
  };
  observations: Observation[];
  hypothesis?: string | undefined;
  limitations: string[];
}

export interface ShotMetadata {
  kind: "openplazma.shot_metadata";
  version: "0.1.0";
  shotId: string;
  displayName: string;
  sourceLabel: string;
  deviceName?: string | undefined;
  recordedAt: string;
  source: {
    kind: DataProvenanceKind;
    provider: DataProvider;
    sourceLabel: string;
    inspiredBy?: InspiredBySource | undefined;
    uri: string;
    license: string;
    sha256?: string | undefined;
    validationStatus?: SourceValidationStatus | undefined;
  };
  signalIds: string[];
  tags: string[];
  notes?: string | undefined;
}

export interface SignalSeries {
  kind: "openplazma.signal_series";
  version: "0.1.0";
  signalId: string;
  label: string;
  quantity: string;
  unit: string;
  timeUnit: "s";
  time: number[];
  values: number[];
}

export interface StudyRecord {
  kind: "openplazma.study_record";
  version: "0.1.0";
  studyId: string;
  createdAt: string;
  source: SourceRef & {
    shotId: string;
  };
  shotRef: {
    provider: DataProvider;
    shotId: string;
  };
  signalsViewed: SignalRef[];
  observations: Observation[];
  hypothesis?: string | undefined;
  limitations: string[];
  context: ExperimentContext;
  shot: ShotMetadata;
  signals: SignalSeries[];
  mhd?: MhdAnalysisBundle | undefined;
}

export interface FixtureManifest {
  kind: "openplazma.fixture_manifest";
  version: "0.1.0";
  provider: "STATIC_FIXTURE";
  inspiredBy?: InspiredBySource | undefined;
  datasetId: string;
  shots: Array<{
    shotId: string;
    path: string;
  }>;
}

export interface FusionDataSource {
  listShots(): Promise<ShotMetadata[]>;
  getStudyRecord(shotId: string): Promise<StudyRecord | null>;
}

export type {
  ArtifactRecord,
  ContextArtifactRef,
  EventRecord,
  EventType,
  MetricRecord,
  MetricValue,
  RunManifest,
  RunRecord,
  RunStatus,
  RunType
} from "./tracking";

export type {
  Scenario,
  StudyTask,
  StudyTaskLevel,
  StudyTaskManifest,
  StudyTaskManifestEntry,
  StudyTaskPrompt,
  StudyTaskPromptType,
  SuggestedMetric
} from "./study-task";

export type {
  StudyFlow,
  StudyFlowManifest,
  StudyFlowManifestEntry,
  StudyFlowStep,
  StudyFlowSurface
} from "./study-flow";

export type {
  Claim,
  DiagnosticArray,
  DiagnosticArrayKind,
  DiagnosticChannel,
  DiagnosticKind,
  ElmAnalysis,
  ElmClassification,
  ElmCrash,
  EvidenceLink,
  EvidenceVerdict,
  Inference,
  InferenceMethod,
  MhdAnalysisBundle,
  ModeEstimateMethod,
  ModeNumberEstimate,
  ObservationModel,
  ObservationModelType,
  PhenomenonEvent,
  PhenomenonKind,
  ProbeGeometry,
  RotationTrackPoint,
  TearingModeHypothesis
} from "./mhd";

export type {
  ArtifactProvenanceKind,
  CandidateEnergySource,
  ConditionEstimateStatus,
  ConditionLogicalRole,
  DiagnosticArtifact,
  DiagnosticArtifactKind,
  FusionConditionAssessment,
  FusionConditionEstimate,
  FusionConditionMode,
  FusionConditionParameter,
  FusionReactionCandidate,
  FusionStatus,
  InvestigationClaim,
  InvestigationClaimStatus,
  InvestigationClaimType,
  InvestigationPackage,
  InvestigationQuestion,
  InvestigationQuestionKind,
  InvestigationTarget,
  InvestigationTargetKind
} from "./investigation";
