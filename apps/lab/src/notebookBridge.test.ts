import { describe, expect, it } from "vitest";
import { sampleFixtureStudyRecord } from "@openplazma/data-client";
import {
  LOCAL_STATIC_WORKBENCH_LITE_URL,
  OPENPLAZMA_EXPERIMENT_CONTEXT_STORAGE_KEY,
  PAGES_WORKBENCH_LITE_URL,
  buildNotebookExperimentContext,
  buildWorkbenchLiteUrl,
  configuredWorkbenchLiteUrl,
  defaultWorkbenchLiteUrl
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

  it("uses the Pages Workbench Lite URL only for production defaults", () => {
    expect(defaultWorkbenchLiteUrl(false)).toBeUndefined();
    expect(defaultWorkbenchLiteUrl(true, "/openplazma/")).toBe(PAGES_WORKBENCH_LITE_URL);
    expect(defaultWorkbenchLiteUrl(true, "/")).toBe(LOCAL_STATIC_WORKBENCH_LITE_URL);
  });

  it("generates a notebook ExperimentContext for the selected signal", () => {
    const context = buildNotebookExperimentContext({
      record: sampleFixtureStudyRecord,
      selectedSignalId: "plasma-current",
      observation: "Current peaks in the static sample.",
      hypothesis: "Notebook view should reproduce the signal."
    });

    expect(context.kind).toBe("openplazma.experiment_context");
    expect(context.version).toBe("0.1.0");
    expect(context.contextId).toBe("sample-001-plasma-current-context");
    expect(context.shotRef.provider).toBe("STATIC_FIXTURE");
    expect(context.shotRef.shotId).toBe("sample-001");
    expect(context.target.type).toBe("static_fixture");
    expect(context.capabilities.readData).toBe(true);
    expect(context.capabilities.writeArtifacts).toBe(true);
    expect(context.capabilities.runSimulation).toBe(false);
    expect(context.capabilities.submitComputeJob).toBe(false);
    expect(context.capabilities.readFacilityTelemetry).toBe(false);
    expect(context.capabilities.controlFacility).toBe(false);
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

  it("builds a Pages Workbench Lite URL with encoded opContext", () => {
    const context = buildNotebookExperimentContext({
      record: sampleFixtureStudyRecord,
      selectedSignalId: "plasma-current"
    });
    const url = buildWorkbenchLiteUrl(PAGES_WORKBENCH_LITE_URL, context);

    const parsed = new URL(url, "https://mishima-computing.github.io");
    expect(url.startsWith("/openplazma/workbench/lab/index.html?")).toBe(true);
    expect(parsed.pathname).toBe("/openplazma/workbench/lab/index.html");
    expect(parsed.searchParams.get("path")).toBe("openplazma/experiment_notebook.ipynb");
    expect(parsed.searchParams.get("opContext")).toBeTruthy();
  });
});
