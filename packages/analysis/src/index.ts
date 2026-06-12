import type {
  DiagnosticArray,
  DiagnosticChannel,
  ElmAnalysis,
  ElmClassification,
  ElmCrash,
  EvidenceLink,
  FrequencyAnalysis,
  FrequencyAnalysisMethod,
  FrequencyDomain,
  Inference,
  ModeNumberEstimate,
  PhenomenonEvent,
  RotationTrackPoint,
  SignalSeries,
  TearingModeHypothesis
} from "@openplazma/core";

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

  return {
    kind: "openplazma.inference",
    version: "0.1.0",
    inferenceId: options.inferenceId ?? `inf-${array.arrayId}`,
    label: options.label ?? `Phase-fit mode estimate for ${array.label}`,
    method: "magnetic_mode_phase_fit",
    sourceArrayId: array.arrayId,
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
    timeRange: hypothesis.timeRange,
    rationale: modeMatch
      ? `Phase fit recovers toroidal mode number n=${inference.modeEstimate.toroidalModeNumber}, matching the hypothesis (confidence ${inference.modeEstimate.confidence.toFixed(2)}).`
      : `Phase fit recovers n=${inference.modeEstimate.toroidalModeNumber}, not the hypothesised n=${hypothesis.toroidalModeNumber}.`
  });

  const quench = events.find((e) => e.phenomenon === "current_quench" || e.phenomenon === "disruption");
  if (inference.lockingDetected && inference.lockTimeRange && quench) {
    const locksBeforeQuench = inference.lockTimeRange[1] <= quench.timeRange[1];
    links.push({
      kind: "openplazma.evidence_link",
      version: "0.1.0",
      verdict: locksBeforeQuench ? "support" : "inconclusive",
      arrayId: inference.sourceArrayId,
      timeRange: inference.lockTimeRange,
      rationale: locksBeforeQuench
        ? "Mode rotation collapses (locks) before the current quench, consistent with a locked-mode disruption."
        : "Locking and quench timing overlap ambiguously."
    });
  } else {
    links.push({
      kind: "openplazma.evidence_link",
      version: "0.1.0",
      verdict: "inconclusive",
      arrayId: inference.sourceArrayId,
      timeRange: hypothesis.timeRange,
      rationale: "No clear locking-then-quench sequence was detected in the available signals."
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
