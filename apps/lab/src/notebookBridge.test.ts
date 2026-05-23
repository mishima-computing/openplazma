import { describe, expect, it } from "vitest";
import { sampleFixtureStudyRecord } from "@openplazma/data-client";
import {
  OPENPLAZMA_EXPERIMENT_CONTEXT_STORAGE_KEY,
  buildNotebookExperimentContext,
  buildWorkbenchLiteUrl,
  configuredWorkbenchLiteUrl
} from "./notebookBridge";

describe("notebook bridge helpers", () => {
  it("uses the expected localStorage key", () => {
    expect(OPENPLAZMA_EXPERIMENT_CONTEXT_STORAGE_KEY).toBe("openplazma.experimentContext.v0");
  });

  it("treats a blank Workbench Lite URL as unconfigured", () => {
    expect(configuredWorkbenchLiteUrl(undefined)).toBeUndefined();
    expect(configuredWorkbenchLiteUrl("   ")).toBeUndefined();
    expect(configuredWorkbenchLiteUrl(" http://127.0.0.1:8000/lab ")).toBe("http://127.0.0.1:8000/lab");
  });

  it("generates a notebook ExperimentContext for the selected signal", () => {
    const context = buildNotebookExperimentContext({
      record: sampleFixtureStudyRecord,
      selectedSignalId: "plasma-current",
      observation: "Current peaks in the static sample.",
      hypothesis: "Notebook view should reproduce the signal."
    });

    expect(context.shotRef.provider).toBe("STATIC_FIXTURE");
    expect(context.shotRef.shotId).toBe("sample-001");
    expect(context.signals[0]?.signalId).toBe("plasma-current");
    expect(context.observations[0]?.text).toContain("Current peaks");
    expect(context.hypothesis).toContain("Notebook view");
  });

  it("builds a Workbench Lite URL with encoded opContext", () => {
    const context = buildNotebookExperimentContext({
      record: sampleFixtureStudyRecord,
      selectedSignalId: "plasma-current"
    });
    const url = buildWorkbenchLiteUrl(
      "http://127.0.0.1:8000/lab/index.html?path=openplazma/experiment_notebook.ipynb",
      context
    );

    const parsed = new URL(url);
    expect(parsed.searchParams.get("path")).toBe("openplazma/experiment_notebook.ipynb");
    expect(parsed.searchParams.get("opContext")).toBeTruthy();
    expect(parsed.searchParams.get("opContext")).not.toContain("+");
    expect(parsed.searchParams.get("opContext")).not.toContain("/");
  });
});
