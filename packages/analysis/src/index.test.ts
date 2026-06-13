import type {
  DiagnosticArtifact,
  DiagnosticArray,
  InvestigationPackage,
  RotationTrackPoint,
  SignalSeries,
  StudyRecord
} from "@openplazma/core";
import { describe, expect, it } from "vitest";
import {
  analyzeElms,
  analyzeTemporalFrequency,
  addDiagnosticArtifact,
  addInvestigationClaim,
  addObservationStatement,
  assessDiagnosticArtifact,
  assessInvestigationMeasurements,
  assessInvestigationSession,
  assessConservativeFusionClaim,
  buildElectromagneticCarrierAnalysis,
  buildInvestigationPackage,
  buildStudyRecordSignalEvidence,
  buildInferenceFromArray,
  crashStats,
  createInvestigationSession,
  createInvestigationSessionReport,
  detectElmCrashes,
  detectModeLocking,
  detectPeriodicCrashes,
  detectThresholdCrossing,
  estimateNtmIslandWidth,
  estimatePoloidalModeNumber,
  estimateToroidalModeNumber,
  forwardTearingModeSignals,
  addSignalEvidenceToInvestigationPackage,
  recordInvestigationReport,
  trackRotationFrequency
} from "./index";

const TWO_PI = Math.PI * 2;

function toroidalArray(channelCount: number): DiagnosticArray {
  return {
    kind: "openplazma.diagnostic_array",
    version: "0.1.0",
    arrayId: "mirnov-toroidal",
    label: "Mirnov toroidal array",
    arrayKind: "mirnov_toroidal",
    channels: Array.from({ length: channelCount }, (_, k) => ({
      kind: "openplazma.diagnostic_channel" as const,
      version: "0.1.0" as const,
      channelId: `mirnov-${k}`,
      label: `Mirnov ${k}`,
      signalId: `mirnov-${k}`,
      diagnosticKind: "magnetic_probe" as const,
      geometry: {
        poloidalAngleRad: 0,
        toroidalAngleRad: (k * TWO_PI) / channelCount,
        majorRadiusM: 1.5
      }
    }))
  };
}

function poloidalArray(channelCount: number): DiagnosticArray {
  return {
    kind: "openplazma.diagnostic_array",
    version: "0.1.0",
    arrayId: "mirnov-poloidal",
    label: "Mirnov poloidal array",
    arrayKind: "mirnov_poloidal",
    channels: Array.from({ length: channelCount }, (_, k) => ({
      kind: "openplazma.diagnostic_channel" as const,
      version: "0.1.0" as const,
      channelId: `mirnov-p-${k}`,
      label: `Mirnov P ${k}`,
      signalId: `mirnov-p-${k}`,
      diagnosticKind: "magnetic_probe" as const,
      geometry: {
        poloidalAngleRad: (k * TWO_PI) / channelCount,
        toroidalAngleRad: 0,
        majorRadiusM: 1.5
      }
    }))
  };
}

function timeGrid(samples: number, dt: number): number[] {
  return Array.from({ length: samples }, (_, i) => i * dt);
}

