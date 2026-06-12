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
    "Read-only analysis and decision support.",
    "No command/control path or hazardous operating procedure.",
    "Not a standalone authority for safety-critical operation or reactor design decisions."
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
      metricRecordSchema.parse({
        kind: "openplazma.metric",
        version: "0.1.0",
        runId: "OPR-20260524-000001",
        name: "nested_summary",
        value: { window: [0, 1], ok: true, note: null },
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

  it("rejects run lifecycle status and finishedAt mismatches", () => {
    expect(() =>
      runRecordSchema.parse({
        ...runRecord,
        status: "finished",
        finishedAt: null
      })
    ).toThrow();

    expect(() =>
      runRecordSchema.parse({
        ...runRecord,
        status: "running",
        finishedAt: "2026-05-24T00:00:03.000Z"
      })
    ).toThrow();
  });

  it("rejects reversed RunRecord timestamps", () => {
    expect(() =>
      runRecordSchema.parse({
        ...runRecord,
        createdAt: "2026-05-24T00:00:02.000Z",
        updatedAt: "2026-05-24T00:00:01.000Z"
      })
    ).toThrow();

    expect(() =>
      runRecordSchema.parse({
        ...runRecord,
        status: "finished",
        updatedAt: "2026-05-24T00:00:02.000Z",
        finishedAt: "2026-05-24T00:00:01.000Z"
      })
    ).toThrow();
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

  it("accepts LOCAL_SIGNAL_FILE run source with local provenance", () => {
    const localRun = {
      ...runRecord,
      source: {
        provider: "LOCAL_SIGNAL_FILE",
        sourceLabel: "Local CSV",
        uri: "local-file:signal.csv",
        sha256: "b".repeat(64),
        validationStatus: "schema_validated"
      },
      limitations: [
        "LOCAL_SIGNAL_FILE read-only import.",
        "Read-only analysis and decision support."
      ]
    };

    expect(() => runRecordSchema.parse(localRun)).not.toThrow();
  });

  it("rejects artifact path traversal", () => {
    expect(() =>
      artifactRecordSchema.parse({
        ...artifactRecord,
        path: "artifacts/../signal-series.json"
      })
    ).toThrow();
  });

  it("rejects duplicate artifact ids and paths in run manifests", () => {
    expect(() =>
      runManifestSchema.parse({
        kind: "openplazma.run_manifest",
        version: "0.1.0",
        runId: "OPR-20260524-000001",
        createdAt: "2026-05-24T00:00:00.000Z",
        updatedAt: "2026-05-24T00:00:03.000Z",
        artifacts: [
          artifactRecord,
          {
            ...artifactRecord,
            name: "duplicate_id",
            path: "artifacts/duplicate-id.json"
          }
        ]
      })
    ).toThrow();

    expect(() =>
      runManifestSchema.parse({
        kind: "openplazma.run_manifest",
        version: "0.1.0",
        runId: "OPR-20260524-000001",
        createdAt: "2026-05-24T00:00:00.000Z",
        updatedAt: "2026-05-24T00:00:03.000Z",
        artifacts: [
          artifactRecord,
          {
            ...artifactRecord,
            artifactId: "OPA-20260524-000002",
            name: "duplicate_path"
          }
        ]
      })
    ).toThrow();
  });

  it("rejects reversed RunManifest timestamps", () => {
    expect(() =>
      runManifestSchema.parse({
        kind: "openplazma.run_manifest",
        version: "0.1.0",
        runId: "OPR-20260524-000001",
        createdAt: "2026-05-24T00:00:02.000Z",
        updatedAt: "2026-05-24T00:00:01.000Z",
        artifacts: []
      })
    ).toThrow();
  });

  it("rejects RunManifest timestamps outside artifact time range", () => {
    expect(() =>
      runManifestSchema.parse({
        kind: "openplazma.run_manifest",
        version: "0.1.0",
        runId: "OPR-20260524-000001",
        createdAt: "2026-05-24T00:00:00.000Z",
        updatedAt: "2026-05-24T00:00:01.000Z",
        artifacts: [
          {
            ...artifactRecord,
            createdAt: "2026-05-24T00:00:02.000Z"
          }
        ]
      })
    ).toThrow();

    expect(() =>
      runManifestSchema.parse({
        kind: "openplazma.run_manifest",
        version: "0.1.0",
        runId: "OPR-20260524-000001",
        createdAt: "2026-05-24T00:00:02.000Z",
        updatedAt: "2026-05-24T00:00:03.000Z",
        artifacts: [
          {
            ...artifactRecord,
            createdAt: "2026-05-24T00:00:01.000Z"
          }
        ]
      })
    ).toThrow();
  });

  it("rejects nested non-finite metric values", () => {
    expect(() =>
      metricRecordSchema.parse({
        kind: "openplazma.metric",
        version: "0.1.0",
        runId: "OPR-20260524-000001",
        name: "bad_metric",
        value: { nested: Number.NaN },
        step: null,
        createdAt: "2026-05-24T00:00:02.000Z"
      })
    ).toThrow();

    expect(() =>
      metricRecordSchema.parse({
        kind: "openplazma.metric",
        version: "0.1.0",
        runId: "OPR-20260524-000001",
        name: "bad_metric",
        value: [Number.POSITIVE_INFINITY],
        step: null,
        createdAt: "2026-05-24T00:00:02.000Z"
      })
    ).toThrow();
  });

  it("rejects nested non-finite artifact and event metadata", () => {
    expect(() =>
      artifactRecordSchema.parse({
        ...artifactRecord,
        metadata: { nested: Number.NaN }
      })
    ).toThrow();

    expect(() =>
      eventRecordSchema.parse({
        kind: "openplazma.event",
        version: "0.1.0",
        runId: "OPR-20260524-000001",
        eventType: "artifact_logged",
        createdAt: "2026-05-24T00:00:03.000Z",
        message: "Logged artifact signal_series",
        metadata: { nested: Number.POSITIVE_INFINITY }
      })
    ).toThrow();
  });
});
