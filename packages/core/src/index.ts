export type DataProvenanceKind = "fixture" | "measured" | "derived" | "synthetic";
export type DataProvider = "STATIC_FIXTURE" | "FAIR_MAST";
export type InspiredBySource = "FAIR_MAST";

export interface ExperimentContext {
  projectId: string;
  datasetId: string;
  facility: string;
  campaign?: string | undefined;
  description: string;
  safetyClassification: "public-educational-fixture";
  createdAt: string;
}

export interface ShotMetadata {
  shotId: string;
  displayName: string;
  deviceName: string;
  recordedAt: string;
  source: {
    kind: DataProvenanceKind;
    provider: DataProvider;
    inspiredBy?: InspiredBySource | undefined;
    uri: string;
    license: string;
  };
  signalIds: string[];
  tags: string[];
  notes?: string | undefined;
}

export interface SignalSeries {
  signalId: string;
  label: string;
  quantity: string;
  unit: string;
  timeUnit: "s";
  time: number[];
  values: number[];
}

export interface StudyRecord {
  schemaVersion: "0.1.0";
  context: ExperimentContext;
  shot: ShotMetadata;
  signals: SignalSeries[];
}

export interface FixtureManifest {
  schemaVersion: "0.1.0";
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
