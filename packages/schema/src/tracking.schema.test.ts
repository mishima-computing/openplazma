import { describe, expect, it } from "vitest";
import {
  artifactRecordSchema,
  eventRecordSchema,
  metricRecordSchema,
  runManifestSchema,
  runRecordSchema
} from "./index";

const safeCapabilities = {
  readData: true,
  writeArtifacts: true,
  runSimulation: false,
  submitComputeJob: false,
  readFacilityTelemetry: false,
  controlFacility: false
} as const;

const runRecord = {
  kind: "openplazma.run",
  version: "0.1.0",
  runId: "OPR-20260524-000001",
  project: "openplazma-demo",
  campaign: "read-the-signal",
  runType: "notebook_analysis",
  status: "running",
  createdAt: "2026-05-24T00:00:00.000Z",
  updatedAt: "2026-05-24T00:00:00.000Z",
  finishedAt: null,
  target: {
    type: "local_run_store",
    id: ".openplazma",
    label: "Local OpenPlazma RunStore"
  },
  source: {
    provider: "STATIC_FIXTURE",
    sourceLabel: "STATIC_FIXTURE sample signal",
    inspiredBy: "FAIR_MAST"
  },
  capabilities: safeCapabilities,
  contextRef: null,
  artifactCount: 0,
  metricCount: 0,
  limitations: [
    "STATIC_FIXTURE data only.",
    "Not a validated fusion simulator.",
    "Not a reactor design tool.",
    "Not a real hardware control system."
  ]
};

const artifactRecord = {
  kind: "openplazma.artifact",
  version: "0.1.0",
  artifactId: "OPA-20260524-000001",
  runId: "OPR-20260524-000001",
  name: "signal_series",
  type: "signal_series",
  path: "artifacts/signal-series.json",
  sha256: "0".repeat(64),
  createdAt: "2026-05-24T00:00:01.000Z",
  metadata: {}
};

describe("tracking schemas", () => {
  it("validates a Python-like RunRecord", () => {
    expect(() => runRecordSchema.parse(runRecord)).not.toThrow();
  });

  it("validates ArtifactRecord, MetricRecord, EventRecord, and RunManifest samples", () => {
    expect(() => artifactRecordSchema.parse(artifactRecord)).not.toThrow();
    expect(() =>
      metricRecordSchema.parse({
        kind: "openplazma.metric",
        version: "0.1.0",
        runId: "OPR-20260524-000001",
        name: "signal_peak",
        value: 0.91,
        step: null,
        createdAt: "2026-05-24T00:00:02.000Z"
      })
    ).not.toThrow();
    expect(() =>
      eventRecordSchema.parse({
        kind: "openplazma.event",
        version: "0.1.0",
        runId: "OPR-20260524-000001",
        eventType: "artifact_logged",
        createdAt: "2026-05-24T00:00:03.000Z",
        message: "Logged artifact signal_series",
        metadata: { artifactId: "OPA-20260524-000001" }
      })
    ).not.toThrow();
    expect(() =>
      runManifestSchema.parse({
        kind: "openplazma.run_manifest",
        version: "0.1.0",
        runId: "OPR-20260524-000001",
        createdAt: "2026-05-24T00:00:00.000Z",
        updatedAt: "2026-05-24T00:00:03.000Z",
        artifacts: [artifactRecord]
      })
    ).not.toThrow();
  });

  it("rejects unsafe capabilities", () => {
    const unsafe = {
      ...runRecord,
      capabilities: {
        ...safeCapabilities,
        controlFacility: true
      }
    };

    expect(() => runRecordSchema.parse(unsafe)).toThrow();
  });

  it("rejects FAIR_MAST as provider and accepts it only as inspiredBy", () => {
    expect(runRecordSchema.parse(runRecord).source.inspiredBy).toBe("FAIR_MAST");

    const badProvider = {
      ...runRecord,
      source: {
        provider: "FAIR_MAST",
        sourceLabel: "Incorrect provider"
      }
    };

    expect(() => runRecordSchema.parse(badProvider)).toThrow();
  });

  it("rejects artifact path traversal", () => {
    expect(() =>
      artifactRecordSchema.parse({
        ...artifactRecord,
        path: "artifacts/../signal-series.json"
      })
    ).toThrow();
  });
});
