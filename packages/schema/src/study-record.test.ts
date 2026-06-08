import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { experimentContextSchema, fixtureManifestSchema, signalSeriesSchema, studyRecordSchema } from "./index";

describe("study record schemas", () => {
  it("validates the bundled sample fixture", () => {
    const fixturePath = join(
      process.cwd(),
      "data",
      "fixtures",
      "static",
      "sample-001",
      "study-record.json"
    );
    const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as unknown;

    expect(() => studyRecordSchema.parse(fixture)).not.toThrow();
  });

  it("validates the synthetic MHD mode fixture and its analysis bundle", () => {
    const fixturePath = join(
      process.cwd(),
      "data",
      "fixtures",
      "static",
      "mhd-mode-001",
      "study-record.json"
    );
    const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as unknown;

    const parsed = studyRecordSchema.parse(fixture);
    expect(parsed.mhd?.provenanceKind).toBe("synthetic");
    expect(parsed.mhd?.arrays[0]?.channels).toHaveLength(8);
    expect(parsed.mhd?.observationModels[0]?.producedSignalIds).toHaveLength(8);
  });

  it("validates the synthetic ELM H-mode fixture", () => {
    const fixturePath = join(
      process.cwd(),
      "data",
      "fixtures",
      "static",
      "elm-h-mode-001",
      "study-record.json"
    );
    const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as unknown;

    const parsed = studyRecordSchema.parse(fixture);
    expect(parsed.mhd?.elmAnalyses?.[0]?.classification).toBe("type_I");
    expect(parsed.mhd?.elmAnalyses?.[0]?.crashes).toHaveLength(10);
    expect(parsed.mhd?.claims[0]?.elmAnalysisId).toBe("elm-d-alpha");
  });

  it("accepts STATIC_FIXTURE provider and FAIR_MAST inspiration separately", () => {
    const fixturePath = join(
      process.cwd(),
      "data",
      "fixtures",
      "static",
      "sample-001",
      "study-record.json"
    );
    const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as { shot: { source: unknown } };
    const parsed = studyRecordSchema.parse(fixture);

    expect(parsed.shot.source.provider).toBe("STATIC_FIXTURE");
    expect(parsed.shot.source.inspiredBy).toBe("FAIR_MAST");
  });

  it("rejects FAIR_MAST as current provider provenance", () => {
    const fixturePath = join(
      process.cwd(),
      "data",
      "fixtures",
      "static",
      "sample-001",
      "study-record.json"
    );
    const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
      shot: { source: { provider: string } };
      source: { provider: string };
      context: { source: { provider: string }; shotRef: { provider: string } };
    };
    fixture.shot.source.provider = "FAIR_MAST";
    fixture.source.provider = "FAIR_MAST";
    fixture.context.source.provider = "FAIR_MAST";
    fixture.context.shotRef.provider = "FAIR_MAST";

    expect(() => studyRecordSchema.parse(fixture)).toThrow();
  });

  it("requires tracking-ready ExperimentContext metadata and safe capabilities", () => {
    const fixturePath = join(
      process.cwd(),
      "data",
      "fixtures",
      "static",
      "sample-001",
      "study-record.json"
    );
    const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
      context: {
        kind?: string;
        version?: string;
        contextId?: string;
        capabilities: { controlFacility: boolean };
        target: { type: string };
      };
    };

    expect(() => experimentContextSchema.parse(fixture.context)).not.toThrow();
    expect(fixture.context.target.type).toBe("static_fixture");
    expect(fixture.context.capabilities.controlFacility).toBe(false);

    delete fixture.context.kind;
    expect(() => experimentContextSchema.parse(fixture.context)).toThrow();
  });

  it("accepts read-only LOCAL_SIGNAL_FILE experiment context provenance", () => {
    const context = {
      kind: "openplazma.experiment_context",
      version: "0.1.0",
      contextId: "ctx-local-signal",
      projectId: "openplazma-local",
      datasetId: "local-sample",
      description: "Read-only local signal import.",
      safetyClassification: "read-only-local-signal",
      createdAt: "2026-05-24T00:00:00.000Z",
      target: {
        type: "local_run_store",
        id: ".openplazma",
        label: "Local OpenPlazma RunStore"
      },
      source: {
        provider: "LOCAL_SIGNAL_FILE",
        sourceLabel: "Local CSV",
        uri: "local-file:signal.csv",
        sha256: "a".repeat(64),
        validationStatus: "schema_validated"
      },
      capabilities: {
        readData: true,
        writeArtifacts: true,
        runSimulation: false,
        submitComputeJob: false,
        readFacilityTelemetry: false,
        controlFacility: false
      },
      shotRef: {
        provider: "LOCAL_SIGNAL_FILE",
        shotId: "local-sample"
      },
      signals: [{ signalId: "loop-voltage" }],
      observations: [],
      limitations: [
        "LOCAL_SIGNAL_FILE read-only import.",
        "Read-only analysis and decision support."
      ]
    };

    expect(() => experimentContextSchema.parse(context)).not.toThrow();
  });

  it("validates the static fixture manifest", () => {
    const fixturePath = join(process.cwd(), "data", "fixtures", "static", "manifest.json");
    const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as unknown;

    expect(() => fixtureManifestSchema.parse(fixture)).not.toThrow();
  });

  it("rejects signal series with mismatched time and value lengths", () => {
    const result = signalSeriesSchema.safeParse({
      kind: "openplazma.signal_series",
      version: "0.1.0",
      signalId: "bad-signal",
      label: "Bad signal",
      quantity: "example",
      unit: "a.u.",
      timeUnit: "s",
      time: [0, 1, 2],
      values: [1, 2]
    });

    expect(result.success).toBe(false);
  });
});