describe("forward/inverse mode analysis", () => {
  it("recovers the toroidal mode number a forward model imprinted (round trip)", () => {
    const array = toroidalArray(8);
    const time = timeGrid(2000, 1e-5);
    const signals = forwardTearingModeSignals(
      array,
      { poloidalModeNumber: 2, toroidalModeNumber: 1, amplitude: 1, rotationFreqHz: 2000, phaseRad: 0.4, timeRange: [0, 0.02] },
      time
    );
    // forward signals are produced with a "-forward" suffix; map them onto channel ids
    const mapped: SignalSeries[] = signals.map((s, k) => ({ ...s, signalId: `mirnov-${k}` }));

    const estimate = estimateToroidalModeNumber(array.channels, mapped, [0, 0.02]);
    expect(estimate.toroidalModeNumber).toBe(1);
    expect(estimate.confidence).toBeGreaterThan(0.95);
  });

  it("recovers the poloidal mode number for a poloidal array", () => {
    const array = poloidalArray(12);
    const time = timeGrid(2000, 1e-5);
    const signals = forwardTearingModeSignals(
      array,
      { poloidalModeNumber: 3, toroidalModeNumber: 1, amplitude: 1, rotationFreqHz: 1500, phaseRad: 0, timeRange: [0, 0.02] },
      time
    );
    const mapped: SignalSeries[] = signals.map((s, k) => ({ ...s, signalId: `mirnov-p-${k}` }));

    const estimate = estimatePoloidalModeNumber(array.channels, mapped, [0, 0.02]);
    expect(estimate.poloidalModeNumber).toBe(3);
  });

  it("aliases high mode numbers to their principal value (n=9 with 8 probes -> 1)", () => {
    const array = toroidalArray(8);
    const time = timeGrid(2000, 1e-5);
    const signals = forwardTearingModeSignals(
      array,
      { poloidalModeNumber: 2, toroidalModeNumber: 9, amplitude: 1, rotationFreqHz: 2000, phaseRad: 0, timeRange: [0, 0.02] },
      time
    );
    const mapped: SignalSeries[] = signals.map((s, k) => ({ ...s, signalId: `mirnov-${k}` }));

    const estimate = estimateToroidalModeNumber(array.channels, mapped, [0, 0.02]);
    expect(estimate.toroidalModeNumber).not.toBe(9);
    expect(estimate.toroidalModeNumber).toBe(1);
  });

  it("detects mode locking when rotation collapses while amplitude grows", () => {
    const track: RotationTrackPoint[] = [
      { time: 0.0, rotationFreqHz: 2000, amplitude: 1.0 },
      { time: 0.1, rotationFreqHz: 1500, amplitude: 1.3 },
      { time: 0.2, rotationFreqHz: 400, amplitude: 1.8 },
      { time: 0.3, rotationFreqHz: 20, amplitude: 2.4 },
      { time: 0.4, rotationFreqHz: 10, amplitude: 2.6 }
    ];
    const result = detectModeLocking(track);
    expect(result.locked).toBe(true);
    expect(result.lockTimeRange?.[0]).toBeGreaterThanOrEqual(0.3);
  });

  it("reports no locking for a steadily rotating mode", () => {
    const track: RotationTrackPoint[] = [
      { time: 0.0, rotationFreqHz: 2000, amplitude: 1.0 },
      { time: 0.1, rotationFreqHz: 1990, amplitude: 1.0 },
      { time: 0.2, rotationFreqHz: 2010, amplitude: 1.0 }
    ];
    expect(detectModeLocking(track).locked).toBe(false);
  });

  it("builds an inference carrying the Nyquist limitation", () => {
    const array = toroidalArray(8);
    const time = timeGrid(2000, 1e-5);
    const signals = forwardTearingModeSignals(
      array,
      { poloidalModeNumber: 2, toroidalModeNumber: 1, amplitude: 1, rotationFreqHz: 2000, phaseRad: 0, timeRange: [0, 0.02] },
      time
    ).map((s, k) => ({ ...s, signalId: `mirnov-${k}` }));

    const inference = buildInferenceFromArray(array, signals);
    expect(inference.modeEstimate.toroidalModeNumber).toBe(1);
    expect(inference.rotationTrack.length).toBeGreaterThan(0);
    expect(inference.limitations.join(" ")).toContain("Nyquist");
    expect(inference.modeEstimate.islandWidthM).toBeUndefined();
  });

  it("includes an island-width estimate when a calibration gain is given", () => {
    const array = toroidalArray(8);
    const time = timeGrid(2000, 1e-5);
    const signals = forwardTearingModeSignals(
      array,
      { poloidalModeNumber: 3, toroidalModeNumber: 2, amplitude: 1.5, rotationFreqHz: 2000, phaseRad: 0, timeRange: [0, 0.02] },
      time
    ).map((s, k) => ({ ...s, signalId: `mirnov-${k}` }));

    const inference = buildInferenceFromArray(array, signals, { islandWidthGain: 0.05 });
    expect(inference.modeEstimate.islandWidthM).toBeGreaterThan(0);
  });

  it("tracks rotation frequency near the imprinted value", () => {
    const array = toroidalArray(8);
    const time = timeGrid(2000, 1e-5);
    const signals = forwardTearingModeSignals(
      array,
      { poloidalModeNumber: 2, toroidalModeNumber: 1, amplitude: 1, rotationFreqHz: 2000, phaseRad: 0, timeRange: [0, 0.02] },
      time
    ).map((s, k) => ({ ...s, signalId: `mirnov-${k}` }));

    const track = trackRotationFrequency(array.channels, signals, { windowSamples: 256, stepSamples: 128 });
    const mid = track[Math.floor(track.length / 2)];
    expect(mid).toBeDefined();
    expect(Math.abs((mid?.rotationFreqHz ?? 0) - 2000)).toBeLessThan(200);
  });
});

function dalphaSignal(periodSec: number, count: number, dt: number): SignalSeries {
  const samples = Math.round((count + 1) * periodSec / dt);
  const time: number[] = [];
  const values: number[] = [];
  for (let i = 0; i < samples; i += 1) {
    const t = i * dt;
    let v = 0.2;
    for (let k = 1; k <= count; k += 1) {
      const tc = k * periodSec;
      v += 1.5 * Math.exp(-((t - tc) * (t - tc)) / (2 * (dt * 1.5) ** 2));
    }
    time.push(Number(t.toFixed(6)));
    values.push(Number(v.toFixed(4)));
  }
  return {
    kind: "openplazma.signal_series",
    version: "0.1.0",
    signalId: "d-alpha",
    label: "D-alpha",
    quantity: "photon_flux",
    unit: "a.u.",
    timeUnit: "s",
    time,
    values
  };
}

