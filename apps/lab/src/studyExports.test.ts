import { describe, expect, it } from "vitest";
import { sampleFixtureStudyRecord } from "@openplazma/data-client";
import { experimentContextSchema, studyRecordSchema } from "@openplazma/schema";
import { buildExperimentContextExport, buildStudyRecordExport } from "./studyExports";

describe("study export helpers", () => {
  it("generates a valid StudyRecord for the selected signal and observation", () => {
    const studyRecord = buildStudyRecordExport({
      record: sampleFixtureStudyRecord,
      selectedSignalId: "loop-voltage",
      observation: "Voltage rises then falls in the short sample window.",
      hypothesis: "The profile is useful for UI validation."
    });

    expect(() => studyRecordSchema.parse(studyRecord)).not.toThrow();
    expect(studyRecord.signals).toHaveLength(1);
    expect(studyRecord.shot.signalIds).toEqual(["loop-voltage"]);
    expect(studyRecord.shot.notes).toContain("Observation:");
    expect(studyRecord.shot.source.provider).toBe("STATIC_FIXTURE");
  });

  it("generates a valid ExperimentContext from the current record", () => {
    const context = buildExperimentContextExport(sampleFixtureStudyRecord);

    expect(() => experimentContextSchema.parse(context)).not.toThrow();
    expect(context.datasetId).toBe("static-fixture-v0");
  });
});
