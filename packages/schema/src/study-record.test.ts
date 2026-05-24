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