describe("ELM analysis", () => {
  it("detects periodic ELM crashes in a D-alpha signal", () => {
    const series = dalphaSignal(0.01, 10, 1e-4);
    const crashes = detectElmCrashes(series, { thresholdSigma: 1.5, minSpacingSec: 0.005 });
    expect(crashes.length).toBe(10);
  });

  it("estimates ELM frequency and flags regular crashes as Type I", () => {
    const series = dalphaSignal(0.01, 10, 1e-4); // 100 Hz cadence
    const analysis = analyzeElms(series, { thresholdSigma: 1.5, minSpacingSec: 0.005 });
    expect(Math.abs(analysis.elmFrequencyHz - 100)).toBeLessThan(10);
    expect(analysis.regularity).toBeGreaterThan(0.9);
    expect(analysis.classification).toBe("type_I");
    expect(analysis.sourceSignalId).toBe("d-alpha");
  });
});

describe("investigation frequency analysis", () => {
  it("extracts a dominant brightness modulation frequency from a signal", () => {
    const time = timeGrid(1000, 0.01);
    const values = time.map((t) => 2 + 0.5 * Math.cos(TWO_PI * 3 * t + 0.2));
    const series: SignalSeries = {
      kind: "openplazma.signal_series",
      version: "0.1.0",
      signalId: "brightness",
      label: "Brightness",
      quantity: "brightness",
      unit: "a.u.",
      timeUnit: "s",
      time,
      values
    };

    const analysis = analyzeTemporalFrequency(series, {
      analysisId: "brightness-fft",
      domain: "intensity_modulation",
      maxFrequencyHz: 20
    });

    expect(analysis.domain).toBe("intensity_modulation");
    expect(analysis.method).toBe("fft");
    expect(analysis.sampleRateHz).toBeCloseTo(100, 6);
    expect(analysis.bands[0]?.upperFrequencyHz).toBeLessThanOrEqual(20);
    expect(analysis.peaks[0]?.frequencyHz).toBeCloseTo(3, 1);
    expect(analysis.limitations.join(" ")).toContain("does not prove");
  });

  it("builds an electromagnetic carrier analysis from wavelengths", () => {
    const analysis = buildElectromagneticCarrierAnalysis({
      analysisId: "visible-carrier",
      sourceQuantity: "spectral_radiance",
      lowerWavelengthMeters: 700e-9,
      upperWavelengthMeters: 400e-9,
      bandId: "visible",
      label: "Visible carrier band",
      peakWavelengthMeters: 550e-9,
      description: "Visible-light carrier range."
    });

    expect(analysis.domain).toBe("electromagnetic_carrier");
    expect(analysis.method).toBe("spectral_line_fit");
    expect(analysis.bands[0]?.lowerFrequencyHz).toBeLessThan(analysis.bands[0]?.upperFrequencyHz ?? 0);
    expect(analysis.peaks[0]?.frequencyHz).toBeGreaterThan(5e14);
    expect(analysis.peaks[0]?.limitations.join(" ")).toContain("not a fusion-product claim");
  });

  it("rejects invalid wavelengths", () => {
    expect(() =>
      buildElectromagneticCarrierAnalysis({
        analysisId: "bad-carrier",
        sourceQuantity: "spectral_radiance",
        lowerWavelengthMeters: 0,
        upperWavelengthMeters: 400e-9,
        bandId: "bad",
        label: "Bad carrier band",
        description: "Invalid wavelength."
      })
    ).toThrow("wavelengthMeters");
  });
});

