"use client";

/** Sanitize untrusted publisher text for safe display. */

const TAG_RE = /<[^>]+>/g;
const SCRIPT_RE = /<script[^>]*>[\s\S]*?<\/script>/gi;

export function sanitizeDisplayText(value: string): string {
  if (!value) return "";
  return value.replace(SCRIPT_RE, "").replace(TAG_RE, "").replace(/javascript:/gi, "").trim();
}

export function SafeText({ text, className }: { text: string; className?: string }) {
  return <span className={className}>{sanitizeDisplayText(text)}</span>;
}
