import type { CapabilitySet, SourceRef, TargetRef } from "./index";

export type RunStatus = "running" | "finished" | "failed";
export type RunType = "notebook_analysis" | string;

export interface ContextArtifactRef {
  artifactName: string;
  artifactType: "experiment_context" | string;
}

export interface RunRecord {
  kind: "openplazma.run";
  version: "0.1.0";
  runId: string;
  project: string;
  campaign: string;
  runType: RunType;
  status: RunStatus;
  createdAt: string;
  updatedAt: string;
  finishedAt?: string | null | undefined;
  target: TargetRef & {
    type: "local_run_store";
  };
  source: SourceRef;
  capabilities: CapabilitySet;
  storeId?: string | undefined;
  machineId?: string | undefined;
  runGroupId?: string | null | undefined;
  partitionId?: string | null | undefined;
  contextRef: ContextArtifactRef | null;
  artifactCount: number;
  metricCount: number;
  limitations: string[];
}

export interface RunStoreMetadata {
  kind: "openplazma.run_store";
  version: "0.1.0";
  layoutVersion: string;
  storeId: string;
  backendKind: "local_filesystem" | string;
  createdAt: string;
  machineId?: string | undefined;
  limitations?: string[] | undefined;
}

export type JsonValue = string | number | boolean | null | JsonObject | JsonValue[];
export interface JsonObject {
  [key: string]: JsonValue;
}
export type MetricValue = JsonValue;

export interface MetricRecord {
  kind: "openplazma.metric";
  version: "0.1.0";
  runId: string;
  name: string;
  value: MetricValue;
  step?: number | null | undefined;
  createdAt: string;
}

export interface ArtifactBlobRef {
  kind: "openplazma.artifact_blob_ref";
  version: "0.1.0";
  algorithm: "sha256";
  digest: string;
  path: string;
  byteSize: number;
  mediaType?: string | undefined;
}

export interface ArtifactRecord {
  kind: "openplazma.artifact";
  version: "0.1.0";
  artifactId: string;
  runId: string;
  name: string;
  type: string;
  path: string;
  sha256: string;
  byteSize?: number | undefined;
  blobRef?: ArtifactBlobRef | undefined;
  createdAt: string;
  metadata: JsonObject;
}

export type EventType = "run_started" | "metric_logged" | "artifact_logged" | "run_finished" | "run_failed";

export interface EventRecord {
  kind: "openplazma.event";
  version: "0.1.0";
  runId: string;
  eventType: EventType;
  machineId?: string | undefined;
  createdAt: string;
  message: string;
  metadata: JsonObject;
}

export interface RunManifest {
  kind: "openplazma.run_manifest";
  version: "0.1.0";
  runId: string;
  createdAt: string;
  updatedAt: string;
  artifacts: ArtifactRecord[];
}
