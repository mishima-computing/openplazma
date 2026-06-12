import { useEffect, useMemo, useState } from "react";
import type { ShotMetadata, StudyRecord } from "@openplazma/core";
import { StaticFixtureDataSource } from "@openplazma/data-client";
import { SignalChart } from "@openplazma/signal-viewer";
import { InvestigationWorkbench } from "./InvestigationWorkbench";
import { MhdAnalysisPanel } from "./MhdAnalysisPanel";
import { NotebookLauncherButton } from "./NotebookLauncherButton";
import { ObservationNotebook } from "./ObservationNotebook";
import {
  buildExperimentContextExport,
  buildStudyRecordExport,
  getSelectedSignal,
  toPrettyJson
} from "./studyExports";

const dataSource = new StaticFixtureDataSource();

function downloadJson(filename: string, value: unknown) {
  const blob = new Blob([toPrettyJson(value)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function MetadataTable({ record }: { record: StudyRecord }) {
  return (
    <dl className="metadata-grid">
      <div>
        <dt>Provider</dt>
        <dd>{record.shot.source.provider}</dd>
      </div>
      <div>
        <dt>Inspired by</dt>
        <dd>{record.shot.source.inspiredBy ?? "None"}</dd>
      </div>
      <div>
        <dt>Dataset</dt>
        <dd>{record.context.datasetId}</dd>
      </div>
      <div>
        <dt>License</dt>
        <dd>{record.shot.source.license}</dd>
      </div>
      <div>
        <dt>Recorded</dt>
        <dd>{record.shot.recordedAt}</dd>
      </div>
      <div>
        <dt>Safety</dt>
        <dd>{record.context.safetyClassification}</dd>
      </div>
    </dl>
  );
}

export function RealSignalRoom() {
  const [shots, setShots] = useState<ShotMetadata[]>([]);
  const [selectedShotId, setSelectedShotId] = useState<string>("sample-001");
  const [record, setRecord] = useState<StudyRecord | null>(null);
  const [selectedSignalId, setSelectedSignalId] = useState<string>("");
  const [observation, setObservation] = useState("");
  const [hypothesis, setHypothesis] = useState("");
  const [exportPreview, setExportPreview] = useState("");

  useEffect(() => {
    void dataSource.listShots().then((loadedShots) => {
      setShots(loadedShots);
      setSelectedShotId((current) => current || loadedShots[0]?.shotId || "");
    });
  }, []);

  useEffect(() => {
    if (selectedShotId === "") {
      return;
    }

    void dataSource.getStudyRecord(selectedShotId).then((loadedRecord) => {
      setRecord(loadedRecord);
      setSelectedSignalId(loadedRecord?.signals[0]?.signalId ?? "");
    });
  }, [selectedShotId]);

  const selectedSignal = useMemo(() => {
    if (record === null || selectedSignalId === "") {
      return null;
    }

    return getSelectedSignal(record, selectedSignalId);
  }, [record, selectedSignalId]);

  if (record === null || selectedSignal === null) {
    return <main className="app-shell loading-shell">Loading static fixture...</main>;
  }

  return (
    <main className="room-shell">
      <aside className="shot-sidebar" aria-label="Shot list">
        <div>
          <p className="eyebrow">OpenPlazma Lab</p>
          <h1>Real Signal Room</h1>
          <p>{record.context.description}</p>
        </div>
        <div className="shot-list" role="list" aria-label="Available shots">
          {shots.map((shot) => (
            <button
              key={shot.shotId}
              type="button"
              className={shot.shotId === selectedShotId ? "shot-button is-active" : "shot-button"}
              onClick={() => setSelectedShotId(shot.shotId)}
            >
              <span>{shot.displayName}</span>
              <small>{shot.source.provider}</small>
            </button>
          ))}
        </div>
      </aside>

      <section className="room-main" aria-label="Selected shot workspace">
        <section className="panel hero-panel">
          <div>
            <p className="eyebrow">Selected Shot</p>
            <h2>{record.shot.displayName}</h2>
            <p>{record.shot.notes}</p>
          </div>
          <MetadataTable record={record} />
        </section>

        <section className="workspace-grid">
          <section className="panel signal-panel" aria-labelledby="signals-heading">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Available Signals</p>
                <h2 id="signals-heading">{selectedSignal.label}</h2>
              </div>
              <div className="signal-tabs" role="list" aria-label="Available signals">
                {record.signals.map((signal) => (
                  <button
                    key={signal.signalId}
                    type="button"
                    className={signal.signalId === selectedSignalId ? "signal-tab is-active" : "signal-tab"}
                    onClick={() => setSelectedSignalId(signal.signalId)}
                  >
                    {signal.label}
                  </button>
                ))}
              </div>
            </div>
            <SignalChart series={selectedSignal} />
            <div className="provenance-strip" aria-label="Signal provenance">
              <span>Provider: {record.shot.source.provider}</span>
              <span>Kind: {record.shot.source.kind}</span>
              <span>Path: {record.shot.source.uri}</span>
            </div>
          </section>

          <ObservationNotebook
            observation={observation}
            hypothesis={hypothesis}
            onObservationChange={setObservation}
            onHypothesisChange={setHypothesis}
          />
        </section>

        {record.mhd ? <MhdAnalysisPanel record={record} /> : null}

        <InvestigationWorkbench dataSource={dataSource} />

        <section className="panel export-panel" aria-labelledby="export-heading">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Exports</p>
              <h2 id="export-heading">Validated JSON</h2>
            </div>
            <NotebookLauncherButton
              record={record}
              selectedSignalId={selectedSignalId}
              observation={observation}
              hypothesis={hypothesis}
              onDownloadJson={downloadJson}
            />
          </div>
          <div className="export-actions">
            <button
              type="button"
              onClick={() => {
                const studyRecord = buildStudyRecordExport({
                  record,
                  selectedSignalId,
                  observation,
                  hypothesis
                });
                setExportPreview(toPrettyJson(studyRecord));
                downloadJson(`${record.shot.shotId}-study-record.json`, studyRecord);
              }}
            >
              Export StudyRecord
            </button>
            <button
              type="button"
              onClick={() => {
                const context = buildExperimentContextExport(record);
                setExportPreview(toPrettyJson(context));
                downloadJson(`${record.shot.shotId}-experiment-context.json`, context);
              }}
            >
              Export ExperimentContext
            </button>
          </div>
          <pre aria-label="Export preview">{exportPreview || "No export generated yet."}</pre>
        </section>
      </section>
    </main>
  );
}
