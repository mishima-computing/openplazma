import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { scenarioSchema, studyTaskManifestSchema, studyTaskSchema } from "./index";

const taskPath = join(process.cwd(), "study-tasks", "read-the-signal-static-v0.1.json");
const scenarioPath = join(process.cwd(), "scenarios", "read-the-signal.json");
const manifestPath = join(process.cwd(), "study-tasks", "manifest.json");

function loadJson(path: string): unknown {
  return JSON.parse(readFileSync(path, "utf8")) as unknown;
}

describe("StudyTask and Scenario schemas", () => {
  it("validates the Read the Signal StudyTask, Scenario, and manifest", () => {
    expect(() => studyTaskSchema.parse(loadJson(taskPath))).not.toThrow();
    expect(() => scenarioSchema.parse(loadJson(scenarioPath))).not.toThrow();
    expect(() => studyTaskManifestSchema.parse(loadJson(manifestPath))).not.toThrow();
  });

  it("accepts STATIC_FIXTURE provider and FAIR_MAST inspiration separately", () => {
    const task = studyTaskSchema.parse(loadJson(taskPath));

    expect(task.source.provider).toBe("STATIC_FIXTURE");
    expect(task.source.inspiredBy).toBe("FAIR_MAST");
  });

  it("rejects FAIR_MAST as current provider provenance", () => {
    const task = loadJson(taskPath) as { source: { provider: string } };
    task.source.provider = "FAIR_MAST";

    expect(() => studyTaskSchema.parse(task)).toThrow();
  });

  it("rejects unsafe capabilities", () => {
    const task = loadJson(taskPath) as { capabilities: { controlFacility: boolean } };
    task.capabilities.controlFacility = true;

    expect(() => studyTaskSchema.parse(task)).toThrow();
  });

  it("requires non-empty prompts, suggested metrics, artifacts, and kind/version fields", () => {
    const task = studyTaskSchema.parse(loadJson(taskPath));
    expect(task.prompts.every((prompt) => prompt.text.length > 0)).toBe(true);
    expect(task.suggestedMetrics.every((metric) => metric.name.length > 0)).toBe(true);
    expect(task.requiredArtifacts.length).toBeGreaterThan(0);

    const missingKind = { ...task, kind: undefined };
    expect(() => studyTaskSchema.parse(missingKind)).toThrow();
  });
});
