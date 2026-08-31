#!/usr/bin/env bash
# Detect the active DRM CRTC index for the HDMI panel (vc4 / Raspberry Pi).
# gammastep drm expects crtc index (0-3), not the modetest CRTC id.
set -euo pipefail

MODETEST_BIN="${MODETEST_BIN:-modetest}"

if ! command -v "$MODETEST_BIN" >/dev/null 2>&1; then
  echo "modetest not installed" >&2
  exit 1
fi

crtc_index="$("$MODETEST_BIN" -M vc4 -p 2>/dev/null | awk -F'\t' '
  /^CRTCs:/ { in_crtc = 1; idx = 0; next }
  /^Planes:/ { in_crtc = 0; next }
  in_crtc && NF >= 4 && $1 ~ /^[0-9]+$/ {
    idx++
    if ($2 ~ /^[0-9]+$/ && $2 > 0 && $4 ~ /\([0-9]+x[0-9]+\)/ && $4 !~ /\(0x0\)/) {
      print idx - 1
      exit
    }
  }
')"

if [ -z "${crtc_index:-}" ]; then
  echo "no active CRTC found" >&2
  exit 1
fi

echo "$crtc_index"