describe("mixed-signal diagnostic assessment", () => {
  function studyRecordForSignal(series: SignalSeries): StudyRecord {
    return {
      kind: "openplazma.study_record",
      version: "0.1.0",
      studyId: "study-signal-bridge",
      createdAt: "2026-06-13T00:00:00.000Z",
      source: {
        provider: "STATIC_FIXTURE",
        sourceLabel: "Static signal fixture",
        inspiredBy: "FAIR_MAST",
        shotId: "shot-signal-bridge"
      },
      shotRef: {
        provider: "STATIC_FIXTURE",
        shotId: "shot-signal-bridge"
      },
      signalsViewed: [{ signalId: series.signalId, label: series.label, quantity: series.quantity, unit: series.unit }],
      observations: [],
      limitations: ["Static signal bridge fixture."],
      context: {
        kind: "openplazma.experiment_context",
        version: "0.1.0",
        contextId: "ctx-signal-bridge",
        projectId: "openplazma-test",
        datasetId: "signal-bridge",
        description: "Signal bridge fixture.",
        safetyClassification: "public-educational-fixture",
        createdAt: "2026-06-13T00:00:00.000Z",
        target: {
          type: "static_fixture",
          id: "signal-bridge-target",
          label: "Signal bridge target"
        },
        source: {
          provider: "STATIC_FIXTURE",
          sourceLabel: "Static signal fixture",
          inspiredBy: "FAIR_MAST"
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
          shotId: "shot-signal-bridge"
        },
        signals: [{ signalId: series.signalId, label: series.label, quantity: series.quantity, unit: series.unit }],
        observations: [],
        limitations: ["Read-only fixture."]
      },
      shot: {
        kind: "openplazma.shot_metadata",
        version: "0.1.0",
        shotId: "shot-signal-bridge",
        displayName: "Signal bridge shot",
        sourceLabel: "Static signal fixture",
        recordedAt: "2026-06-13T00:00:00.000Z",
        source: {
          kind: "fixture",
          provider: "STATIC_FIXTURE",
          sourceLabel: "Static signal fixture",
          inspiredBy: "FAIR_MAST",
          uri: "static-fixture:signal-bridge",
          license: "MIT"
        },
        signalIds: [series.signalId],
        tags: ["test"]
      },
      signals: [series]
    };
  }

  function humanEyeArtifact(): DiagnosticArtifact {
    return {
      kind: "openplazma.diagnostic_artifact",
      version: "0.1.0",
      artifactId: "eye-report",
      artifactKind: "event_log",
      label: "Human visual report",
      provenanceKind: "testimony",
      instrument: {
        instrumentKind: "human_eye",
        label: "Unaided human eye",
        observables: ["visible_light"],
        calibration: {
          status: "uncalibrated",
          responseKnown: false,
          correctionApplied: false,
          description: "No calibrated visual response.",
          limitations: ["Human vision does not separate plasma light and thermal glow unaided."]
        }
      },
      contributions: [
        {
          contributionKind: "plasma_emission",
          role: "candidate",
          status: "unresolved",
          description: "Could be plasma emission.",
          limitations: ["No line-resolved diagnostic."]
        },
        {
          contributionKind: "background",
          role: "contaminant",
          status: "modeled",
          description: "Background light is present.",
          limitations: ["Background model is rough."]
        }
      ],
      description: "Witness report.",
      limitations: ["Testimony is not a calibrated diagnostic."]
    };
  }

  function mixedCurrentArtifact(): DiagnosticArtifact {
    return {
      kind: "openplazma.diagnostic_artifact",
      version: "0.1.0",
      artifactId: "mixed-current",
      artifactKind: "signal_series",
      label: "Mixed current",
      provenanceKind: "measured",
      instrument: {
        instrumentKind: "current_probe",
        label: "Current probe",
        observables: ["electric_current"],
        calibration: {
          status: "estimated",
          responseKnown: false,
          correctionApplied: false,
          description: "Estimated response.",
          limitations: ["Thermal, optical, and gravity-like coupling are not separated."]
        }
      },
      contributions: [
        {
          contributionKind: "thermal_coupling",
          role: "candidate",
          status: "unresolved",
          description: "Heat may induce current.",
          limitations: ["Thermal coupling is uncalibrated."]
        },
        {
          contributionKind: "instrument_noise",
          role: "noise",
          status: "unresolved",
          description: "Electronics noise may contribute.",
          limitations: ["Noise floor is estimated."]
        }
      ],
      signalIds: ["current"],
      quantity: "electric_current",
      unit: "A",
      description: "Mixed current trace.",
      limitations: ["Current trace is mixed-source until decomposed."]
    };
  }

  it("marks an unaided human-eye artifact as unable to identify a source", () => {
    const assessment = assessDiagnosticArtifact(humanEyeArtifact(), ["visible_light", "neutron_flux"]);

    expect(assessment.calibrationStatus).toBe("uncalibrated");
    expect(assessment.identifiability).toBe("source_identity_not_supported");
    expect(assessment.missingObservables).toContain("neutron_flux");
    expect(assessment.unresolvedContributions).toContain("plasma_emission:unresolved");
    expect(assessment.noiseContributions).toContain("background:modeled");
  });

  it("preserves unresolved coupling and noise in a mixed current artifact", () => {
    const assessment = assessDiagnosticArtifact(mixedCurrentArtifact(), ["electric_current"]);

    expect(assessment.identifiability).toBe("source_identity_candidate_only");
    expect(assessment.measuredObservables).toEqual(["electric_current"]);
    expect(assessment.unresolvedContributions).toContain("thermal_coupling:unresolved");
    expect(assessment.noiseContributions).toContain("instrument_noise:unresolved");
    expect(assessment.summary).toContain("cannot identify");
  });

  it("summarizes missing observables across an investigation package", () => {
    const pack: InvestigationPackage = {
      kind: "openplazma.investigation_package",
      version: "0.1.0",
      packageId: "mixed-test",
      title: "Mixed signal test",
      target: {
        kind: "openplazma.investigation_target",
        version: "0.1.0",
        targetId: "target",
        targetKind: "unknown",
        label: "Target",
        description: "Target under test.",
        candidateEnergySources: ["unknown"],
        limitations: ["Fixture target."]
      },
      questions: [
        {
          questionId: "q-source",
          questionKind: "energy_source_classification",
          text: "What source is supported?"
        }
      ],
      artifacts: [humanEyeArtifact(), mixedCurrentArtifact()],
      fusionAssessment: {
        kind: "openplazma.fusion_condition_assessment",
        version: "0.1.0",
        assessmentId: "assessment",
        fusionStatus: "unknown",
        conditionMode: "unknown",
        reactionCandidates: ["unknown"],
        observedOrInferredConditions: [],
        requiredConditions: [],
        unknowns: ["particle products"],
        assumptions: [],
        limitations: ["No fusion claim is resolved."]
      },
      claims: [],
      limitations: ["Package-level fixture."]
    };

    const assessment = assessInvestigationMeasurements(pack, ["visible_light", "electric_current", "neutron_flux"]);

    expect(assessment.packageId).toBe("mixed-test");
    expect(assessment.artifactAssessments).toHaveLength(2);
    expect(assessment.missingObservables).toEqual(["neutron_flux"]);
    expect(assessment.unresolvedArtifactIds).toEqual(["eye-report", "mixed-current"]);
  });

  it("bridges StudyRecord signals into mediated evidence and keeps fusion untested", () => {
    const time = timeGrid(200, 0.01);
    const series: SignalSeries = {
      kind: "openplazma.signal_series",
      version: "0.1.0",
      signalId: "thermal-brightness",
      label: "Thermal brightness",
      quantity: "brightness",
      unit: "a.u.",
      timeUnit: "s",
      time,
      values: time.map((t) => 1 + 0.2 * Math.cos(TWO_PI * 2 * t))
    };
    const evidence = buildStudyRecordSignalEvidence(studyRecordForSignal(series), { maxFrequencyHz: 10 });
    const pack = buildInvestigationPackage({
      packageId: "signal-bridge-package",
      title: "Signal bridge package",
      target: {
        kind: "openplazma.investigation_target",
        version: "0.1.0",
        targetId: "signal-bridge-target",
        targetKind: "unknown",
        label: "Signal bridge target",
        description: "Unknown energy-source target.",
        candidateEnergySources: ["fusion", "sensor_artifact", "unknown"],
        limitations: ["Candidate labels are hypotheses, not evidence."]
      },
      questions: [
        {
          questionId: "q-fusion",
          questionKind: "is_fusion",
          text: "Is a fusion claim supported?"
        }
      ]
    });
    const withEvidence = addSignalEvidenceToInvestigationPackage(pack, evidence);
    const assessment = assessConservativeFusionClaim(withEvidence);

    expect(evidence.artifacts[0]?.signalWindows?.[0]?.signalId).toBe("thermal-brightness");
    expect(evidence.observations[0]?.readoutKind).toBe("frequency_peak");
    expect(withEvidence.observations).toHaveLength(1);
    expect(assessment.disposition).toBe("fusion_claim_untested");
    expect(assessment.claim.status).toBe("untested");
    expect(assessment.limitations.join(" ")).toContain("not treated as a premise");
  });

  it("does not treat inverse fusion-condition assumptions as a supported claim", () => {
    const pack = buildInvestigationPackage({
      packageId: "inverse-claim-package",
      title: "Inverse claim package",
      target: {
        kind: "openplazma.investigation_target",
        version: "0.1.0",
        targetId: "inverse-target",
        targetKind: "stellar_object",
        label: "Inverse target",
        description: "Target with an inverse fusion-condition premise.",
        candidateEnergySources: ["fusion", "unknown"],
        limitations: ["The premise still needs evidence."]
      },
      questions: [
        {
          questionId: "q-fusion",
          questionKind: "is_fusion",
          text: "Is the fusion claim supported?"
        }
      ],
      fusionAssessment: {
        kind: "openplazma.fusion_condition_assessment",
        version: "0.1.0",
        assessmentId: "inverse-claim-assessment",
        fusionStatus: "supported",
        conditionMode: "inverse_from_fusion_condition",
        reactionCandidates: ["proton_proton_chain"],
        observedOrInferredConditions: [],
        requiredConditions: [
          {
            parameter: "ion_temperature",
            status: "required",
            logicalRole: "necessary",
            evidenceArtifactIds: [],
            assumptions: ["A fusion premise would require ion temperature support."],
            limitations: ["No mediated ion temperature readout is present."]
          }
        ],
        unknowns: ["ion temperature", "particle products"],
        assumptions: ["Fusion is only an inverse-stage premise."],
        limitations: ["Inverse reasoning does not prove fusion."]
      }
    });
    const assessment = assessConservativeFusionClaim(pack);

    expect(assessment.disposition).toBe("fusion_claim_untested");
    expect(assessment.claim.status).toBe("untested");
    expect(assessment.missingRequiredConditions).toContain("ion_temperature");
  });

  it("supports a neutral external investigation session from evidence to report", () => {
    const pack = buildInvestigationPackage({
      packageId: "external-session-001",
      title: "External investigation session",
      target: {
        kind: "openplazma.investigation_target",
        version: "0.1.0",
        targetId: "external-target",
        targetKind: "unknown",
        label: "External target",
        description: "A target supplied by an external application.",
        candidateEnergySources: ["unknown", "plasma", "fusion"],
        limitations: ["External target semantics are supplied outside OpenPlazma."]
      },
      questions: [
        {
          questionId: "q-source",
          questionKind: "energy_source_classification",
          text: "Which source claim is supported by the evidence?"
        }
      ]
    });
    const session = createInvestigationSession({
      sessionId: "session-external-001",
      package: pack,
      requiredObservables: ["visible_light", "electric_current", "neutron_flux"],
      createdAt: "2026-06-13T00:00:00.000Z"
    });

    const withArtifact = addDiagnosticArtifact(session, humanEyeArtifact(), "2026-06-13T00:01:00.000Z");
    const withReadout = addObservationStatement(
      withArtifact,
      {
        kind: "openplazma.observation_statement",
        version: "0.1.0",
        readoutId: "eye-visible-readout",
        artifactId: "eye-report",
        observable: "visible_light",
        readoutKind: "human_report",
        method: "unaided_visual_report",
        status: "candidate",
        assumptions: ["The witness report is sincere."],
        limitations: ["Human vision is not calibrated to separate source mechanisms."],
        alternatives: ["thermal glow", "chemical luminescence", "reflection"]
      },
      "2026-06-13T00:01:30.000Z"
    );
    const withClaim = addInvestigationClaim(
      withReadout,
      {
        kind: "openplazma.investigation_claim",
        version: "0.1.0",
        claimId: "claim-visible-only-insufficient",
        claimType: "fusion_status",
        statement: "Visible testimony alone does not support a fusion claim.",
        status: "support",
        evidenceArtifactIds: ["eye-report"],
        evidenceReadoutIds: ["eye-visible-readout"],
        method: "evidence_gap_review",
        assumptions: [],
        limitations: ["No particle product diagnostic is attached."],
        alternatives: ["chemical luminescence", "thermal emission", "reflection"]
      },
      "2026-06-13T00:02:00.000Z"
    );
    const assessment = assessInvestigationSession(withClaim);
    const report = createInvestigationSessionReport(withClaim, {
      createdAt: "2026-06-13T00:03:00.000Z"
    });
    const reported = recordInvestigationReport(withClaim, report, "2026-06-13T00:04:00.000Z");

    expect(session.status).toBe("collecting_evidence");
    expect(withClaim.status).toBe("ready_for_report");
    expect(assessment.readyForReport).toBe(true);
    expect(assessment.measurementAssessment.missingObservables).toEqual(["electric_current", "neutron_flux"]);
    expect(report.packageId).toBe("external-session-001");
    expect(report.nextObservations.join(" ")).toContain("neutron_flux");
    expect(reported.status).toBe("reported");
    expect(reported.reports).toHaveLength(1);
  });

  it("rejects package claims that reference evidence outside the package boundary", () => {
    expect(() =>
      buildInvestigationPackage({
        packageId: "package-boundary-test",
        title: "Package boundary test",
        target: {
          kind: "openplazma.investigation_target",
          version: "0.1.0",
          targetId: "package-boundary-target",
          targetKind: "unknown",
          label: "Package boundary target",
          description: "Package boundary target.",
          candidateEnergySources: ["unknown"],
          limitations: ["Boundary fixture."]
        },
        questions: [
          {
            questionId: "q-source",
            questionKind: "energy_source_classification",
            text: "What source is supported?"
          }
        ],
        artifacts: [humanEyeArtifact()],
        claims: [
          {
            kind: "openplazma.investigation_claim",
            version: "0.1.0",
            claimId: "claim-missing-artifact",
            claimType: "source_identity",
            statement: "A missing artifact supports this claim.",
            status: "support",
            evidenceArtifactIds: ["missing-artifact"],
            assumptions: [],
            limitations: []
          }
        ]
      })
    ).toThrow("unknown diagnostic artifact");
  });

  it("rejects package inputs outside the canonical schema shape", () => {
    expect(() =>
      buildInvestigationPackage({
        packageId: "",
        title: "",
        target: {
          kind: "openplazma.investigation_target",
          version: "0.1.0",
          targetId: "bad-package-target",
          targetKind: "unknown",
          label: "Bad package target",
          description: "Bad package target.",
          candidateEnergySources: ["unknown"],
          limitations: ["Bad package fixture."]
        },
        questions: [],
        limitations: []
      })
    ).toThrow("packageId");
  });

  it("rejects invalid investigation session initialization contracts", () => {
    const claim = {
      kind: "openplazma.investigation_claim" as const,
      version: "0.1.0" as const,
      claimId: "claim-eye",
      claimType: "source_identity" as const,
      statement: "The eye report is evidence.",
      status: "inconclusive" as const,
      evidenceArtifactIds: ["eye-report"],
      assumptions: [],
      limitations: []
    };
    const pack = buildInvestigationPackage({
      packageId: "session-contract-test",
      title: "Session contract test",
      target: {
        kind: "openplazma.investigation_target",
        version: "0.1.0",
        targetId: "session-contract-target",
        targetKind: "unknown",
        label: "Session contract target",
        description: "Session contract target.",
        candidateEnergySources: ["unknown"],
        limitations: ["Session fixture."]
      },
      questions: [
        {
          questionId: "q-source",
          questionKind: "energy_source_classification",
          text: "What source is supported?"
        }
      ],
      artifacts: [humanEyeArtifact()],
      claims: [claim]
    });

    expect(() =>
      createInvestigationSession({
        sessionId: "",
        package: pack,
        createdAt: "2026-06-13T00:00:00.000Z"
      })
    ).toThrow("sessionId");

    expect(() =>
      createInvestigationSession({
        sessionId: "session-reported-without-report",
        package: pack,
        status: "reported",
        createdAt: "2026-06-13T00:00:00.000Z"
      })
    ).toThrow("reported");

    expect(() =>
      createInvestigationSession({
        sessionId: "session-bad-created-at",
        package: pack,
        createdAt: "today"
      })
    ).toThrow("createdAt");

    expect(() =>
      createInvestigationSession({
        sessionId: "session-impossible-created-at",
        package: pack,
        createdAt: "2026-02-31T00:00:00.000Z"
      })
    ).toThrow("createdAt");

    expect(() =>
      createInvestigationSession({
        sessionId: "session-bad-updated-at",
        package: pack,
        createdAt: "2026-06-13T00:00:00.000Z",
        updatedAt: "today"
      })
    ).toThrow("updatedAt");

    expect(() =>
      createInvestigationSession({
        sessionId: "session-bad-initial-report-id",
        package: pack,
        createdAt: "2026-06-13T00:00:00.000Z",
        reports: [
          {
            kind: "openplazma.investigation_report",
            version: "0.1.0",
            reportId: "",
            packageId: "session-contract-test",
            createdAt: "2026-06-13T00:00:00.000Z",
            claims: [claim],
            assumptions: [],
            limitations: ["Report ID must be non-empty."],
            nextObservations: []
          }
        ]
      })
    ).toThrow("reportId");

    expect(() =>
      createInvestigationSession({
        sessionId: "session-bad-initial-report",
        package: pack,
        createdAt: "2026-06-13T00:00:00.000Z",
        reports: [
          {
            kind: "openplazma.investigation_report",
            version: "0.1.0",
            reportId: "bad-initial-report",
            packageId: "session-contract-test",
            createdAt: "today",
            claims: [claim],
            assumptions: [],
            limitations: ["Report timestamp must be machine-readable."],
            nextObservations: []
          }
        ]
      })
    ).toThrow("createdAt");
  });

  it("rejects invalid session mutation timestamps", () => {
    const pack = buildInvestigationPackage({
      packageId: "mutation-time-test",
      title: "Mutation time test",
      target: {
        kind: "openplazma.investigation_target",
        version: "0.1.0",
        targetId: "mutation-time-target",
        targetKind: "unknown",
        label: "Mutation time target",
        description: "Mutation time target.",
        candidateEnergySources: ["unknown"],
        limitations: ["Mutation fixture."]
      },
      questions: [
        {
          questionId: "q-source",
          questionKind: "energy_source_classification",
          text: "What source is supported?"
        }
      ],
      artifacts: [humanEyeArtifact()]
    });
    const session = createInvestigationSession({
      sessionId: "session-mutation-time",
      package: pack,
      createdAt: "2026-06-13T00:00:00.000Z"
    });

    expect(() =>
      addDiagnosticArtifact(
        session,
        {
          ...humanEyeArtifact(),
          artifactId: "second-eye-report",
          label: "Second human visual report"
        },
        "today"
      )
    ).toThrow("updatedAt");

    expect(() =>
      addInvestigationClaim(
        session,
        {
          kind: "openplazma.investigation_claim",
          version: "0.1.0",
          claimId: "claim-eye-bad-time",
          claimType: "source_identity",
          statement: "The eye report is evidence.",
          status: "inconclusive",
          evidenceArtifactIds: ["eye-report"],
          assumptions: [],
          limitations: []
        },
        "today"
      )
    ).toThrow("updatedAt");
  });

  it("rejects generated reports outside the canonical schema shape", () => {
    const claim = {
      kind: "openplazma.investigation_claim" as const,
      version: "0.1.0" as const,
      claimId: "claim-eye",
      claimType: "source_identity" as const,
      statement: "The eye report is evidence.",
      status: "inconclusive" as const,
      evidenceArtifactIds: ["eye-report"],
      assumptions: [],
      limitations: []
    };
    const pack = buildInvestigationPackage({
      packageId: "report-contract-test",
      title: "Report contract test",
      target: {
        kind: "openplazma.investigation_target",
        version: "0.1.0",
        targetId: "report-contract-target",
        targetKind: "unknown",
        label: "Report contract target",
        description: "Report contract target.",
        candidateEnergySources: ["unknown"],
        limitations: ["Report fixture."]
      },
      questions: [
        {
          questionId: "q-source",
          questionKind: "energy_source_classification",
          text: "What source is supported?"
        }
      ],
      artifacts: [humanEyeArtifact()],
      claims: [claim]
    });
    const session = createInvestigationSession({
      sessionId: "session-report-contract",
      package: pack,
      createdAt: "2026-06-13T00:00:00.000Z"
    });

    expect(() => createInvestigationSessionReport(session, { reportId: "" })).toThrow("reportId");
    expect(() =>
      createInvestigationSessionReport(session, {
        createdAt: "2026-02-31T00:00:00.000Z"
      })
    ).toThrow("createdAt");
  });

  it("rejects session claims and reports that reference the wrong evidence boundary", () => {
    const pack = buildInvestigationPackage({
      packageId: "boundary-test",
      title: "Boundary test",
      target: {
        kind: "openplazma.investigation_target",
        version: "0.1.0",
        targetId: "boundary-target",
        targetKind: "unknown",
        label: "Boundary target",
        description: "Boundary target.",
        candidateEnergySources: ["unknown"],
        limitations: ["Boundary fixture."]
      },
      questions: [
        {
          questionId: "q-source",
          questionKind: "energy_source_classification",
          text: "What source is supported?"
        }
      ],
      artifacts: [humanEyeArtifact()]
    });
    const session = createInvestigationSession({
      sessionId: "session-boundary",
      package: pack,
      createdAt: "2026-06-13T00:00:00.000Z"
    });

    expect(() =>
      addInvestigationClaim(session, {
        kind: "openplazma.investigation_claim",
        version: "0.1.0",
        claimId: "claim-missing-artifact",
        claimType: "source_identity",
        statement: "A missing artifact supports this claim.",
        status: "support",
        evidenceArtifactIds: ["missing-artifact"],
        assumptions: [],
        limitations: []
      })
    ).toThrow("unknown diagnostic artifact");

    expect(() =>
      recordInvestigationReport(session, {
        kind: "openplazma.investigation_report",
        version: "0.1.0",
        reportId: "empty-claims-report",
        packageId: "boundary-test",
        createdAt: "2026-06-13T00:00:00.000Z",
        claims: [],
        assumptions: [],
        limitations: ["Reports need at least one claim."],
        nextObservations: []
      })
    ).toThrow("requires at least one claim");

    expect(() =>
      recordInvestigationReport(session, {
        kind: "openplazma.investigation_report",
        version: "0.1.0",
        reportId: "bad-time-report",
        packageId: "boundary-test",
        createdAt: "today",
        claims: [
          {
            kind: "openplazma.investigation_claim",
            version: "0.1.0",
            claimId: "claim-eye-bad-time",
            claimType: "source_identity",
            statement: "The eye report is evidence.",
            status: "inconclusive",
            evidenceArtifactIds: ["eye-report"],
            assumptions: [],
            limitations: []
          }
        ],
        assumptions: [],
        limitations: ["Report timestamp must be machine-readable."],
        nextObservations: []
      })
    ).toThrow("createdAt");

    expect(() =>
      recordInvestigationReport(session, {
        kind: "openplazma.investigation_report",
        version: "0.1.0",
        reportId: "wrong-report",
        packageId: "other-package",
        createdAt: "2026-06-13T00:00:00.000Z",
        claims: [
          {
            kind: "openplazma.investigation_claim",
            version: "0.1.0",
            claimId: "claim-eye",
            claimType: "source_identity",
            statement: "The eye report is evidence.",
            status: "inconclusive",
            evidenceArtifactIds: ["eye-report"],
            assumptions: [],
            limitations: []
          }
        ],
        assumptions: [],
        limitations: ["Wrong package boundary."],
        nextObservations: []
      })
    ).toThrow("packageId");

    expect(() =>
      recordInvestigationReport(session, {
        kind: "openplazma.investigation_report",
        version: "0.1.0",
        reportId: "missing-artifact-report",
        packageId: "boundary-test",
        createdAt: "2026-06-13T00:00:00.000Z",
        claims: [
          {
            kind: "openplazma.investigation_claim",
            version: "0.1.0",
            claimId: "claim-missing-report-artifact",
            claimType: "source_identity",
            statement: "The report references evidence outside the package.",
            status: "support",
            evidenceArtifactIds: ["missing-artifact"],
            evidenceReadoutIds: ["missing-readout"],
            method: "boundary_review",
            assumptions: [],
            limitations: [],
            alternatives: ["unknown source"]
          }
        ],
        assumptions: [],
        limitations: ["Wrong evidence boundary."],
        nextObservations: []
      })
    ).toThrow("unknown diagnostic artifact");
  });
});

