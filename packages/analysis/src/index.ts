import type {
  DiagnosticArray,
  DiagnosticArtifact,
  DiagnosticChannel,
  ElmAnalysis,
  ElmClassification,
  ElmCrash,
  EvidenceLink,
  FrequencyAnalysis,
  FrequencyAnalysisMethod,
  FrequencyDomain,
  FusionConditionAssessment,
  FusionConditionParameter,
  InvestigationClaim,
  InvestigationPackage,
  InvestigationQuestion,
  InvestigationReport,
  InvestigationSession,
  InvestigationSessionStatus,
  InvestigationTarget,
  Inference,
  MeasuredObservable,
  ModeNumberEstimate,
  ObservationStatement,
  PhenomenonEvent,
  RotationTrackPoint,
  SignalSeries,
  StudyRecord,
  TearingModeHypothesis
} from "@openplazma/core";
import {
  parseInvestigationPackage,
  parseInvestigationReport,
  parseInvestigationSession
} from "@openplazma/schema";

/**
 * In-process forward/inverse analysis for magnetic MHD mode diagnostics.
 *
 * Everything here is analytic and read-only: the forward model is a closed-form
 * tearing-mode signature, the inverse recovers mode numbers and rotation from a
 * probe array by phase fitting. No facility control, no live telemetry, no solver.
 */

const TWO_PI = Math.PI * 2;

// ---------------------------------------------------------------------------
// Math helpers
// ---------------------------------------------------------------------------

/** Unwrap a sequence of phases (radians) so successive jumps stay within +/-pi. */
export function unwrapPhase(phases: number[]): number[] {
  const out: number[] = [];
  let offset = 0;
  let prev = 0;
  phases.forEach((phase, index) => {
    if (index === 0) {
      prev = phase;
      out.push(phase);
      return;
    }
    let delta = phase + offset - prev;
    while (delta > Math.PI) {
      offset -= TWO_PI;
      delta -= TWO_PI;
    }
    while (delta < -Math.PI) {
      offset += TWO_PI;
      delta += TWO_PI;
    }
    const value = phase + offset;
    out.push(value);
    prev = value;
  });
  return out;
}

export interface PhaseAmplitude {
  amplitude: number;
  /** Phase in the cos(2*pi*f*t + phase) convention, radians. */
  phase: number;
}

/**
 * Single-frequency correlation (one DFT bin) of an evenly-sampled window.
 * For a signal A*cos(2*pi*f*t + phi) returns amplitude ~A and phase ~phi.
 */
export function goertzelPhaseAmplitude(values: number[], dt: number, freqHz: number): PhaseAmplitude {
  const n = values.length;
  if (n === 0 || dt <= 0) {
    return { amplitude: 0, phase: 0 };
  }
  let cosSum = 0;
  let sinSum = 0;
  for (let i = 0; i < n; i += 1) {
    const v = values[i] ?? 0;
    const angle = TWO_PI * freqHz * (i * dt);
    cosSum += v * Math.cos(angle);
    sinSum += v * Math.sin(angle);
  }
  const amplitude = (2 / n) * Math.hypot(cosSum, sinSum);
  // signal = A cos(wt + phi) => cosSum ~ (N/2)A cos phi, sinSum ~ -(N/2)A sin phi
  const phase = Math.atan2(-sinSum, cosSum);
  return { amplitude, phase };
}

export interface LinearFit {
  slope: number;
  intercept: number;
  /** Coefficient of determination, 0..1. */
  r2: number;
}

export function linearFit(x: number[], y: number[]): LinearFit {
  const n = Math.min(x.length, y.length);
  if (n < 2) {
    return { slope: 0, intercept: y[0] ?? 0, r2: 0 };
  }
  let sx = 0;
  let sy = 0;
  for (let i = 0; i < n; i += 1) {
    sx += x[i] ?? 0;
    sy += y[i] ?? 0;
  }
  const mx = sx / n;
  const my = sy / n;
  let sxx = 0;
  let sxy = 0;
  let syy = 0;
  for (let i = 0; i < n; i += 1) {
    const dx = (x[i] ?? 0) - mx;
    const dy = (y[i] ?? 0) - my;
    sxx += dx * dx;
    sxy += dx * dy;
    syy += dy * dy;
  }
  const slope = sxx === 0 ? 0 : sxy / sxx;
  const intercept = my - slope * mx;
  const r2 = sxx === 0 || syy === 0 ? 0 : (sxy * sxy) / (sxx * syy);
  return { slope, intercept, r2 };
}

// ---------------------------------------------------------------------------
// Sampling helpers
// ---------------------------------------------------------------------------

function inferDt(time: number[]): number {
  if (time.length < 2) {
    return 0;
  }
  const first = time[0] ?? 0;
  const last = time[time.length - 1] ?? 0;
  return (last - first) / (time.length - 1);
}

function windowIndices(time: number[], window: [number, number]): [number, number] {
  let start = 0;
  let end = time.length;
  for (let i = 0; i < time.length; i += 1) {
    if ((time[i] ?? 0) >= window[0]) {
      start = i;
      break;
    }
  }
  for (let i = time.length - 1; i >= 0; i -= 1) {
    if ((time[i] ?? 0) <= window[1]) {
      end = i + 1;
      break;
    }
  }
  return [start, Math.max(start + 1, end)];
}

function signalById(signals: SignalSeries[]): Map<string, SignalSeries> {
  return new Map(signals.map((signal) => [signal.signalId, signal]));
}

/** Scan a coarse frequency grid and refine to find the dominant component. */
export function dominantFrequency(values: number[], dt: number, maxFreqHz?: number): number {
  if (values.length < 4 || dt <= 0) {
    return 0;
  }
  const nyquist = 1 / (2 * dt);
  const top = Math.min(maxFreqHz ?? nyquist, nyquist);
  const minFreq = 1 / (values.length * dt);
  const steps = 256;
  let bestFreq = minFreq;
  let bestAmp = -1;
  for (let s = 0; s <= steps; s += 1) {
    const freq = minFreq + ((top - minFreq) * s) / steps;
    const { amplitude } = goertzelPhaseAmplitude(values, dt, freq);
    if (amplitude > bestAmp) {
      bestAmp = amplitude;
      bestFreq = freq;
    }
  }
  // local refinement around the best coarse bin
  const span = (top - minFreq) / steps;
  let lo = Math.max(minFreq, bestFreq - span);
  let hi = Math.min(top, bestFreq + span);
  for (let iter = 0; iter < 20; iter += 1) {
    const mid1 = lo + (hi - lo) / 3;
    const mid2 = hi - (hi - lo) / 3;
    const a1 = goertzelPhaseAmplitude(values, dt, mid1).amplitude;
    const a2 = goertzelPhaseAmplitude(values, dt, mid2).amplitude;
    if (a1 >= a2) {
      hi = mid2;
    } else {
      lo = mid1;
    }
  }
  return (lo + hi) / 2;
}

// ---------------------------------------------------------------------------
// Forward model
// ---------------------------------------------------------------------------

/**
 * Forward observation model: the magnetic-fluctuation signature a rotating
 * (m, n) tearing mode would imprint on each probe in the array, as synthetic
 * derived signals. b ~ A cos(m*theta - n*phi - 2*pi*f*t + phase0).
 */
