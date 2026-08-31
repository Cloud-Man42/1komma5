"use client";

export function EconomyInfoTip({ text }: { text: string }) {
  return (
    <span className="edash-info-tip" tabIndex={0} aria-label={text}>
      <span className="edash-info-tip-icon" aria-hidden="true">
        i
      </span>
      <span className="edash-info-tip-body" role="tooltip">
        {text}
      </span>
    </span>
  );
}
