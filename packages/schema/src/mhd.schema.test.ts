import { describe, expect, it } from "vitest";
import { mhdAnalysisBundleSchema, parseMhdAnalysisBundle } from "./index";

function validBundle() {
  return {
    kind: "openplazma.mhd_analysis_bundle",
    version: "0.1.0",
    provenanceKind: "synthetic",
    arrays: [
      {
        kind: "openplazma.diagnostic_array",
        version: "0.1.0",
        arrayId: "mirnov-toroidal",
        label: "Mirnov toroidal array",
        arrayKind: "mirnov_toroidal",
        channels: [
          {
            kind: "openplazma.diagnostic_channel",
            version: "0.1.0",
            channelId: "mirnov-01",
            label: "Mirnov 01",
            signalId: "mirnov-01",
            diagnosticKind: "magnetic_probe",
            geometry: { poloidalAngleRad: 0, toroidalAngleRad: 0, majorRadiusM: 1.5 }
          }
        ]
      }
    ],
    events: [
      {
        kind: "openplazma.phenomenon_event",
        version: "0.1.0",
        eventId: "lock",
        phenomenon: "mode_locking",
        label: "Mode locks",
        timeRange: [0.3, 0.35]
      }
    ],
    observationModels: [
      {
        kind: "openplazma.observation_model",
        version: "0.1.0",
        modelId: "tm-2-1",
        label: "2/1 tearing mode",
        modelType: "analytic_tearing_mode",
        targetArrayId: "mirnov-toroidal",
        hypothesis: {
          poloidalModeNumber: 2,
          toroidalModeNumber: 1,
          amplitude: 1,
          rotationFreqHz: 2000,
          phaseRad: 0,
          timeRange: [0, 0.3]
        },
        producedSignalIds: ["mirnov-01-forward"],
        assumptions: ["single dominant mode"],
        limitations: ["analytic, not a facility simulation"]
      }
    ],
    inferences: [
      {
        kind: "openplazma.inference",
        version: "0.1.0",
        inferenceId: "inf-1",
        label: "Phase-fit mode estimate",
        method: "magnetic_mode_phase_fit",
        sourceArrayId: "mirnov-toroidal",
        modeEstimate: { toroidalModeNumber: 1, confidence: 0.9, method: "phase_fit_toroidal" },
        rotationTrack: [{ time: 0.1, rotationFreqHz: 2000, amplitude: 1 }],
        lockingDetected: true,
        lockTimeRange: [0.3, 0.35],
        assumptions: [],
        limitations: ["|n| <= channels/2 (Nyquist)"]
      }
    ],
    claims: [
      {
        kind: "openplazma.claim",
        version: "0.1.0",
        claimId: "claim-1",
        statement: "A 2/1 tearing mode locks and precedes disruption.",
        observationModelId: "tm-2-1",
        inferenceId: "inf-1",
        evidence: [
          {
            kind: "openplazma.evidence_link",
            version: "0.1.0",
            verdict: "support",
            arrayId: "mirnov-toroidal",
            timeRange: [0.3, 0.35],
            rationale: "Rotation collapses while amplitude grows."
          }
        ]
      }
    ]
  };
}

describe("MhdAnalysisBundle schema", () => {
  it("parses a valid synthetic bundle", () => {
    const bundle = parseMhdAnalysisBundle(validBundle());
    expect(bundle.arrays[0]?.channels.length).toBe(1);
    expect(bundle.provenanceKind).toBe("synthetic");
  });

  it("rejects a claim referencing an unknown observation model", () => {
    const bundle = validBundle();
    bundle.claims[0]!.observationModelId = "does-not-exist";
    expect(() => mhdAnalysisBundleSchema.parse(bundle)).toThrow();
  });

  it("rejects an observation model targeting an unknown array", () => {
    const bundle = validBundle();
    bundle.observationModels[0]!.targetArrayId = "ghost-array";
    expect(() => mhdAnalysisBundleSchema.parse(bundle)).toThrow();
  });

  it("rejects evidence referencing an unknown array", () => {
    const bundle = validBundle();
    bundle.claims[0]!.evidence[0]!.arrayId = "ghost-array";
    expect(() => mhdAnalysisBundleSchema.parse(bundle)).toThrow();
  });

  it("requires at least one diagnostic array and observation model", () => {
    const bundle = validBundle();
    bundle.arrays = [];
    expect(() => mhdAnalysisBundleSchema.parse(bundle)).toThrow();
  });
});