export function forwardTearingModeSignals(
  array: DiagnosticArray,
  hypothesis: TearingModeHypothesis,
  time: number[]
): SignalSeries[] {
  const { poloidalModeNumber: m, toroidalModeNumber: n, amplitude, rotationFreqHz, phaseRad } = hypothesis;
  return array.channels.map((channel) => {
    const theta = channel.geometry.poloidalAngleRad;
    const phi = channel.geometry.toroidalAngleRad;
    const spatial = m * theta - n * phi + phaseRad;
    const values = time.map((t) => amplitude * Math.cos(spatial - TWO_PI * rotationFreqHz * t));
    const series: SignalSeries = {
      kind: "openplazma.signal_series",
      version: "0.1.0",
      signalId: `${channel.channelId}-forward`,
      label: `${channel.label} (forward ${m}/${n})`,
      quantity: "magnetic_fluctuation",
      unit: "a.u.",
      timeUnit: "s",
      time: [...time],
      values
    };
    return series;
  });
}

// ---------------------------------------------------------------------------
// Inverse: mode-number estimation
// ---------------------------------------------------------------------------

function estimateModeNumber(
  channels: DiagnosticChannel[],
  signals: SignalSeries[],
  window: [number, number],
  axis: "toroidal" | "poloidal"
): ModeNumberEstimate {
  const byId = signalById(signals);
  const samples: Array<{ angle: number; phase: number }> = [];
  let dt = 0;
  let refFreq = 0;

  // Determine a shared reference frequency from the first usable channel.
  for (const channel of channels) {
    const series = byId.get(channel.signalId);
    if (!series) {
      continue;
    }
    const [start, end] = windowIndices(series.time, window);
    const slice = series.values.slice(start, end);
    dt = inferDt(series.time);
    refFreq = dominantFrequency(slice, dt);
    if (refFreq > 0) {
      break;
    }
  }

  for (const channel of channels) {
    const series = byId.get(channel.signalId);
    if (!series) {
      continue;
    }
    const [start, end] = windowIndices(series.time, window);
    const slice = series.values.slice(start, end);
    const { phase } = goertzelPhaseAmplitude(slice, inferDt(series.time), refFreq);
    const angle =
      axis === "toroidal" ? channel.geometry.toroidalAngleRad : channel.geometry.poloidalAngleRad;
    samples.push({ angle, phase });
  }

  samples.sort((a, b) => a.angle - b.angle);
  const angles = samples.map((s) => s.angle);
  const phases = unwrapPhase(samples.map((s) => s.phase));
  const fit = linearFit(angles, phases);

  // measured phase ~ +n*phi (toroidal) or -m*theta (poloidal); see forward model.
  const raw = axis === "toroidal" ? fit.slope : -fit.slope;
  const modeNumber = Math.round(raw);
  const confidence = Math.max(0, Math.min(1, fit.r2));

  if (axis === "toroidal") {
    return { toroidalModeNumber: modeNumber, confidence, method: "phase_fit_toroidal" };
  }
  return { toroidalModeNumber: 0, poloidalModeNumber: modeNumber, confidence, method: "phase_fit_poloidal" };
}

export function estimateToroidalModeNumber(
  channels: DiagnosticChannel[],
  signals: SignalSeries[],
  window: [number, number]
): ModeNumberEstimate {
  return estimateModeNumber(channels, signals, window, "toroidal");
}

export function estimatePoloidalModeNumber(
  channels: DiagnosticChannel[],
  signals: SignalSeries[],
  window: [number, number]
): ModeNumberEstimate {
  return estimateModeNumber(channels, signals, window, "poloidal");
}

// ---------------------------------------------------------------------------
// Inverse: rotation tracking + locking
// ---------------------------------------------------------------------------

export interface RotationTrackOptions {
  /** Sliding window length in samples. */
  windowSamples?: number;
  /** Step between window centres, in samples. */
  stepSamples?: number;
}

export function trackRotationFrequency(
  channels: DiagnosticChannel[],
  signals: SignalSeries[],
  options: RotationTrackOptions = {}
): RotationTrackPoint[] {
  const byId = signalById(signals);
  const ref = channels.map((c) => byId.get(c.signalId)).find((s): s is SignalSeries => s !== undefined);
  if (!ref) {
    return [];
  }
  const dt = inferDt(ref.time);
  const n = ref.values.length;
  const windowSamples = Math.max(8, options.windowSamples ?? Math.floor(n / 12));
  const stepSamples = Math.max(1, options.stepSamples ?? Math.floor(windowSamples / 2));
  const track: RotationTrackPoint[] = [];
  for (let start = 0; start + windowSamples <= n; start += stepSamples) {
    const slice = ref.values.slice(start, start + windowSamples);
    const freq = dominantFrequency(slice, dt);
    const { amplitude } = goertzelPhaseAmplitude(slice, dt, freq);
    const centreIndex = start + Math.floor(windowSamples / 2);
    track.push({ time: ref.time[centreIndex] ?? 0, rotationFreqHz: freq, amplitude });
  }
  return track;
}

export interface LockingOptions {
  /** Rotation below this frequency (Hz) is treated as effectively locked. */
  lockFreqThresholdHz?: number;
  /** Locking only counts when amplitude is at least this fraction of the peak. */
  minAmplitudeFraction?: number;
}

export interface LockingResult {
  locked: boolean;
  lockTimeRange?: [number, number] | undefined;
}

export function detectModeLocking(track: RotationTrackPoint[], options: LockingOptions = {}): LockingResult {
  if (track.length === 0) {
    return { locked: false };
  }
  const peakAmp = track.reduce((max, p) => Math.max(max, p.amplitude), 0);
  const ampFloor = peakAmp * (options.minAmplitudeFraction ?? 0.3);
  const maxFreq = track.reduce((max, p) => Math.max(max, p.rotationFreqHz), 0);
  const threshold = options.lockFreqThresholdHz ?? Math.max(50, maxFreq * 0.1);

  let lockStart: number | undefined;
  let lockEnd: number | undefined;
  for (const point of track) {
    if (point.rotationFreqHz <= threshold && point.amplitude >= ampFloor) {
      if (lockStart === undefined) {
        lockStart = point.time;
      }
      lockEnd = point.time;
    }
  }
  if (lockStart === undefined || lockEnd === undefined) {
    return { locked: false };
  }
  return { locked: true, lockTimeRange: [lockStart, lockEnd] };
}

// ---------------------------------------------------------------------------
// Orchestration + evidence
// ---------------------------------------------------------------------------

export interface BuildInferenceOptions {
  inferenceId?: string;
  label?: string;
  /** Window for mode-number estimation; defaults to the early (rotating) phase. */
  modeWindow?: [number, number];
  rotation?: RotationTrackOptions;
  locking?: LockingOptions;
  /**
   * If set, estimate a magnetic-island width from the peak fluctuation
   * amplitude using this calibration gain (metres per sqrt of a.u.).
   */
  islandWidthGain?: number;
}

export function buildInferenceFromArray(
  array: DiagnosticArray,
  signals: SignalSeries[],
  options: BuildInferenceOptions = {}
): Inference {
  const byId = signalById(signals);
  const ref = array.channels
    .map((c) => byId.get(c.signalId))
    .find((s): s is SignalSeries => s !== undefined);
  const fullStart = ref?.time[0] ?? 0;
  const fullEnd = ref?.time[ref.time.length - 1] ?? 1;
  const modeWindow = options.modeWindow ?? [fullStart, fullStart + (fullEnd - fullStart) * 0.4];

  const baseEstimate = estimateToroidalModeNumber(array.channels, signals, modeWindow);
  const rotationTrack = trackRotationFrequency(array.channels, signals, options.rotation);
  const locking = detectModeLocking(rotationTrack, options.locking);
  const nyquistN = Math.floor(array.channels.length / 2);

  const modeEstimate =
    options.islandWidthGain === undefined
      ? baseEstimate
      : {
          ...baseEstimate,
          islandWidthM: estimateNtmIslandWidth(
            rotationTrack.reduce((max, p) => Math.max(max, p.amplitude), 0),
            options.islandWidthGain
          )
        };
  const inferenceId = options.inferenceId ?? `inf-${array.arrayId}`;

  return {
    kind: "openplazma.inference",
    version: "0.1.0",
    inferenceId,
    label: options.label ?? `Phase-fit mode estimate for ${array.label}`,
    method: "magnetic_mode_phase_fit",
    sourceArrayId: array.arrayId,
    evidenceReadoutIds: [`${inferenceId}-phase-fit-readout`],
    modeEstimate,
    rotationTrack,
    lockingDetected: locking.locked,
    lockTimeRange: locking.lockTimeRange,
    assumptions: [
      "Single dominant rotating mode within the analysis window.",
      "Probe phases are coherent across the array."
    ],
    limitations: [
      `Toroidal mode number is only resolved up to |n| <= ${nyquistN} (Nyquist limit for ${array.channels.length} probes); higher n aliases to its principal value.`,
      "Rotation frequency is estimated per window and smears fast transients."
    ],
    alternatives: [
      "Higher toroidal mode numbers can alias onto the principal value.",
      "Multiple simultaneous modes can bias a single-mode phase fit."
    ]
  };
}

