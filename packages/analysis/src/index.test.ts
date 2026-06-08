import type { DiagnosticArray, RotationTrackPoint, SignalSeries } from "@openplazma/core";
import { describe, expect, it } from "vitest";
import {
  buildInferenceFromArray,
  detectModeLocking,
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
