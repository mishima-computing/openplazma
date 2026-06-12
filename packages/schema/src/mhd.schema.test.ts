import { describe, expect, it } from "vitest";
import type { MhdAnalysisBundle } from "@openplazma/core";
import { mhdAnalysisBundleSchema, parseMhdAnalysisBundle } from "./index";

function validBundle(): MhdAnalysisBundle {
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
        timeRange: [0.3, 0.35],
        producedByInferenceId: "inf-1",
        evidenceReadoutIds: ["locking-readout"]
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
        evidenceReadoutIds: ["phase-fit-readout"],
        modeEstimate: { toroidalModeNumber: 1, confidence: 0.9, method: "phase_fit_toroidal" },
        rotationTrack: [{ time: 0.1, rotationFreqHz: 2000, amplitude: 1 }],
        lockingDetected: true,
        lockTimeRange: [0.3, 0.35],
        assumptions: [],
        limitations: ["|n| <= channels/2 (Nyquist)"],
        alternatives: ["Aliased higher-n mode"]
      }
    ],
    readouts: [
      {
        kind: "openplazma.mhd_observation_statement",
        version: "0.1.0",
        readoutId: "phase-fit-readout",
        readoutKind: "phase_fit",
        observable: "magnetic_field",
        arrayId: "mirnov-toroidal",
        method: "magnetic_mode_phase_fit",
        status: "detected",
        timeRange: [0, 0.3],
        assumptions: ["single dominant mode"],
        limitations: ["Synthetic fixture readout, not facility telemetry."],
        alternatives: ["Aliased higher-n mode"]
      },
      {
        kind: "openplazma.mhd_observation_statement",
        version: "0.1.0",
        readoutId: "locking-readout",
        readoutKind: "event_detection",
        observable: "magnetic_field",
        arrayId: "mirnov-toroidal",
        inferenceId: "inf-1",
        method: "rotation_track_threshold",
        status: "detected",
        timeRange: [0.3, 0.35],
        assumptions: ["mode amplitude remains coherent"],
        limitations: ["Synthetic fixture readout, not facility telemetry."],
        alternatives: ["Transient amplitude dropout"]
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
            readoutId: "locking-readout",
            inferenceId: "inf-1",
            method: "rotation_track_threshold",
            timeRange: [0.3, 0.35],
            rationale: "Rotation collapses while amplitude grows.",
            assumptions: ["mode amplitude remains coherent"],
            limitations: ["Synthetic fixture readout, not facility telemetry."],
            alternatives: ["Transient amplitude dropout"]
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

  it("validates mediated MHD readouts for inference, event, and claim evidence", () => {
    const bundle = validBundle();
    bundle.events[0]!.producedByInferenceId = "inf-1";
    bundle.events[0]!.evidenceReadoutIds = ["locking-readout"];
    bundle.claims[0]!.eventIds = ["lock"];

    const parsed = parseMhdAnalysisBundle(bundle);

    expect(parsed.readouts?.map((readout) => readout.readoutId)).toContain("locking-readout");
    expect(parsed.events[0]?.producedByInferenceId).toBe("inf-1");
    expect(parsed.claims[0]?.evidence[0]?.readoutId).toBe("locking-readout");
  });

  it("rejects inferences without mediated evidence readouts", () => {
    const bundle = validBundle();
    bundle.inferences[0]!.evidenceReadoutIds = [];

    expect(() => mhdAnalysisBundleSchema.parse(bundle)).toThrow("mediated readout");
  });

  it("rejects phenomenon events that are not produced by inference or readout evidence", () => {
    const bundle = validBundle();
    delete bundle.events[0]!.producedByInferenceId;
    bundle.events[0]!.evidenceReadoutIds = [];

    expect(() => mhdAnalysisBundleSchema.parse(bundle)).toThrow("phenomenon event");
  });

  it("rejects event-only claims and empty MHD claim evidence", () => {
    const eventOnly = validBundle();
    eventOnly.events[0]!.producedByInferenceId = "inf-1";
    eventOnly.events[0]!.evidenceReadoutIds = ["locking-readout"];
    eventOnly.claims[0] = {
      kind: "openplazma.claim",
      version: "0.1.0",
      claimId: "event-only",
      statement: "The event label alone proves mode locking.",
      eventIds: ["lock"],
      evidence: [
        {
          kind: "openplazma.evidence_link",
          version: "0.1.0",
          verdict: "support",
          eventId: "lock",
          method: "event_label_shortcut",
          timeRange: [0.3, 0.35],
          rationale: "The event label says locking.",
          assumptions: ["Event label is proof."],
          limitations: ["No readout or inference is cited."],
          alternatives: []
        }
      ]
    };

    expect(() => mhdAnalysisBundleSchema.parse(eventOnly)).toThrow("bare event");

    const emptyEvidence = validBundle();
    emptyEvidence.events[0]!.producedByInferenceId = "inf-1";
    emptyEvidence.events[0]!.evidenceReadoutIds = ["locking-readout"];
    emptyEvidence.claims[0]!.evidence = [];

    expect(() => mhdAnalysisBundleSchema.parse(emptyEvidence)).toThrow("evidence");

    const signalOnly = validBundle();
    signalOnly.claims[0]!.evidence = [
      {
        kind: "openplazma.evidence_link",
        version: "0.1.0",
        verdict: "support",
        signalId: "mirnov-01",
        arrayId: "mirnov-toroidal",
        method: "raw_signal_shortcut",
        timeRange: [0.3, 0.35],
        rationale: "The raw signal is treated as the claim.",
        assumptions: ["Raw signal equals phenomenon identity."],
        limitations: ["No mediated readout or inference is cited."],
        alternatives: ["instrument response"]
      }
    ];

    expect(() => mhdAnalysisBundleSchema.parse(signalOnly)).toThrow("mediated readout or inference");
  });

  it("requires at least one diagnostic array and observation model", () => {
    const bundle = validBundle();
    bundle.arrays = [];
    expect(() => mhdAnalysisBundleSchema.parse(bundle)).toThrow();
  });
});
