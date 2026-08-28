"use client";

import { useId, type CSSProperties } from "react";
import {
  describeArc,
  GAUGE_MAX_ANGLE,
  GAUGE_MIN_ANGLE,
  gaugeFillRatio,
  needleAngleForWatts,
  polar,
  tickAngles,
} from "@/lib/analogGauge";

const TICK_COUNT = 9;

export function SpaSemiGauge({
  title,
  value,
  max,
  displayValue,
  minLabel,
  maxLabel,
  footer,
  accent = "#38bdf8",
  accentGlow,
  statusLabel,
  statusOk,
}: {
  title: string;
  value: number;
  max: number;
  displayValue: string;
  minLabel: string;
  maxLabel: string;
  footer?: string;
  accent?: string;
  accentGlow?: string;
  statusLabel?: string;
  statusOk?: boolean;
}) {
  const uid = useId().replace(/:/g, "");
  const cx = 100;
  const cy = 98;
  const radius = 74;
  const ratio = gaugeFillRatio(value, max, "positive");
  const needleAngle = needleAngleForWatts(value, max, "positive");
  const fillEnd = GAUGE_MIN_ANGLE + ratio * (GAUGE_MAX_ANGLE - GAUGE_MIN_ANGLE);
  const arc = describeArc(cx, cy, radius, GAUGE_MIN_ANGLE, fillEnd);
  const glow = accentGlow ?? accent;
  const ticks = tickAngles(TICK_COUNT);
  const active = value > 0;

  return (
    <article
      className={`sdash-gauge-card ${active ? "is-active" : ""}`.trim()}
      style={{ "--sdash-gauge-accent": accent, "--sdash-gauge-glow": glow } as CSSProperties}
    >
      <p className="sdash-gauge-kicker">{title}</p>
      <div className="sdash-gauge-wrap">
        <svg viewBox="0 0 200 124" className="sdash-gauge-svg" aria-hidden="true">
          <defs>
            <linearGradient id={`${uid}-fill`} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={accent} stopOpacity="0.55" />
              <stop offset="100%" stopColor={glow} stopOpacity="1" />
            </linearGradient>
            <filter id={`${uid}-glow`} x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="2.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <path
            d={describeArc(cx, cy, radius, GAUGE_MIN_ANGLE, GAUGE_MAX_ANGLE)}
            fill="none"
            stroke="rgba(148,163,184,0.14)"
            strokeWidth="11"
            strokeLinecap="round"
          />
          {active ? (
            <path
              d={arc}
              fill="none"
              stroke={`url(#${uid}-fill)`}
              strokeWidth="11"
              strokeLinecap="round"
              filter={`url(#${uid}-glow)`}
            />
          ) : null}
          {ticks.map((angle) => {
            const outer = polar(cx, cy, radius + 2, angle);
            const inner = polar(cx, cy, radius - (angle % 36 === 0 ? 10 : 6), angle);
            return (
              <line
                key={angle}
                x1={inner.x}
                y1={inner.y}
                x2={outer.x}
                y2={outer.y}
                stroke="rgba(148,163,184,0.28)"
                strokeWidth={angle % 36 === 0 ? 1.6 : 1}
              />
            );
          })}
          <line
            x1={cx}
            y1={cy}
            x2={cx}
            y2={cy - radius + 12}
            stroke={accent}
            strokeWidth="2.5"
            strokeLinecap="round"
            transform={`rotate(${needleAngle} ${cx} ${cy})`}
            filter={active ? `url(#${uid}-glow)` : undefined}
          />
          <circle cx={cx} cy={cy} r="5.5" fill="#0f172a" stroke={accent} strokeWidth="2" />
        </svg>
        <div className="sdash-gauge-value">{displayValue}</div>
      </div>
      <div className="sdash-gauge-scale">
        <span>{minLabel}</span>
        <span>{maxLabel}</span>
      </div>
      {statusLabel ? (
        <p className={`sdash-gauge-status ${statusOk ? "is-ok" : ""}`.trim()}>
          {statusOk ? <span className="sdash-status-dot" aria-hidden="true" /> : null}
          {statusLabel}
        </p>
      ) : null}
      {footer ? <p className="sdash-gauge-footer">{footer}</p> : null}
    </article>
  );
}