/**
 * Compare a hypothesised mode against the inference and recorded events,
 * emitting support/contradict/inconclusive evidence links.
 */
export function evaluateEvidence(
  hypothesis: TearingModeHypothesis,
  inference: Inference,
  events: PhenomenonEvent[]
): EvidenceLink[] {
  const links: EvidenceLink[] = [];

  const modeMatch = inference.modeEstimate.toroidalModeNumber === hypothesis.toroidalModeNumber;
  links.push({
    kind: "openplazma.evidence_link",
    version: "0.1.0",
    verdict: modeMatch ? "support" : "contradict",
    arrayId: inference.sourceArrayId,
    readoutId: inference.evidenceReadoutIds[0],
    inferenceId: inference.inferenceId,
    method: inference.method,
    timeRange: hypothesis.timeRange,
    rationale: modeMatch
      ? `Phase fit recovers toroidal mode number n=${inference.modeEstimate.toroidalModeNumber}, matching the hypothesis (confidence ${inference.modeEstimate.confidence.toFixed(2)}).`
      : `Phase fit recovers n=${inference.modeEstimate.toroidalModeNumber}, not the hypothesised n=${hypothesis.toroidalModeNumber}.`,
    assumptions: inference.assumptions,
    limitations: inference.limitations,
    alternatives: inference.alternatives
  });

  const quench = events.find((e) => e.phenomenon === "current_quench" || e.phenomenon === "disruption");
  if (inference.lockingDetected && inference.lockTimeRange && quench) {
    const locksBeforeQuench = inference.lockTimeRange[1] <= quench.timeRange[1];
    links.push({
      kind: "openplazma.evidence_link",
      version: "0.1.0",
      verdict: locksBeforeQuench ? "support" : "inconclusive",
      arrayId: inference.sourceArrayId,
      readoutId: inference.evidenceReadoutIds[0],
      inferenceId: inference.inferenceId,
      method: "rotation_track_threshold",
      timeRange: inference.lockTimeRange,
      rationale: locksBeforeQuench
        ? "Mode rotation collapses (locks) before the current quench, consistent with a locked-mode disruption."
        : "Locking and quench timing overlap ambiguously.",
      assumptions: inference.assumptions,
      limitations: inference.limitations,
      alternatives: ["A timing overlap can also reflect unrelated transients or threshold selection."]
    });
  } else {
    links.push({
      kind: "openplazma.evidence_link",
      version: "0.1.0",
      verdict: "inconclusive",
      arrayId: inference.sourceArrayId,
      readoutId: inference.evidenceReadoutIds[0],
      inferenceId: inference.inferenceId,
      method: "rotation_track_threshold",
      timeRange: hypothesis.timeRange,
      rationale: "No clear locking-then-quench sequence was detected in the available signals.",
      assumptions: inference.assumptions,
      limitations: inference.limitations,
      alternatives: ["A mode may be present without a resolved locking-then-quench sequence."]
    });
  }

  return links;
}

// ---------------------------------------------------------------------------
// Edge-localised modes (ELMs)
// ---------------------------------------------------------------------------

