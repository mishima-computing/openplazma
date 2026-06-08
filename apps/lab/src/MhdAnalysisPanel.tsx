import { useMemo } from "react";
import type { ElmAnalysis, MhdAnalysisBundle, SignalSeries, StudyRecord } from "@openplazma/core";
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

function EvidenceList({ evidence }: { evidence: MhdAnalysisBundle["claims"][number]["evidence"] }) {
  return (
    <ul className="mhd-evidence-list">
      {evidence.map((link, index) => (
        <li key={index} className={`verdict verdict-${link.verdict}`}>
          <span className="verdict-tag">{link.verdict}</span>
          <span className="verdict-rationale">{link.rationale}</span>
        </li>
      ))}
    </ul>
  );
}

function ElmSection({ analysis, signals }: { analysis: ElmAnalysis; signals: SignalSeries[] }) {
  const source = signals.find((s) => s.signalId === analysis.sourceSignalId) ?? null;
  const markers: ChartMarker[] = analysis.crashes.map((crash, index) => ({
    time: crash.time,
    label: `ELM ${index + 1}`,
    phenomenon: "elm_crash"
  }));
  return (
    <div className="elm-section">
      <h3>{analysis.label}</h3>
      {source ? <SignalChart series={source} markers={markers} height={160} /> : null}
      <dl className="mhd-estimate-grid">
        <div>
          <dt>ELM frequency</dt>
          <dd>{analysis.elmFrequencyHz.toFixed(0)} Hz</dd>
        </div>
        <div>
          <dt>Classification</dt>
          <dd>{analysis.classification.replace("_", "-")}</dd>
        </div>
        <div>
          <dt>Regularity</dt>
          <dd>{analysis.regularity.toFixed(2)}</dd>
        </div>
        <div>
          <dt>Crashes</dt>
          <dd>{analysis.crashes.length}</dd>
        </div>
      </dl>
    </div>
  );
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

  // For event-driven shots (sawtooth, density limit) pick the signal most events
  // point at, and show it with the timeline markers.
  const overviewSignal = useMemo(() => {
    if (!mhd) {
      return null;
    }
    const counts = new Map<string, number>();
    for (const event of mhd.events) {
      if (event.signalId) {
        counts.set(event.signalId, (counts.get(event.signalId) ?? 0) + 1);
      }
    }
    let bestId = record.signalsViewed[0]?.signalId ?? record.signals[0]?.signalId ?? "";
    let best = -1;
    for (const [id, count] of counts) {
      if (count > best) {
        best = count;
        bestId = id;
      }
    }
    return record.signals.find((s) => s.signalId === bestId) ?? null;
  }, [mhd, record.signals, record.signalsViewed]);

  if (!mhd) {
    return null;
  }

  const markers = eventMarkers(mhd);
  const rotation = rotationSeries(mhd);
  const stored = mhd.inferences[0];
  const model = mhd.observationModels[0];
  const elmAnalyses = mhd.elmAnalyses ?? [];
  const headerElm = elmAnalyses[0];

  return (
    <section className="panel mhd-panel" aria-labelledby="mhd-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Post-ignition dynamics</p>
          <h2 id="mhd-heading">
            {array ? "MHD mode analysis" : headerElm ? "Edge instability analysis" : "Event & instability analysis"}
          </h2>
        </div>
        {array ? (
          <span className={stored?.lockingDetected ? "mhd-badge is-locked" : "mhd-badge"}>
            {stored?.lockingDetected ? "Mode locking detected" : "Rotating, no locking"}
          </span>
        ) : headerElm ? (
          <span className="mhd-badge is-locked">
            {headerElm.classification.replace("_", "-")} ELMs @ {headerElm.elmFrequencyHz.toFixed(0)} Hz
          </span>
        ) : mhd.events.length > 0 ? (
          <span className="mhd-badge">{mhd.events.length} events</span>
        ) : null}
      </div>

      {array ? (
        <>
          <MirnovArrayChart array={array} signals={coilSignals} markers={markers} />
          {rotation ? <SignalChart series={rotation} markers={markers} height={150} /> : null}
          <dl className="mhd-estimate-grid">
            <div>
              <dt>Toroidal mode number n</dt>
              <dd>
                {stored?.modeEstimate.toroidalModeNumber ?? "?"}
                {model ? (
                  <small>
                    {" "}
                    (hypothesis {model.hypothesis.poloidalModeNumber}/{model.hypothesis.toroidalModeNumber})
                  </small>
                ) : null}
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
            {stored?.modeEstimate.islandWidthM != null ? (
              <div>
                <dt>Island width</dt>
                <dd>{(stored.modeEstimate.islandWidthM * 100).toFixed(1)} cm</dd>
              </div>
            ) : null}
          </dl>
        </>
      ) : null}

      {!array && elmAnalyses.length === 0 && overviewSignal ? (
        <SignalChart series={overviewSignal} markers={markers} height={180} />
      ) : null}

      {elmAnalyses.map((analysis) => (
        <ElmSection key={analysis.analysisId} analysis={analysis} signals={record.signals} />
      ))}

      {mhd.claims.map((claim) => (
        <div key={claim.claimId} className="mhd-claim">
          <p className="mhd-claim-statement">{claim.statement}</p>
          <EvidenceList evidence={claim.evidence} />
        </div>
      ))}

      <p className="mhd-disclaimer">
        Synthetic, read-only analysis. Forward models are analytic, not facility simulations or control.
      </p>
    </section>
  );
}
