import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { studyFlowManifestSchema, studyFlowSchema } from "./index";

const flowPath = join(process.cwd(), "study-flows", "read-the-signal-guided-v0.1.json");
const manifestPath = join(process.cwd(), "study-flows", "manifest.json");

function loadJson(path: string): unknown {
  return JSON.parse(readFileSync(path, "utf8")) as unknown;
}

describe("StudyFlow schemas", () => {
  it("validates the Read the Signal guided StudyFlow and manifest", () => {
    expect(() => studyFlowSchema.parse(loadJson(flowPath))).not.toThrow();
    expect(() => studyFlowManifestSchema.parse(loadJson(manifestPath))).not.toThrow();
  });

  it("accepts STATIC_FIXTURE provider and FAIR_MAST inspiration separately", () => {
    const flow = studyFlowSchema.parse(loadJson(flowPath));

    expect(flow.source.provider).toBe("STATIC_FIXTURE");
    expect(flow.source.inspiredBy).toBe("FAIR_MAST");
  });

  it("rejects FAIR_MAST as current provider provenance", () => {
    const flow = loadJson(flowPath) as { source: { provider: string } };
    flow.source.provider = "FAIR_MAST";

    expect(() => studyFlowSchema.parse(flow)).toThrow();
  });

  it("rejects unsafe capabilities", () => {
    const flow = loadJson(flowPath) as { capabilities: { controlFacility: boolean } };
    flow.capabilities.controlFacility = true;

    expect(() => studyFlowSchema.parse(flow)).toThrow();
  });

  it("requires non-empty steps, expected artifacts, expected metrics, checklist, and kind/version fields", () => {
    const flow = studyFlowSchema.parse(loadJson(flowPath));
    expect(flow.steps.length).toBeGreaterThan(0);
    expect(flow.expectedArtifacts.length).toBeGreaterThan(0);
    expect(flow.expectedMetrics.length).toBeGreaterThan(0);
    expect(flow.completionChecklist.length).toBeGreaterThan(0);

    const missingKind = { ...flow, kind: undefined };
    expect(() => studyFlowSchema.parse(missingKind)).toThrow();
  });
});