function mean(values: number[]): number {
  if (values.length === 0) {
    return 0;
  }
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

function stddev(values: number[]): number {
  if (values.length < 2) {
    return 0;
  }
  const m = mean(values);
  const variance = values.reduce((sum, v) => sum + (v - m) * (v - m), 0) / values.length;
  return Math.sqrt(variance);
}

// ---------------------------------------------------------------------------
// Investigation frequency analysis
// ---------------------------------------------------------------------------

const SPEED_OF_LIGHT_M_PER_S = 299_792_458;

export interface TemporalFrequencyAnalysisOptions {
  analysisId?: string;
  domain: FrequencyDomain;
  method?: Extract<FrequencyAnalysisMethod, "fft" | "stft" | "periodogram" | "lomb_scargle" | "unknown">;
  sourceQuantity?: string;
  bandId?: string;
  bandLabel?: string;
  peakId?: string;
  lowerFrequencyHz?: number;
  upperFrequencyHz?: number;
  maxFrequencyHz?: number;
  description?: string;
  assumptions?: string[];
  limitations?: string[];
}

function centered(values: number[]): number[] {
  const baseline = mean(values);
  return values.map((value) => value - baseline);
}

function residualStddev(values: number[], dt: number, freqHz: number, amplitude: number, phase: number): number {
  if (values.length === 0 || dt <= 0 || freqHz <= 0) {
    return 0;
  }
  const residuals = values.map((value, index) => {
    const fitted = amplitude * Math.cos(TWO_PI * freqHz * index * dt + phase);
    return value - fitted;
  });
  return stddev(residuals);
}

export function analyzeTemporalFrequency(
  series: SignalSeries,
  options: TemporalFrequencyAnalysisOptions
): FrequencyAnalysis {
  const dt = inferDt(series.time);
  const sampleRateHz = dt > 0 ? 1 / dt : undefined;
  const durationSeconds =
    series.time.length > 1
      ? (series.time[series.time.length - 1] ?? 0) - (series.time[0] ?? 0)
      : undefined;
  const frequencyResolutionHz = durationSeconds && durationSeconds > 0 ? 1 / durationSeconds : undefined;
  const values = centered(series.values);
  const nyquistHz = sampleRateHz !== undefined ? sampleRateHz / 2 : undefined;
  const upperFrequencyHz = Math.min(
    options.upperFrequencyHz ?? options.maxFrequencyHz ?? nyquistHz ?? Number.POSITIVE_INFINITY,
    nyquistHz ?? Number.POSITIVE_INFINITY
  );
  const peakFrequencyHz = dominantFrequency(values, dt, Number.isFinite(upperFrequencyHz) ? upperFrequencyHz : undefined);
  const { amplitude, phase } = goertzelPhaseAmplitude(values, dt, peakFrequencyHz);
  const noise = residualStddev(values, dt, peakFrequencyHz, amplitude, phase);
  const signalToNoiseRatio = noise > 0 ? amplitude / noise : undefined;

  return {
    analysisId: options.analysisId ?? `${series.signalId}-frequency`,
    domain: options.domain,
    method: options.method ?? "fft",
    sourceQuantity: options.sourceQuantity ?? series.quantity,
    sampleRateHz,
    windowSeconds: durationSeconds,
    frequencyResolutionHz,
    bands: [
      {
        bandId: options.bandId ?? `${series.signalId}-analysis-band`,
        domain: options.domain,
        label: options.bandLabel ?? `${series.label} analysis band`,
        lowerFrequencyHz: options.lowerFrequencyHz ?? frequencyResolutionHz,
        upperFrequencyHz: Number.isFinite(upperFrequencyHz) ? upperFrequencyHz : undefined,
        quantity: `${series.quantity} modulation`,
        unit: series.unit,
        description: "Temporal frequency band examined for this signal.",
        limitations: ["The band constrains modulation, not source identity."]
      }
    ],
    peaks:
      peakFrequencyHz > 0
        ? [
            {
              peakId: options.peakId ?? `${series.signalId}-dominant-peak`,
              frequencyHz: peakFrequencyHz,
              amplitude,
              phaseRadians: phase,
              signalToNoiseRatio,
              interpretation: "Dominant temporal modulation candidate.",
              limitations: ["A frequency peak can be source behavior, coupling, motion, aliasing, or instrument response."]
            }
          ]
        : [],
    description: options.description ?? `Frequency decomposition of ${series.label}.`,
    assumptions: options.assumptions ?? ["Samples are treated as evenly spaced."],
    limitations: options.limitations ?? ["Frequency analysis does not prove plasma, fusion, or source identity by itself."]
  };
}

export function wavelengthMetersToFrequencyHz(wavelengthMeters: number): number {
  if (wavelengthMeters <= 0 || !Number.isFinite(wavelengthMeters)) {
    throw new Error("wavelengthMeters must be a positive finite number");
  }
  return SPEED_OF_LIGHT_M_PER_S / wavelengthMeters;
}

export interface ElectromagneticCarrierAnalysisOptions {
  analysisId: string;
  sourceQuantity: string;
  lowerWavelengthMeters: number;
  upperWavelengthMeters: number;
  bandId: string;
  label: string;
  peakWavelengthMeters?: number;
  description: string;
  assumptions?: string[];
  limitations?: string[];
}

export function buildElectromagneticCarrierAnalysis(
  options: ElectromagneticCarrierAnalysisOptions
): FrequencyAnalysis {
  const f1 = wavelengthMetersToFrequencyHz(options.lowerWavelengthMeters);
  const f2 = wavelengthMetersToFrequencyHz(options.upperWavelengthMeters);
  const lowerFrequencyHz = Math.min(f1, f2);
  const upperFrequencyHz = Math.max(f1, f2);

  return {
    analysisId: options.analysisId,
    domain: "electromagnetic_carrier",
    method: "spectral_line_fit",
    sourceQuantity: options.sourceQuantity,
    bands: [
      {
        bandId: options.bandId,
        domain: "electromagnetic_carrier",
        label: options.label,
        lowerFrequencyHz,
        upperFrequencyHz,
        quantity: "electromagnetic carrier frequency",
        unit: "Hz",
        description: options.description,
        limitations: options.limitations ?? ["Carrier frequency constrains the observed band, not source identity."]
      }
    ],
    peaks:
      options.peakWavelengthMeters !== undefined
        ? [
            {
              peakId: `${options.bandId}-peak`,
              frequencyHz: wavelengthMetersToFrequencyHz(options.peakWavelengthMeters),
              interpretation: "Candidate carrier-frequency feature.",
              limitations: ["A carrier peak is spectral evidence, not a fusion-product claim by itself."]
            }
          ]
        : [],
    description: options.description,
    assumptions: options.assumptions ?? ["Wavelength-to-frequency conversion uses vacuum light speed."],
    limitations: options.limitations ?? ["Carrier analysis must be combined with calibrated diagnostics before claims."]
  };
}

// ---------------------------------------------------------------------------
// Signal evidence bridge
// ---------------------------------------------------------------------------

export interface StudyRecordSignalEvidenceOptions {
  signalIds?: string[] | undefined;
  artifactIdPrefix?: string | undefined;
  readoutIdPrefix?: string | undefined;
  maxFrequencyHz?: number | undefined;
  domainByQuantity?: Partial<Record<string, FrequencyDomain>> | undefined;
}

export interface StudyRecordSignalEvidence {
  artifacts: DiagnosticArtifact[];
  observations: ObservationStatement[];
  frequencyAnalyses: FrequencyAnalysis[];
}

function safeIdSegment(value: string): string {
  const sanitized = value.replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "");
  return sanitized.length > 0 ? sanitized : "signal";
}

function inferFrequencyDomainForSignal(series: SignalSeries, options: StudyRecordSignalEvidenceOptions): FrequencyDomain {
  const explicit = options.domainByQuantity?.[series.quantity];
  if (explicit !== undefined) {
    return explicit;
  }
  if (series.quantity.includes("current")) {
    return "electric_variation";
  }
  if (series.quantity.includes("magnetic")) {
    return "magnetic_variation";
  }
  if (series.quantity.includes("acoustic") || series.quantity.includes("pressure")) {
    return "acoustic_modulation";
  }
  if (series.quantity.includes("gravity")) {
    return "gravity_variation";
  }
  return "intensity_modulation";
}

function diagnosticProvenanceFromStudyRecord(record: StudyRecord): DiagnosticArtifact["provenanceKind"] {
  switch (record.shot.source.kind) {
    case "measured":
    case "derived":
    case "synthetic":
      return record.shot.source.kind;
    default:
      return "unknown";
  }
}

export function buildStudyRecordSignalEvidence(
  record: StudyRecord,
  options: StudyRecordSignalEvidenceOptions = {}
): StudyRecordSignalEvidence {
  const selectedIds = options.signalIds === undefined ? undefined : new Set(options.signalIds);
  const provenanceKind = diagnosticProvenanceFromStudyRecord(record);
  const artifacts: DiagnosticArtifact[] = [];
  const observations: ObservationStatement[] = [];
  const frequencyAnalyses: FrequencyAnalysis[] = [];

  for (const series of record.signals) {
    if (selectedIds !== undefined && !selectedIds.has(series.signalId)) {
      continue;
    }
    const id = safeIdSegment(series.signalId);
    const artifactId = `${options.artifactIdPrefix ?? "signal"}-${id}`;
    const readoutId = `${options.readoutIdPrefix ?? "readout"}-${id}-dominant-frequency`;
    const analysis = analyzeTemporalFrequency(series, {
      analysisId: `${artifactId}-frequency`,
      domain: inferFrequencyDomainForSignal(series, options),
      ...(options.maxFrequencyHz !== undefined ? { maxFrequencyHz: options.maxFrequencyHz } : {})
    });
    frequencyAnalyses.push(analysis);

    const startTime = series.time[0] ?? 0;
    const endTime = series.time[series.time.length - 1] ?? startTime;
    const artifact: DiagnosticArtifact = {
      kind: "openplazma.diagnostic_artifact",
      version: "0.1.0",
      artifactId,
      artifactKind: "signal_series",
      label: series.label,
      provenanceKind,
      signalIds: [series.signalId],
      signalWindows: [
        {
          windowId: `${artifactId}-window`,
          signalId: series.signalId,
          role: "primary",
          timeRange: [startTime, endTime],
          sampleCount: series.values.length,
          description: `Analysis window for ${series.label}.`,
          limitations: ["Window bounds come from the stored signal timestamps."]
        }
      ],
      frequencyAnalyses: [analysis],
      source: {
        sourceKind: "derived_artifact",
        label: record.source.sourceLabel,
        signalIds: [series.signalId],
        ...(record.source.uri !== undefined ? { uri: record.source.uri } : {}),
        ...(record.source.sha256 !== undefined ? { sha256: record.source.sha256 } : {}),
        limitations: ["Derived from a StudyRecord signal; no live data fetch is performed."]
      },
      quantity: series.quantity,
      unit: series.unit,
      description: `Diagnostic artifact bridged from StudyRecord signal '${series.signalId}'.`,
      limitations: [
        "Signal-derived evidence is mediated by analysis choices.",
        "Frequency structure alone does not establish energy source or fusion status."
      ]
    };
    artifacts.push(artifact);

    const peak = analysis.peaks[0];
    const observation: ObservationStatement = {
      kind: "openplazma.observation_statement",
      version: "0.1.0",
      readoutId,
      artifactId,
      signalId: series.signalId,
      observable: "unknown",
      readoutKind: peak === undefined ? "summary_statistic" : "frequency_peak",
      method: analysis.method,
      ...(peak !== undefined
        ? {
            selector: `frequencyAnalyses[${analysis.analysisId}].peaks[${peak.peakId}]`,
            value: peak.frequencyHz,
            unit: "Hz"
          }
        : {}),
      status: peak === undefined ? "unknown" : "candidate",
      ...(analysis.frequencyResolutionHz !== undefined
        ? {
            uncertaintyEstimate: {
              value: analysis.frequencyResolutionHz,
              unit: "Hz",
              description: "Frequency-bin resolution from the bridged signal window.",
              limitations: ["Resolution does not include instrument response or timestamp uncertainty."]
            }
          }
        : {}),
      assumptions: ["Samples are treated as evenly spaced for the bridge analysis."],
      limitations: ["This readout is evidence for signal content, not direct source identity."],
      alternatives: ["instrument response", "aliasing", "noise", "source modulation"]
    };
    observations.push(observation);
  }

  return { artifacts, observations, frequencyAnalyses };
}