describe("sawtooth / threshold / island helpers", () => {
  it("detects periodic sawtooth crashes and their frequency", () => {
    const series = { ...dalphaSignal(0.004, 12, 1e-4), signalId: "sxr-core", label: "Central SXR" };
    const crashes = detectPeriodicCrashes(series, { thresholdSigma: 1.5, minSpacingSec: 0.002 });
    expect(crashes.length).toBe(12);
    const stats = crashStats(crashes);
    expect(Math.abs(stats.frequencyHz - 250)).toBeLessThan(25); // 1 / 0.004 s
    expect(stats.regularity).toBeGreaterThan(0.9);
  });

  it("finds the first threshold crossing of a rising signal", () => {
    const time = Array.from({ length: 11 }, (_, i) => Number((i * 0.01).toFixed(3)));
    const values = time.map((_, i) => i / 10); // 0 .. 1.0
    const series: SignalSeries = {
      kind: "openplazma.signal_series",
      version: "0.1.0",
      signalId: "f-rad",
      label: "Radiated fraction",
      quantity: "fraction",
      unit: "",
      timeUnit: "s",
      time,
      values
    };
    const crossing = detectThresholdCrossing(series, 0.8);
    expect(crossing.crossed).toBe(true);
    expect(crossing.time).toBeCloseTo(0.08, 5);
  });

  it("scales island width as sqrt of amplitude", () => {
    expect(estimateNtmIslandWidth(0)).toBe(0);
    expect(estimateNtmIslandWidth(4, 0.03)).toBeCloseTo(0.06, 6);
  });
});
