#!/usr/bin/env bash
# Strip CRLF from files copied from a Windows checkout, then make scripts executable.
# Run from inside the copied kiosk directory.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

for f in *; do
  [ -f "$f" ] || continue
  case "$f" in *.png|*.jpg) continue ;; esac
  tr -d '\r' <"$f" >"$f.normalized"
  mv "$f.normalized" "$f"
done

chmod +x ./*.sh
echo "normalized $(ls -1 | wc -l) files in $(pwd)"