export function addSignalEvidenceToInvestigationPackage(
  pack: InvestigationPackage,
  evidence: StudyRecordSignalEvidence
): InvestigationPackage {
  const nextPackage: InvestigationPackage = {
    ...pack,
    artifacts: uniqueArtifacts([...pack.artifacts, ...evidence.artifacts]),
    observations: uniqueObservations([...(pack.observations ?? []), ...evidence.observations])
  };
  return parseInvestigationPackage(nextPackage);
}

// ---------------------------------------------------------------------------
// Mixed-signal diagnostic assessment
// ---------------------------------------------------------------------------

export type DiagnosticIdentifiability =
  | "source_identity_not_supported"
  | "source_identity_constrained"
  | "source_identity_candidate_only";

export interface DiagnosticArtifactAssessment {
  artifactId: string;
  instrumentLabel?: string | undefined;
  measuredObservables: MeasuredObservable[];
  calibrationStatus: "calibrated" | "estimated" | "uncalibrated" | "unknown" | "missing";
  unresolvedContributions: string[];
  noiseContributions: string[];
  missingObservables: MeasuredObservable[];
  identifiability: DiagnosticIdentifiability;
  summary: string;
  limitations: string[];
}

export interface InvestigationMeasurementAssessment {
  packageId: string;
  artifactAssessments: DiagnosticArtifactAssessment[];
  missingObservables: MeasuredObservable[];
  unresolvedArtifactIds: string[];
  summary: string;
  limitations: string[];
}

const noiseContributionKinds = new Set([
  "background",
  "instrument_noise",
  "aliasing_artifact",
  "motion_artifact",
  "reconstruction_artifact"
]);

function contributionLabel(contribution: NonNullable<DiagnosticArtifact["contributions"]>[number]): string {
  return `${contribution.contributionKind}:${contribution.status}`;
}

export function assessDiagnosticArtifact(
  artifact: DiagnosticArtifact,
  requiredObservables: MeasuredObservable[] = []
): DiagnosticArtifactAssessment {
  const measuredObservables = artifact.instrument?.observables ?? [];
  const calibration = artifact.instrument?.calibration;
  const calibrationStatus = calibration?.status ?? "missing";
  const contributions = artifact.contributions ?? [];
  const unresolvedContributions = contributions
    .filter((contribution) => contribution.status === "unresolved" || contribution.role === "candidate")
    .map(contributionLabel);
  const noiseContributions = contributions
    .filter(
      (contribution) =>
        contribution.role === "noise" ||
        contribution.role === "contaminant" ||
        noiseContributionKinds.has(contribution.contributionKind)
    )
    .map(contributionLabel);
  const missingObservables = requiredObservables.filter((observable) => !measuredObservables.includes(observable));
  const hasCalibrationGap =
    calibration === undefined ||
    calibration.status !== "calibrated" ||
    !calibration.responseKnown ||
    !calibration.correctionApplied;
  const identifiability: DiagnosticIdentifiability =
    missingObservables.length > 0 || calibration === undefined
      ? "source_identity_not_supported"
      : hasCalibrationGap || unresolvedContributions.length > 0 || noiseContributions.length > 0
        ? "source_identity_candidate_only"
        : "source_identity_constrained";

  return {
    artifactId: artifact.artifactId,
    instrumentLabel: artifact.instrument?.label,
    measuredObservables,
    calibrationStatus,
    unresolvedContributions,
    noiseContributions,
    missingObservables,
    identifiability,
    summary:
      identifiability === "source_identity_constrained"
        ? "The artifact can constrain a source claim but still needs cross-evidence."
        : "The artifact cannot identify the source by itself.",
    limitations: [
      ...artifact.limitations,
      ...(calibration?.limitations ?? ["No instrument calibration metadata is attached."]),
      ...(missingObservables.length > 0
        ? [`Missing required observables: ${missingObservables.join(", ")}.`]
        : []),
      ...(unresolvedContributions.length > 0
        ? [`Unresolved contributions remain: ${unresolvedContributions.join(", ")}.`]
        : [])
    ]
  };
}

export function assessInvestigationMeasurements(
  pack: InvestigationPackage,
  requiredObservables: MeasuredObservable[] = []
): InvestigationMeasurementAssessment {
  const artifactAssessments = pack.artifacts.map((artifact) =>
    assessDiagnosticArtifact(artifact, requiredObservables)
  );
  const observed = new Set(artifactAssessments.flatMap((assessment) => assessment.measuredObservables));
  const missingObservables = requiredObservables.filter((observable) => !observed.has(observable));
  const unresolvedArtifactIds = artifactAssessments
    .filter((assessment) => assessment.identifiability !== "source_identity_constrained")
    .map((assessment) => assessment.artifactId);

  return {
    packageId: pack.packageId,
    artifactAssessments,
    missingObservables,
    unresolvedArtifactIds,
    summary:
      unresolvedArtifactIds.length === 0
        ? "All supplied artifacts can constrain source claims, subject to package limitations."
        : "Some supplied artifacts cannot identify source claims without more diagnostics or calibration.",
    limitations: [
      ...pack.limitations,
      ...(missingObservables.length > 0
        ? [`Package is missing required observables: ${missingObservables.join(", ")}.`]
        : [])
    ]
  };
}

export type ConservativeFusionClaimDisposition =
  | "fusion_claim_supported"
  | "fusion_claim_contradicted"
  | "fusion_claim_not_supported"
  | "fusion_claim_unknown"
  | "fusion_claim_untested";

export interface ConservativeFusionClaimAssessmentOptions {
  claimId?: string | undefined;
  requiredObservables?: MeasuredObservable[] | undefined;
  method?: string | undefined;
}

export interface ConservativeFusionClaimAssessment {
  packageId: string;
  fusionAssessment: FusionConditionAssessment;
  claim: InvestigationClaim;
  disposition: ConservativeFusionClaimDisposition;
  missingObservables: MeasuredObservable[];
  missingRequiredConditions: FusionConditionParameter[];
  hasUnspecifiedRequiredConditions: boolean;
  supportingReadoutIds: string[];
  supportingArtifactIds: string[];
  nextObservations: string[];
  summary: string;
  limitations: string[];
}

const defaultFusionClaimObservables: MeasuredObservable[] = [
  "neutron_flux",
  "gamma_ray",
  "particle_flux",
  "temperature",
  "density"
];

const fusionProductObservables = new Set<MeasuredObservable>([
  "neutron_flux",
  "gamma_ray",
  "particle_flux",
  "neutrino_flux"
]);

function uniqueStrings(values: string[]): string[] {
  return [...new Set(values)];
}

