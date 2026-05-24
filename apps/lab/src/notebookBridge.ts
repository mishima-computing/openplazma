import type { ExperimentContext, SignalSeries, StudyRecord } from "@openplazma/core";
import { experimentContextSchema } from "@openplazma/schema";
import { getSelectedSignal } from "./studyExports";

export const OPENPLAZMA_EXPERIMENT_CONTEXT_STORAGE_KEY = "openplazma.experimentContext.v0";

export const DEFAULT_WORKBENCH_LITE_URL =
  "http://127.0.0.1:8000/lab/index.html?path=openplazma/experiment_notebook.ipynb";

export const PAGES_WORKBENCH_LITE_URL =
  "/openplazma/workbench/lab/index.html?path=openplazma/experiment_notebook.ipynb";

export const LOCAL_STATIC_WORKBENCH_LITE_URL =
  "/workbench/lab/index.html?path=openplazma/experiment_notebook.ipynb";

export type NotebookExperimentContext = ExperimentContext;

function trimmed(value: string | undefined): string | undefined {
  const clean = value?.trim();
  return clean === "" ? undefined : clean;
}

function signalTimeRange(signal: SignalSeries): [number, number] {
  return [Math.min(...signal.time), Math.max(...signal.time)];
}

export function buildNotebookExperimentContext(input: {
  record: StudyRecord;
  selectedSignalId: string;
  observation?: string;
  hypothesis?: string;
}): NotebookExperimentContext {
  experimentContextSchema.parse(input.record.context);
  const signal = getSelectedSignal(input.record, input.selectedSignalId);
  const observation = trimmed(input.observation);
  const hypothesis = trimmed(input.hypothesis);

  const context: NotebookExperimentContext = {
    kind: "openplazma.experiment_context",
    version: "0.1.0",
    contextId: `${input.record.shot.shotId}-${signal.signalId}-context`,
    projectId: input.record.context.projectId,
    datasetId: input.record.context.datasetId,
    campaign: input.record.context.campaign,
    description: input.record.context.description,
    safetyClassification: "public-educational-fixture",
    createdAt: input.record.context.createdAt,
    target: {
      type: "static_fixture",
      id: input.record.shot.shotId,
      label: "STATIC_FIXTURE sample"
    },
    source: {
      provider: "STATIC_FIXTURE",
      sourceLabel: input.record.shot.source.sourceLabel,
      inspiredBy: input.record.shot.source.inspiredBy
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
      provider: "STATIC_FIXTURE",
      shotId: input.record.shot.shotId
    },
    signals: [
      {
        signalId: signal.signalId,
        label: signal.label,
        quantity: signal.quantity,
        unit: signal.unit
      }
    ],
    view: {
      timeRange: signalTimeRange(signal)
    },
    observations: observation === undefined ? [] : [{ text: observation, signalId: signal.signalId }],
    limitations: [
      "This context uses STATIC_FIXTURE data only.",
      "This is not a validated fusion simulation, reactor design artifact, or hardware experiment.",
      "This context has no facility control capability."
    ]
  };

  if (hypothesis !== undefined) {
    context.hypothesis = hypothesis;
  }

  return experimentContextSchema.parse(context) as NotebookExperimentContext;
}

export function encodeBase64UrlJson(value: unknown): string {
  const json = JSON.stringify(value);

  if (typeof btoa === "function") {
    const bytes = new TextEncoder().encode(json);
    let binary = "";
    for (const byte of bytes) {
      binary += String.fromCharCode(byte);
    }
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/u, "");
  }

  throw new Error("Base64 encoding is not available in this runtime.");
}

function isAbsoluteUrl(value: string): boolean {
  return /^[a-z][a-z\d+.-]*:/iu.test(value);
}

export function buildWorkbenchLiteUrl(baseUrl: string, context: NotebookExperimentContext): string {
  const absolute = isAbsoluteUrl(baseUrl);
  const origin = typeof window === "undefined" ? "http://localhost" : window.location.origin;
  const url = new URL(baseUrl, origin);
  url.searchParams.set("opContext", encodeBase64UrlJson(context));
  return absolute ? url.toString() : `${url.pathname}${url.search}${url.hash}`;
}

export function configuredWorkbenchLiteUrl(value: string | undefined): string | undefined {
  const clean = value?.trim();
  return clean === "" ? undefined : clean;
}

export function defaultWorkbenchLiteUrl(isProduction: boolean, pathname?: string): string | undefined {
  if (!isProduction) {
    return undefined;
  }
  const currentPath = pathname ?? (typeof window === "undefined" ? "/" : window.location.pathname);
  return currentPath === "/openplazma" || currentPath.startsWith("/openplazma/")
    ? PAGES_WORKBENCH_LITE_URL
    : LOCAL_STATIC_WORKBENCH_LITE_URL;
}

export function storeNotebookExperimentContext(context: NotebookExperimentContext, storage: Storage = localStorage) {
  storage.setItem(OPENPLAZMA_EXPERIMENT_CONTEXT_STORAGE_KEY, JSON.stringify(context));
}
