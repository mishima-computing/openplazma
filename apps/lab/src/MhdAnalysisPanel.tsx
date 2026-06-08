import { useMemo } from "react";
import type { MhdAnalysisBundle, SignalSeries, StudyRecord } from "@openplazma/core";
import { buildInferenceFromArray } from "@openplazma/analysis";
import { MirnovArrayChart, SignalChart, type ChartMarker } from "@openplazma/signal-viewer";

function eventMarkers(mhd: MhdAnalysisBundle): ChartMarker[] {
  return mhd.events.map((event) => ({
    time: event.timeRange[0],
    label: event.label,
    phenomenon: event.phenomenon
  }));
}

function rotationSeries(mhd: MhdAnalysisBundle): SignalSeries | null {
  const inference = mhd.inferences[0];
  if (!inference || inference.rotationTrack.length === 0) {
    return null;
  }
  return {
    kind: "openplazma.signal_series",
    version: "0.1.0",
    signalId: "rotation-frequency",
    label: "Mode rotation frequency",
    quantity: "frequency",
    unit: "Hz",
    timeUnit: "s",
    time: inference.rotationTrack.map((p) => p.time),
    values: inference.rotationTrack.map((p) => p.rotationFreqHz)
  };
}

export function MhdAnalysisPanel({ record }: { record: StudyRecord }) {
  const mhd = record.mhd;
  const array = mhd?.arrays[0];

  const coilSignals = useMemo(() => {
    if (!array) {
      return [] as SignalSeries[];
    }
    const ids = new Set(array.channels.map((c) => c.signalId));
    return record.signals.filter((s) => ids.has(s.signalId));
  }, [array, record.signals]);

  // Live, in-process recompute from the stored coil signals (read-only).
  const liveInference = useMemo(() => {
    if (!array || coilSignals.length === 0) {
      return null;
    }
    return buildInferenceFromArray(array, coilSignals);
  }, [array, coilSignals]);

  if (!mhd || !array) {
    return null;
  }

  const markers = eventMarkers(mhd);
  const rotation = rotationSeries(mhd);
  const stored = mhd.inferences[0];
  const model = mhd.observationModels[0];

  return (
    <section className="panel mhd-panel" aria-labelledby="mhd-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Post-ignition dynamics</p>
          <h2 id="mhd-heading">MHD mode analysis</h2>
        </div>
        <span className={stored?.lockingDetected ? "mhd-badge is-locked" : "mhd-badge"}>
          {stored?.lockingDetected ? "Mode locking detected" : "No locking"}
        </span>
      </div>

      <MirnovArrayChart array={array} signals={coilSignals} markers={markers} />

      {rotation ? (
        <SignalChart series={rotation} markers={markers} height={150} />
      ) : null}

      <dl className="mhd-estimate-grid">
        <div>
          <dt>Toroidal mode number n</dt>
          <dd>
            {stored?.modeEstimate.toroidalModeNumber ?? "?"}
            {model ? <small> (hypothesis {model.hypothesis.poloidalModeNumber}/{model.hypothesis.toroidalModeNumber})</small> : null}
          </dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{stored ? stored.modeEstimate.confidence.toFixed(2) : "?"}</dd>
        </div>
        <div>
          <dt>Live recompute (n)</dt>
          <dd>
            {liveInference ? liveInference.modeEstimate.toroidalModeNumber : "?"}
            {liveInference ? <small> · locking {liveInference.lockingDetected ? "yes" : "no"}</small> : null}
          </dd>
        </div>
      </dl>

      {mhd.claims.map((claim) => (
        <div key={claim.claimId} className="mhd-claim">
          <p className="mhd-claim-statement">{claim.statement}</p>
          <ul className="mhd-evidence-list">
            {claim.evidence.map((link, index) => (
              <li key={index} className={`verdict verdict-${link.verdict}`}>
                <span className="verdict-tag">{link.verdict}</span>
                <span className="verdict-rationale">{link.rationale}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}

      <p className="mhd-disclaimer">
        Synthetic, read-only analysis. Forward models are analytic, not facility simulations or control.
      </p>
    </section>
  );
}
