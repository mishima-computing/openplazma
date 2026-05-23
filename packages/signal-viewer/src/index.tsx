import type { SignalSeries } from "@openplazma/core";

export interface SignalChartProps {
  series: SignalSeries;
  width?: number;
  height?: number;
}

export function SignalChart({ series, width = 520, height = 180 }: SignalChartProps) {
  const padding = 18;
  const plotWidth = width - padding * 2;
  const plotHeight = height - padding * 2;
  const minTime = Math.min(...series.time);
  const maxTime = Math.max(...series.time);
  const minValue = Math.min(...series.values);
  const maxValue = Math.max(...series.values);
  const timeSpan = maxTime === minTime ? 1 : maxTime - minTime;
  const valueSpan = maxValue === minValue ? 1 : maxValue - minValue;

  const points = series.time
    .map((time, index) => {
      const value = series.values[index] ?? 0;
      const x = padding + ((time - minTime) / timeSpan) * plotWidth;
      const y = padding + (1 - (value - minValue) / valueSpan) * plotHeight;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
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
        <polyline points={points} fill="none" />
      </svg>
    </figure>
  );
}
