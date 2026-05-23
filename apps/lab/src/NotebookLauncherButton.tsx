import type { StudyRecord } from "@openplazma/core";
import { buildExperimentContextExport, toPrettyJson } from "./studyExports";

export interface NotebookLauncherButtonProps {
  record: StudyRecord;
  onDownloadJson: (filename: string, value: unknown) => void;
}

export function NotebookLauncherButton({ record, onDownloadJson }: NotebookLauncherButtonProps) {
  return (
    <button
      type="button"
      className="primary-action"
      onClick={() => {
        const context = buildExperimentContextExport(record);
        console.log("Experiment notebook context", toPrettyJson(context));
        onDownloadJson(`${record.shot.shotId}-experiment-context.json`, context);
      }}
    >
      Open Experiment Notebook
    </button>
  );
}