function artifactHasCalibratedResponse(artifact: DiagnosticArtifact | undefined): boolean {
  const calibration = artifact?.instrument?.calibration;
  return (
    calibration !== undefined &&
    calibration.status === "calibrated" &&
    calibration.responseKnown &&
    calibration.correctionApplied &&
    calibration.response !== undefined
  );
}

function conditionIsResolved(condition: FusionConditionAssessment["observedOrInferredConditions"][number]): boolean {
  return (
    ["measured", "inferred", "bounded"].includes(condition.status) &&
    (condition.evidenceReadoutIds ?? []).length > 0 &&
    condition.method !== undefined
  );
}

export function assessConservativeFusionClaim(
  pack: InvestigationPackage,
  options: ConservativeFusionClaimAssessmentOptions = {}
): ConservativeFusionClaimAssessment {
  const parsed = parseInvestigationPackage(pack);
  const readouts = parsed.observations ?? [];
  const readoutById = new Map(readouts.map((readout) => [readout.readoutId, readout]));
  const artifactById = new Map(parsed.artifacts.map((artifact) => [artifact.artifactId, artifact]));
  const requiredObservables = options.requiredObservables ?? defaultFusionClaimObservables;
  const observedObservables = new Set<MeasuredObservable>([
    ...parsed.artifacts.flatMap((artifact) => artifact.instrument?.observables ?? []),
    ...readouts.map((readout) => readout.observable)
  ]);
  const missingObservables = requiredObservables.filter((observable) => !observedObservables.has(observable));
  const requiredConditions = parsed.fusionAssessment.requiredConditions.filter(
    (condition) => condition.logicalRole === "necessary"
  );
  const resolvedParameters = new Set(
    parsed.fusionAssessment.observedOrInferredConditions
      .filter(conditionIsResolved)
      .map((condition) => condition.parameter)
  );
  const missingRequiredConditions = requiredConditions
    .filter((condition) => !resolvedParameters.has(condition.parameter))
    .map((condition) => condition.parameter);
  const hasUnspecifiedRequiredConditions = requiredConditions.length === 0;
  const productReadouts = readouts.filter((readout) => fusionProductObservables.has(readout.observable));
  const calibratedProductReadouts = productReadouts.filter(
    (readout) => readout.status === "detected" && artifactHasCalibratedResponse(artifactById.get(readout.artifactId))
  );
  const conditionReadoutIds = parsed.fusionAssessment.observedOrInferredConditions.flatMap(
    (condition) => condition.evidenceReadoutIds ?? []
  );
  const contradictingReadoutIds = parsed.fusionAssessment.observedOrInferredConditions
    .filter((condition) => condition.status === "contradicted" || condition.logicalRole === "contradicting")
    .flatMap((condition) => condition.evidenceReadoutIds ?? []);
  const supportingReadoutIds = uniqueStrings([
    ...calibratedProductReadouts.map((readout) => readout.readoutId),
    ...conditionReadoutIds.filter((readoutId) => readoutById.has(readoutId))
  ]);
  const supportingArtifactIds = uniqueStrings([
    ...supportingReadoutIds.map((readoutId) => readoutById.get(readoutId)?.artifactId).filter((value): value is string => value !== undefined),
    ...parsed.fusionAssessment.observedOrInferredConditions.flatMap((condition) => condition.evidenceArtifactIds)
  ]).filter((artifactId) => artifactById.has(artifactId));
  const alternativeSources = parsed.target.candidateEnergySources
    .filter((source) => source !== "fusion" && source !== "unknown")
    .map((source) => source.replace(/_/g, " "));
  const alternatives = alternativeSources.length > 0
    ? alternativeSources
    : ["non-fusion source", "instrument response", "insufficient diagnostic coverage"];
  const method = options.method ?? "conservative_fusion_condition_review";
  const canSupportFusion =
    parsed.fusionAssessment.fusionStatus === "supported" &&
    parsed.fusionAssessment.conditionMode !== "inverse_from_fusion_condition" &&
    !hasUnspecifiedRequiredConditions &&
    missingRequiredConditions.length === 0 &&
    missingObservables.length === 0 &&
    calibratedProductReadouts.length > 0;

  let disposition: ConservativeFusionClaimDisposition;
  let claimStatus: InvestigationClaim["status"];
  let statement: string;
  if (canSupportFusion) {
    disposition = "fusion_claim_supported";
    claimStatus = "support";
    statement = "Current mediated observations support a fusion claim within the stated limitations.";
  } else if (contradictingReadoutIds.length > 0 || parsed.fusionAssessment.fusionStatus === "contradicted") {
    disposition = "fusion_claim_contradicted";
    claimStatus = supportingReadoutIds.length > 0 || contradictingReadoutIds.length > 0 ? "contradict" : "inconclusive";
    statement = "Current mediated observations contradict at least one necessary fusion-condition claim.";
  } else if (parsed.fusionAssessment.fusionStatus === "unsupported" && supportingReadoutIds.length > 0) {
    disposition = "fusion_claim_not_supported";
    claimStatus = "support";
    statement = "Current mediated observations do not support a fusion claim.";
  } else if (supportingReadoutIds.length === 0) {
    disposition = "fusion_claim_untested";
    claimStatus = "untested";
    statement = "Fusion remains untested because no mediated fusion-relevant readouts are available.";
  } else {
    disposition = "fusion_claim_unknown";
    claimStatus = "inconclusive";
    statement = "Fusion remains unresolved because necessary conditions or diagnostics are still missing.";
  }

  const evidenceReadoutIds = uniqueStrings([
    ...supportingReadoutIds,
    ...contradictingReadoutIds.filter((readoutId) => readoutById.has(readoutId))
  ]);
  const evidenceArtifactIds = uniqueStrings([
    ...supportingArtifactIds,
    ...evidenceReadoutIds.map((readoutId) => readoutById.get(readoutId)?.artifactId).filter((value): value is string => value !== undefined)
  ]);
  const nextObservations = uniqueStrings([
    ...missingObservables.map((observable) => `Add a calibrated mediated readout for ${observable}.`),
    ...missingRequiredConditions.map((parameter) => `Resolve fusion condition '${parameter}'.`),
    ...(hasUnspecifiedRequiredConditions ? ["State the necessary fusion conditions before strengthening the claim."] : []),
    ...parsed.fusionAssessment.unknowns.map((unknown) => `Resolve ${unknown}.`)
  ]).slice(0, 6);
  const limitations = uniqueStrings([
    "Fusion is assessed as a claim, not treated as a premise.",
    "Candidate energy-source labels are not evidence by themselves.",
    ...parsed.fusionAssessment.limitations,
    ...(missingObservables.length > 0 ? [`Missing observables: ${missingObservables.join(", ")}.`] : []),
    ...(missingRequiredConditions.length > 0
      ? [`Missing required fusion conditions: ${missingRequiredConditions.join(", ")}.`]
      : []),
    ...(hasUnspecifiedRequiredConditions ? ["Required fusion conditions are not enumerated."] : []),
    ...(calibratedProductReadouts.length === 0
      ? ["No calibrated fusion-product readout with structured instrument response is available."]
      : [])
  ]);
  const claim: InvestigationClaim = {
    kind: "openplazma.investigation_claim",
    version: "0.1.0",
    claimId: options.claimId ?? `${parsed.packageId}-conservative-fusion-claim`,
    claimType: "fusion_status",
    statement,
    status: claimStatus,
    evidenceArtifactIds,
    ...(evidenceReadoutIds.length > 0 ? { evidenceReadoutIds } : {}),
    method,
    assumptions: ["The assessment only uses mediated package evidence and condition estimates."],
    limitations,
    alternatives
  };

  return {
    packageId: parsed.packageId,
    fusionAssessment: parsed.fusionAssessment,
    claim,
    disposition,
    missingObservables,
    missingRequiredConditions,
    hasUnspecifiedRequiredConditions,
    supportingReadoutIds,
    supportingArtifactIds,
    nextObservations,
    summary: statement,
    limitations
  };
}

