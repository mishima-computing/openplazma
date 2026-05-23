import type { StudyRecord } from "@openplazma/core";
import {
  buildNotebookExperimentContext,
  buildWorkbenchLiteUrl,
  configuredWorkbenchLiteUrl,
  storeNotebookExperimentContext
} from "./notebookBridge";
import { toPrettyJson } from "./studyExports";

export interface NotebookLauncherButtonProps {
  record: StudyRecord;
  selectedSignalId: string;
  observation: string;
  hypothesis: string;
  onDownloadJson: (filename: string, value: unknown) => void;
}

export function NotebookLauncherButton({
  record,
  selectedSignalId,
  observation,
  hypothesis,
  onDownloadJson
}: NotebookLauncherButtonProps) {
  return (
    <button
      type="button"
      className="primary-action"
      onClick={() => {
        const context = buildNotebookExperimentContext({
          record,
          selectedSignalId,
          observation,
          hypothesis
        });
        const configuredUrl = configuredWorkbenchLiteUrl(import.meta.env.VITE_OPENPLAZMA_WORKBENCH_LITE_URL);

        try {
          storeNotebookExperimentContext(context);
        } catch (error) {
          console.warn("ExperimentContext could not be saved to localStorage.", error);
        }

        if (configuredUrl === undefined) {
          console.log("Experiment notebook context", toPrettyJson(context));
          onDownloadJson(`${record.shot.shotId}-experiment-context.json`, context);
          return;
        }

        try {
          const workbenchUrl = buildWorkbenchLiteUrl(configuredUrl, context);
          window.open(workbenchUrl, "_blank", "noopener,noreferrer");
        } catch (error) {
          console.log("Experiment notebook context", toPrettyJson(context));
          onDownloadJson(`${record.shot.shotId}-experiment-context.json`, context);
          console.error("Workbench Lite could not be opened. Downloaded ExperimentContext instead.", error);
        }
      }}
    >
      Open Experiment Notebook
    </button>
  );
}
