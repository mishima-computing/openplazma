import type { DiagnosticArray, SignalSeries } from "@openplazma/core";

export interface ChartMarker {
  time: number;
  label: string;
  phenomenon?: string;
}

export interface SignalChartProps {
  series: SignalSeries;
  width?: number;
  height?: number;
  markers?: ChartMarker[];
  /** Additional series drawn on the same axes (shared scaling). */
  overlay?: SignalSeries[];
}

function extent(values: number[]): [number, number] {
  return [Math.min(...values), Math.max(...values)];
}

export function SignalChart({ series, width = 520, height = 180, markers = [], overlay = [] }: SignalChartProps) {
  const padding = 18;
  const plotWidth = width - padding * 2;
  const plotHeight = height - padding * 2;

  const allSeries = [series, ...overlay];
  const allTimes = allSeries.flatMap((s) => s.time);
  const allValues = allSeries.flatMap((s) => s.values);
  const [minTime, maxTime] = extent(allTimes);
  const [minValue, maxValue] = extent(allValues);
  const timeSpan = maxTime === minTime ? 1 : maxTime - minTime;
  const valueSpan = maxValue === minValue ? 1 : maxValue - minValue;

  const xAt = (time: number) => padding + ((time - minTime) / timeSpan) * plotWidth;
  const yAt = (value: number) => padding + (1 - (value - minValue) / valueSpan) * plotHeight;

  const toPoints = (s: SignalSeries) =>
    s.time
      .map((time, index) => `${xAt(time).toFixed(1)},${yAt(s.values[index] ?? 0).toFixed(1)}`)
      .join(" ");

  return (
    <figure className="signal-chart" aria-label={`${series.label} signal chart`}>
      <figcaption>
        <strong>{series.label}</strong>
        <span>
          {series.quantity} ({series.unit})
        </span>
      </figcaption>
      <svg viewBox={`0 0 ${width} ${height}`} role="img">
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} />
        {overlay.map((s) => (
          <polyline key={s.signalId} className="signal-overlay" points={toPoints(s)} fill="none" />
        ))}
        <polyline points={toPoints(series)} fill="none" />
        {markers.map((marker, index) => {
          const x = xAt(marker.time);
          return (
            <g key={`${marker.label}-${index}`} className="signal-marker" data-phenomenon={marker.phenomenon}>
              <line x1={x} y1={padding} x2={x} y2={height - padding} />
              <text x={x + 2} y={padding + 9}>
                {marker.label}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

export interface MirnovArrayChartProps {
  array: DiagnosticArray;
  signals: SignalSeries[];
  markers?: ChartMarker[];
  width?: number;
  height?: number;
}

/**
 * Stacked small-multiples of a magnetic-probe array, ordered by toroidal angle,
 * so a rotating mode reads as a diagonal travelling pattern across the probes.
 */
export function MirnovArrayChart({ array, signals, markers = [], width = 520, height = 260 }: MirnovArrayChartProps) {
  const padding = 18;
  const plotWidth = width - padding * 2;
  const byId = new Map(signals.map((s) => [s.signalId, s]));

  const channels = [...array.channels].sort(
    (a, b) => a.geometry.toroidalAngleRad - b.geometry.toroidalAngleRad
  );
  const rowHeight = (height - padding * 2) / Math.max(1, channels.length);

  const allTimes = channels.flatMap((c) => byId.get(c.signalId)?.time ?? []);
  const minTime = allTimes.length ? Math.min(...allTimes) : 0;
  const maxTime = allTimes.length ? Math.max(...allTimes) : 1;
  const timeSpan = maxTime === minTime ? 1 : maxTime - minTime;
  const xAt = (time: number) => padding + ((time - minTime) / timeSpan) * plotWidth;

  return (
    <figure className="mirnov-array-chart" aria-label={`${array.label} array chart`}>
      <figcaption>
        <strong>{array.label}</strong>
        <span>{channels.length} probes, ordered by toroidal angle</span>
      </figcaption>
      <svg viewBox={`0 0 ${width} ${height}`} role="img">
        {channels.map((channel, row) => {
          const series = byId.get(channel.signalId);
          if (!series) {
            return null;
          }
          const [minValue, maxValue] = extent(series.values);
          const valueSpan = maxValue === minValue ? 1 : maxValue - minValue;
          const rowTop = padding + row * rowHeight;
          const yAt = (value: number) => rowTop + (1 - (value - minValue) / valueSpan) * rowHeight * 0.85;
          const points = series.time
            .map((time, index) => `${xAt(time).toFixed(1)},${yAt(series.values[index] ?? 0).toFixed(1)}`)
            .join(" ");
          return (
            <g key={channel.channelId} className="mirnov-row">
              <text x={padding} y={rowTop + 8} className="mirnov-row-label">
                {channel.label}
              </text>
              <polyline points={points} fill="none" />
            </g>
          );
        })}
        {markers.map((marker, index) => {
          const x = xAt(marker.time);
          return (
            <g key={`${marker.label}-${index}`} className="signal-marker" data-phenomenon={marker.phenomenon}>
              <line x1={x} y1={padding} x2={x} y2={height - padding} />
              <text x={x + 2} y={padding + 9}>
                {marker.label}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