export interface BuildInvestigationPackageInput {
  packageId: string;
  title: string;
  target: InvestigationTarget;
  questions: InvestigationQuestion[];
  artifacts?: DiagnosticArtifact[] | undefined;
  observations?: ObservationStatement[] | undefined;
  fusionAssessment?: FusionConditionAssessment | undefined;
  claims?: InvestigationClaim[] | undefined;
  limitations?: string[] | undefined;
}

export interface CreateInvestigationSessionInput {
  sessionId: string;
  package: InvestigationPackage;
  requiredObservables?: MeasuredObservable[] | undefined;
  createdAt?: string | undefined;
  updatedAt?: string | undefined;
  status?: InvestigationSessionStatus | undefined;
  reports?: InvestigationReport[] | undefined;
  limitations?: string[] | undefined;
}

export interface CreateInvestigationSessionReportOptions {
  reportId?: string | undefined;
  createdAt?: string | undefined;
  claims?: InvestigationClaim[] | undefined;
  assumptions?: string[] | undefined;
  limitations?: string[] | undefined;
  nextObservations?: string[] | undefined;
}

export interface InvestigationSessionAssessment {
  sessionId: string;
  packageId: string;
  status: InvestigationSessionStatus;
  measurementAssessment: InvestigationMeasurementAssessment;
  readyForReport: boolean;
  reportCount: number;
  latestReportId?: string | undefined;
  summary: string;
  limitations: string[];
}

function nowIso(): string {
  return new Date().toISOString();
}

function defaultFusionAssessment(packageId: string): FusionConditionAssessment {
  return {
    kind: "openplazma.fusion_condition_assessment",
    version: "0.1.0",
    assessmentId: `${packageId}-fusion-assessment`,
    fusionStatus: "unknown",
    conditionMode: "unknown",
    reactionCandidates: ["unknown"],
    observedOrInferredConditions: [],
    requiredConditions: [],
    unknowns: ["source identity", "plasma presence", "fusion products", "plasma maintenance"],
    assumptions: [],
    limitations: ["No fusion condition assessment has been resolved."]
  };
}

function uniqueArtifacts(artifacts: DiagnosticArtifact[]): DiagnosticArtifact[] {
  const seen = new Set<string>();
  for (const artifact of artifacts) {
    if (seen.has(artifact.artifactId)) {
      throw new Error(`Duplicate diagnostic artifact id '${artifact.artifactId}'.`);
    }
    seen.add(artifact.artifactId);
  }
  return artifacts;
}

function uniqueObservations(observations: ObservationStatement[]): ObservationStatement[] {
  const seen = new Set<string>();
  for (const observation of observations) {
    if (seen.has(observation.readoutId)) {
      throw new Error(`Duplicate observation readout id '${observation.readoutId}'.`);
    }
    seen.add(observation.readoutId);
  }
  return observations;
}

function assertClaimArtifactRefs(pack: InvestigationPackage, claim: InvestigationClaim): void {
  const artifactIds = new Set(pack.artifacts.map((artifact) => artifact.artifactId));
  for (const artifactId of claim.evidenceArtifactIds) {
    if (!artifactIds.has(artifactId)) {
      throw new Error(`Investigation claim references unknown diagnostic artifact '${artifactId}'.`);
    }
  }
}

function assertInvestigationReportContract(pack: InvestigationPackage, report: InvestigationReport): void {
  if (report.claims.length === 0) {
    throw new Error("Investigation report requires at least one claim.");
  }
  if (report.limitations.length === 0) {
    throw new Error("Investigation report requires at least one limitation.");
  }
  parseInvestigationReport(report);
  if (report.packageId !== pack.packageId) {
    throw new Error("Investigation report packageId must match the session package.");
  }
  for (const claim of report.claims) {
    assertClaimArtifactRefs(pack, claim);
  }
}

function assertInvestigationSessionContract(session: InvestigationSession): void {
  parseInvestigationSession(session);
}

function deriveSessionStatus(pack: InvestigationPackage, reports: InvestigationReport[]): InvestigationSessionStatus {
  if (reports.length > 0) {
    return "reported";
  }
  if (pack.artifacts.length > 0 && pack.claims.length > 0) {
    return "ready_for_report";
  }
  return "collecting_evidence";
}

function defaultNextObservations(session: InvestigationSession): string[] {
  const assessment = assessInvestigationMeasurements(session.package, session.requiredObservables);
  const observables = assessment.missingObservables.map(
    (observable) => `Add a calibrated diagnostic for ${observable}.`
  );
  const unknowns = session.package.fusionAssessment.unknowns.map((unknown) => `Resolve ${unknown}.`);
  const next = [...observables, ...unknowns].slice(0, 4);
  return next.length > 0 ? next : ["Add an independent calibrated diagnostic before strengthening the claim."];
}

export function buildInvestigationPackage(input: BuildInvestigationPackageInput): InvestigationPackage {
  const pack: InvestigationPackage = {
    kind: "openplazma.investigation_package",
    version: "0.1.0",
    packageId: input.packageId,
    title: input.title,
    target: input.target,
    questions: input.questions,
    artifacts: uniqueArtifacts(input.artifacts ?? []),
    observations: input.observations === undefined ? undefined : uniqueObservations(input.observations),
    fusionAssessment: input.fusionAssessment ?? defaultFusionAssessment(input.packageId),
    claims: input.claims ?? [],
    limitations: input.limitations ?? ["External investigation package; source-specific limitations must be reviewed."]
  };
  for (const claim of pack.claims) {
    assertClaimArtifactRefs(pack, claim);
  }
  return parseInvestigationPackage(pack);
}

export function createInvestigationSession(input: CreateInvestigationSessionInput): InvestigationSession {
  const reports = input.reports ?? [];
  const createdAt = input.createdAt ?? nowIso();
  const session: InvestigationSession = {
    kind: "openplazma.investigation_session",
    version: "0.1.0",
    sessionId: input.sessionId,
    createdAt,
    updatedAt: input.updatedAt ?? createdAt,
    status: input.status ?? deriveSessionStatus(input.package, reports),
    package: input.package,
    requiredObservables: input.requiredObservables ?? [],
    reports,
    limitations: input.limitations ?? ["Read-only investigation session; no facility telemetry or control path."]
  };
  assertInvestigationSessionContract(session);
  return session;
}

export function addDiagnosticArtifact(
  session: InvestigationSession,
  artifact: DiagnosticArtifact,
  updatedAt: string = nowIso()
): InvestigationSession {
  const artifacts = uniqueArtifacts([...session.package.artifacts, artifact]);
  const nextPackage: InvestigationPackage = {
    ...session.package,
    artifacts
  };
  const nextSession: InvestigationSession = {
    ...session,
    updatedAt,
    status: deriveSessionStatus(nextPackage, session.reports),
    package: nextPackage
  };
  assertInvestigationSessionContract(nextSession);
  return nextSession;
}

export function addObservationStatement(
  session: InvestigationSession,
  observation: ObservationStatement,
  updatedAt: string = nowIso()
): InvestigationSession {
  const observations = uniqueObservations([...(session.package.observations ?? []), observation]);
  const nextPackage: InvestigationPackage = {
    ...session.package,
    observations
  };
  const nextSession: InvestigationSession = {
    ...session,
    updatedAt,
    status: deriveSessionStatus(nextPackage, session.reports),
    package: nextPackage
  };
  assertInvestigationSessionContract(nextSession);
  return nextSession;
}

