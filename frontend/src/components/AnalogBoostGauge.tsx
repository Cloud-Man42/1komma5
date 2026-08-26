"use client";

import { useId, type CSSProperties } from "react";

import {
  DEFAULT_GAUGE_MAX_W,
  describeArc,
  formatGaugeKw,
  formatGaugeScaleKw,
  GAUGE_MAX_ANGLE,
  GAUGE_MIN_ANGLE,
  gaugeFillRatio,
  isGaugeActive,
  needleAngleForWatts,
  polar,
  tickAngles,
  type GaugeScaleMode,
} from "@/lib/analogGauge";

export interface AnalogBoostGaugeProps {
  label: string;
  watts: number;
  maxW?: number;
  mode?: GaugeScaleMode;
  directionLabel?: string;
  secondary?: string;
  accent: string;
  accentGlow?: string;
  compact?: boolean;
  icon?: string;
}

const TICK_COUNT = 11;

export function AnalogBoostGauge({
  label,
  watts,
  maxW = DEFAULT_GAUGE_MAX_W,
  mode = "positive",
  directionLabel,
  secondary,
  accent,
  accentGlow,
  compact = false,
  icon,
}: AnalogBoostGaugeProps) {
  const uid = useId().replace(/:/g, "");
  const cx = 100;
  const cy = 98;
  const radius = compact ? 62 : 72;
  const needleAngle = needleAngleForWatts(watts, maxW, mode);
  const fill = gaugeFillRatio(watts, maxW, mode);
  const active = isGaugeActive(watts, mode);
  const glow = accentGlow ?? accent;
  const ticks = tickAngles(TICK_COUNT);

  const fillStart = mode === "bidirectional" ? 0 : GAUGE_MIN_ANGLE;
  const fillEnd =
    mode === "bidirectional"
      ? needleAngle
      : GAUGE_MIN_ANGLE + fill * (GAUGE_MAX_ANGLE - GAUGE_MIN_ANGLE);

  const ariaValue = mode === "bidirectional" ? watts : Math.max(0, watts);
  const displayValue = `${formatGaugeKw(watts)} kW`;

  return (
    <div
      className={`analog-boost-gauge ${compact ? "analog-boost-gauge-compact" : ""} ${active ? "is-active" : ""}`}
      style={
        {
          "--gauge-accent": accent,
          "--gauge-glow": glow,
          "--gauge-fill": fill,
        } as CSSProperties
      }
      role="meter"
      aria-label={label}
      aria-valuemin={mode === "bidirectional" ? -maxW : 0}
      aria-valuemax={maxW}
      aria-valuenow={Math.round(ariaValue)}
      aria-valuetext={`${displayValue}${directionLabel ? `, ${directionLabel}` : ""}`}
    >
      <svg
        className="analog-boost-gauge-svg"
        viewBox="0 0 200 128"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <linearGradient id={`${uid}-bezel`} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#4b5563" />
            <stop offset="45%" stopColor="#1f2937" />
            <stop offset="100%" stopColor="#0b0f14" />
          </linearGradient>
          <linearGradient id={`${uid}-face`} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#111827" />
            <stop offset="100%" stopColor="#030712" />
          </linearGradient>
          <linearGradient id={`${uid}-arc`} x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={accent} stopOpacity="0.15" />
            <stop offset="100%" stopColor={glow} stopOpacity="0.95" />
          </linearGradient>
          <filter id={`${uid}-glow`} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <ellipse cx={cx} cy={cy + 8} rx={radius + 16} ry={12} className="analog-boost-gauge-shadow" />

        <path
          d={describeArc(cx, cy, radius + 10, GAUGE_MIN_ANGLE - 4, GAUGE_MAX_ANGLE + 4)}
          className="analog-boost-gauge-bezel"
          fill="none"
          stroke={`url(#${uid}-bezel)`}
          strokeWidth="10"
          strokeLinecap="round"
        />

        <path
          d={describeArc(cx, cy, radius + 2, GAUGE_MIN_ANGLE, GAUGE_MAX_ANGLE)}
          className="analog-boost-gauge-track"
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
        />

        {active && (
          <path
            d={describeArc(
              cx,
              cy,
              radius + 2,
              mode === "bidirectional" && watts < 0 ? fillEnd : fillStart,
              fillEnd,
            )}
            className="analog-boost-gauge-fill"
            fill="none"
            stroke={`url(#${uid}-arc)`}
            strokeWidth="8"
            strokeLinecap="round"
            filter={`url(#${uid}-glow)`}
          />
        )}

        {ticks.map((angle, index) => {
          const major = index % 2 === 0;
          const inner = polar(cx, cy, radius - (major ? 12 : 8), angle);
          const outer = polar(cx, cy, radius + (major ? 4 : 2), angle);
          return (
            <line
              key={angle}
              x1={inner.x}
              y1={inner.y}
              x2={outer.x}
              y2={outer.y}
              className={major ? "analog-boost-gauge-tick-major" : "analog-boost-gauge-tick-minor"}
            />
          );
        })}

        {mode === "bidirectional" && (
          <line
            x1={polar(cx, cy, radius - 6, 0).x}
            y1={polar(cx, cy, radius - 6, 0).y}
            x2={polar(cx, cy, radius + 2, 0).x}
            y2={polar(cx, cy, radius + 2, 0).y}
            className="analog-boost-gauge-zero"
          />
        )}

        <text
          x={polar(cx, cy, radius - 22, GAUGE_MIN_ANGLE + 6).x}
          y={polar(cx, cy, radius - 22, GAUGE_MIN_ANGLE + 6).y}
          className="analog-boost-gauge-scale-label"
        >
          0
        </text>
        <text
          x={polar(cx, cy, radius - 22, GAUGE_MAX_ANGLE - 6).x}
          y={polar(cx, cy, radius - 22, GAUGE_MAX_ANGLE - 6).y}
          className="analog-boost-gauge-scale-label analog-boost-gauge-scale-label-max"
        >
          {formatGaugeScaleKw(maxW)}
        </text>
        {mode === "bidirectional" ? (
          <text
            x={polar(cx, cy, radius - 24, -GAUGE_MAX_ANGLE + 8).x}
            y={polar(cx, cy, radius - 24, -GAUGE_MAX_ANGLE + 8).y}
            className="analog-boost-gauge-scale-label analog-boost-gauge-scale-label-min"
          >
            −{formatGaugeScaleKw(maxW)}
          </text>
        ) : null}

        <g
          className="analog-boost-gauge-needle-group"
          style={{ transform: `rotate(${needleAngle}deg)`, transformOrigin: `${cx}px ${cy}px` } as CSSProperties}
        >
          <line
            x1={cx}
            y1={cy}
            x2={cx}
            y2={cy - radius + (compact ? 14 : 18)}
            className="analog-boost-gauge-needle-shadow"
          />
          <line
            x1={cx}
            y1={cy}
            x2={cx}
            y2={cy - radius + (compact ? 14 : 18)}
            className="analog-boost-gauge-needle"
          />
        </g>

        <circle cx={cx} cy={cy} r={compact ? 7 : 8} className="analog-boost-gauge-hub" />
        <circle cx={cx} cy={cy} r={compact ? 3 : 3.5} className="analog-boost-gauge-hub-cap" />
      </svg>

      <div className="analog-boost-gauge-readout">
        {icon ? <span className="analog-boost-gauge-icon">{icon}</span> : null}
        <span className="analog-boost-gauge-value">{displayValue}</span>
        {directionLabel ? (
          <span className="analog-boost-gauge-direction">{directionLabel}</span>
        ) : null}
        {secondary ? <span className="analog-boost-gauge-secondary">{secondary}</span> : null}
      </div>

      <span className="analog-boost-gauge-label">{label}</span>
    </div>
  );
}
