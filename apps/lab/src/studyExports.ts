import type { ExperimentContext, SignalSeries, StudyRecord } from "@openplazma/core";
import { experimentContextSchema, studyRecordSchema } from "@openplazma/schema";

export interface StudyExportInput {
  record: StudyRecord;
  selectedSignalId: string;
  observation?: string;
  hypothesis?: string;
}

function cleanText(value: string | undefined): string | undefined {
  const cleaned = value?.trim();
  return cleaned === "" ? undefined : cleaned;
}

function buildNotes(record: StudyRecord, observation: string | undefined, hypothesis: string | undefined) {
  const parts = [cleanText(record.shot.notes)];
  const cleanedObservation = cleanText(observation);
  const cleanedHypothesis = cleanText(hypothesis);

  if (cleanedObservation !== undefined) {
    parts.push(`Observation: ${cleanedObservation}`);
  }

  if (cleanedHypothesis !== undefined) {
    parts.push(`Hypothesis: ${cleanedHypothesis}`);
  }

  return parts.filter((part): part is string => part !== undefined).join("\n\n");
}

export function getSelectedSignal(record: StudyRecord, selectedSignalId: string): SignalSeries {
  const selectedSignal = record.signals.find((signal) => signal.signalId === selectedSignalId);

  if (selectedSignal === undefined) {
    throw new Error(`Signal '${selectedSignalId}' was not found in shot '${record.shot.shotId}'.`);
  }

  return selectedSignal;
}

export function buildStudyRecordExport(input: StudyExportInput): StudyRecord {
  const selectedSignal = getSelectedSignal(input.record, input.selectedSignalId);
  const notes = buildNotes(input.record, input.observation, input.hypothesis);
  const observation = cleanText(input.observation);
  const hypothesis = cleanText(input.hypothesis);
  const candidate: StudyRecord = {
    ...input.record,
    signalsViewed: [
      {
        signalId: selectedSignal.signalId,
        label: selectedSignal.label,
        quantity: selectedSignal.quantity,
        unit: selectedSignal.unit
      }
    ],
    observations:
      observation === undefined
        ? input.record.observations
        : [
            ...input.record.observations,
            {
              text: observation,
              signalId: selectedSignal.signalId,
              timeRange: [Math.min(...selectedSignal.time), Math.max(...selectedSignal.time)]
            }
          ],
    shot: {
      ...input.record.shot,
      signalIds: [selectedSignal.signalId],
      notes
    },
    signals: [selectedSignal]
  };

  if (hypothesis !== undefined) {
    candidate.hypothesis = hypothesis;
  } else {
    delete candidate.hypothesis;
  }

  return studyRecordSchema.parse(candidate) as StudyRecord;
}

export function buildExperimentContextExport(record: StudyRecord): ExperimentContext {
  return experimentContextSchema.parse(record.context) as ExperimentContext;
}

export function toPrettyJson(value: unknown): string {
  return `${JSON.stringify(value, null, 2)}\n`;
}
