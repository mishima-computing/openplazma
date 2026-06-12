import type { DiagnosticArray, RotationTrackPoint, SignalSeries } from "@openplazma/core";
import { describe, expect, it } from "vitest";
import {
  analyzeElms,
  analyzeTemporalFrequency,
  buildElectromagneticCarrierAnalysis,
  buildInferenceFromArray,
  crashStats,
  detectElmCrashes,
  detectModeLocking,
  detectPeriodicCrashes,
  detectThresholdCrossing,
  estimateNtmIslandWidth,
  estimatePoloidalModeNumber,
  estimateToroidalModeNumber,
  forwardTearingModeSignals,
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
