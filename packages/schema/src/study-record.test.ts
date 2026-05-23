import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { fixtureManifestSchema, signalSeriesSchema, studyRecordSchema } from "./index";

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

  it("validates the static fixture manifest", () => {
    const fixturePath = join(process.cwd(), "data", "fixtures", "static", "manifest.json");
    const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as unknown;

    expect(() => fixtureManifestSchema.parse(fixture)).not.toThrow();
  });

  it("rejects signal series with mismatched time and value lengths", () => {
    const result = signalSeriesSchema.safeParse({
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