export function addInvestigationClaim(
  session: InvestigationSession,
  claim: InvestigationClaim,
  updatedAt: string = nowIso()
): InvestigationSession {
  assertClaimArtifactRefs(session.package, claim);
  const nextPackage: InvestigationPackage = {
    ...session.package,
    claims: [...session.package.claims, claim]
  };
  const nextSession: InvestigationSession = {
    ...session,
    updatedAt,
    status: deriveSessionStatus(nextPackage, session.reports),
    package: nextPackage
  };
  assertInvestigationSessionContract(nextSession);
  return nextSession;
}

export function createInvestigationSessionReport(
  session: InvestigationSession,
  options: CreateInvestigationSessionReportOptions = {}
): InvestigationReport {
  const claims = options.claims ?? session.package.claims;
  if (claims.length === 0) {
    throw new Error("Investigation report requires at least one claim.");
  }
  for (const claim of claims) {
    assertClaimArtifactRefs(session.package, claim);
  }
  const report: InvestigationReport = {
    kind: "openplazma.investigation_report",
    version: "0.1.0",
    reportId: options.reportId ?? `report-${session.sessionId}`,
    packageId: session.package.packageId,
    createdAt: options.createdAt ?? nowIso(),
    claims,
    assumptions: options.assumptions ?? session.package.fusionAssessment.assumptions,
    limitations: options.limitations ?? [...session.limitations, ...session.package.limitations],
    nextObservations: options.nextObservations ?? defaultNextObservations(session)
  };
  assertInvestigationReportContract(session.package, report);
  return report;
}

export function recordInvestigationReport(
  session: InvestigationSession,
  report: InvestigationReport,
  updatedAt: string = nowIso()
): InvestigationSession {
  assertInvestigationReportContract(session.package, report);
  const nextSession: InvestigationSession = {
    ...session,
    updatedAt,
    status: "reported",
    reports: [...session.reports, report]
  };
  assertInvestigationSessionContract(nextSession);
  return nextSession;
}

export function assessInvestigationSession(session: InvestigationSession): InvestigationSessionAssessment {
  const measurementAssessment = assessInvestigationMeasurements(session.package, session.requiredObservables);
  const readyForReport = session.package.artifacts.length > 0 && session.package.claims.length > 0;
  const latestReport = session.reports[session.reports.length - 1];
  return {
    sessionId: session.sessionId,
    packageId: session.package.packageId,
    status: session.status,
    measurementAssessment,
    readyForReport,
    reportCount: session.reports.length,
    latestReportId: latestReport?.reportId,
    summary: readyForReport
      ? "The session has evidence and at least one claim ready for a report."
      : "The session still needs evidence and a claim before report generation.",
    limitations: [...session.limitations, ...measurementAssessment.limitations]
  };
}

export interface CrashDetectOptions {
  /** Crash threshold as mean + thresholdSigma * stddev of the signal. */
  thresholdSigma?: number;
  /** Minimum spacing between crashes, seconds (refractory period). */
  minSpacingSec?: number;
}

/** Backwards-compatible alias for ELM-specific call sites. */
export type ElmDetectOptions = CrashDetectOptions;

/**
 * Detect periodic crashes as sharp local maxima above an adaptive threshold,
 * respecting a refractory spacing. Shared by ELM (D-alpha) and sawtooth
 * (central soft-X-ray) detection.
 */
export function detectPeriodicCrashes(series: SignalSeries, options: CrashDetectOptions = {}): ElmCrash[] {
  const { values, time } = series;
  const n = values.length;
  if (n < 3) {
    return [];
  }
  const threshold = mean(values) + (options.thresholdSigma ?? 2) * stddev(values);
  const dt = inferDt(time);
  const minSpacing = options.minSpacingSec ?? 0;
  const crashes: ElmCrash[] = [];
  let lastTime = Number.NEGATIVE_INFINITY;
  for (let i = 1; i < n - 1; i += 1) {
    const v = values[i] ?? 0;
    const prev = values[i - 1] ?? 0;
    const next = values[i + 1] ?? 0;
    if (v > threshold && v >= prev && v > next) {
      const t = time[i] ?? i * dt;
      if (t - lastTime >= minSpacing) {
        crashes.push({ time: t, amplitude: v });
        lastTime = t;
      }
    }
  }
  return crashes;
}

/** Detect ELM crashes (alias of {@link detectPeriodicCrashes}). */
export function detectElmCrashes(series: SignalSeries, options: ElmDetectOptions = {}): ElmCrash[] {
  return detectPeriodicCrashes(series, options);
}

export interface CrashStats {
  frequencyHz: number;
  /** 0..1, where 1 is perfectly periodic crash spacing. */
  regularity: number;
}

/** Repetition frequency and regularity of a crash train. */
export function crashStats(crashes: ElmCrash[]): CrashStats {
  const intervals: number[] = [];
  for (let i = 1; i < crashes.length; i += 1) {
    intervals.push((crashes[i]?.time ?? 0) - (crashes[i - 1]?.time ?? 0));
  }
  const meanInterval = mean(intervals);
  const frequencyHz = meanInterval > 0 ? 1 / meanInterval : 0;
  const cv = meanInterval > 0 ? stddev(intervals) / meanInterval : 1;
  const regularity = intervals.length === 0 ? 0 : Math.max(0, Math.min(1, 1 - cv));
  return { frequencyHz, regularity };
}

export interface ThresholdCrossing {
  crossed: boolean;
  time?: number | undefined;
}

/** First time the signal rises to or above a threshold (e.g. radiated fraction -> 1). */
export function detectThresholdCrossing(series: SignalSeries, threshold: number): ThresholdCrossing {
  for (let i = 0; i < series.values.length; i += 1) {
    if ((series.values[i] ?? Number.NEGATIVE_INFINITY) >= threshold) {
      return { crossed: true, time: series.time[i] };
    }
  }
  return { crossed: false };
}

/**
 * Estimate a magnetic-island width from a fluctuation amplitude. Island width
 * scales as sqrt of the perturbed field, so this is width ~ gain * sqrt(amp).
 * Educational scaling only, not a calibrated reconstruction.
 */
export function estimateNtmIslandWidth(amplitude: number, gainMPerSqrtAu = 1): number {
  return gainMPerSqrtAu * Math.sqrt(Math.max(0, amplitude));
}

function classifyElms(frequencyHz: number, regularity: number): ElmClassification {
  if (frequencyHz <= 0) {
    return "unknown";
  }
  // Coarse heuristic: regular, well-separated crashes read as Type I;
  // dense and irregular bursts read as Type III.
  if (regularity >= 0.6) {
    return "type_I";
  }
  if (frequencyHz > 200) {
    return "type_III";
  }
  return "unknown";
}

export interface AnalyzeElmsOptions extends ElmDetectOptions {
  analysisId?: string;
  label?: string;
}

export function analyzeElms(series: SignalSeries, options: AnalyzeElmsOptions = {}): ElmAnalysis {
  const crashes = detectElmCrashes(series, options);
  const { frequencyHz: elmFrequencyHz, regularity } = crashStats(crashes);
  const classification = classifyElms(elmFrequencyHz, regularity);

  return {
    kind: "openplazma.elm_analysis",
    version: "0.1.0",
    analysisId: options.analysisId ?? `elm-${series.signalId}`,
    label: options.label ?? `ELM analysis on ${series.label}`,
    sourceSignalId: series.signalId,
    crashes,
    elmFrequencyHz,
    regularity,
    classification,
    assumptions: [
      "Crashes appear as sharp positive spikes in the source signal.",
      "Crash spacing reflects the ELM cycle."
    ],
    limitations: [
      "Threshold-based detection can miss small crashes or merge close ones.",
      "Classification is a coarse heuristic, not a pedestal-stability calculation."
    ]
  };
}
