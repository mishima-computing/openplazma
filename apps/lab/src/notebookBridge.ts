import type { SignalSeries, StudyRecord } from "@openplazma/core";
import { experimentContextSchema } from "@openplazma/schema";
import { getSelectedSignal } from "./studyExports";

export const OPENPLAZMA_EXPERIMENT_CONTEXT_STORAGE_KEY = "openplazma.experimentContext.v0";

export const DEFAULT_WORKBENCH_LITE_URL =
  "http://127.0.0.1:8000/lab/index.html?path=openplazma/experiment_notebook.ipynb";

export interface NotebookExperimentContext {
  kind: "openplazma.experiment_context";
  version: "0.1";
  studyId: string;
  createdAt: string;
  shotRef: {
    provider: "STATIC_FIXTURE";
    shotId: string;
  };
  signals: Array<{
    signalId: string;
    label: string;
    quantity: string;
    unit: string;
  }>;
  view: {
    timeRange: [number, number];
  };
  observations: Array<{
    text: string;
  }>;
  hypothesis?: string;
  limitations: string[];
}

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
    version: "0.1",
    studyId: `${input.record.shot.shotId}-${signal.signalId}-study`,
    createdAt: input.record.context.createdAt,
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
    observations: observation === undefined ? [] : [{ text: observation }],
    limitations: [
      "This context uses STATIC_FIXTURE data only.",
      "This is not a validated fusion simulation or hardware experiment."
    ]
  };

  if (hypothesis !== undefined) {
    context.hypothesis = hypothesis;
  }

  return context;
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

export function buildWorkbenchLiteUrl(baseUrl: string, context: NotebookExperimentContext): string {
  const url = new URL(baseUrl);
  url.searchParams.set("opContext", encodeBase64UrlJson(context));
  return url.toString();
}

export function configuredWorkbenchLiteUrl(value: string | undefined): string | undefined {
  const clean = value?.trim();
  return clean === "" ? undefined : clean;
}

export function storeNotebookExperimentContext(context: NotebookExperimentContext, storage: Storage = localStorage) {
  storage.setItem(OPENPLAZMA_EXPERIMENT_CONTEXT_STORAGE_KEY, JSON.stringify(context));
}
