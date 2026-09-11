#!/usr/bin/env bash
set -eu
TMP="/tmp/bwrap-id-test-$$"
mkdir -p "$TMP/data"
chmod 777 "$TMP/data"
PY="/home/hm/energy-monitoring/.venv-linux-isolation/bin/python3"
bwrap \
  --unshare-user --uid 10001 --gid 10001 \
  --unshare-net --cap-drop ALL \
  --dev /dev --proc /proc \
  --bind "$TMP/data" /data \
  --ro-bind "$PY" "$PY" \
  --ro-bind /lib /lib --ro-bind /lib64 /lib64 --ro-bind /usr/lib /usr/lib \
  "$PY" -c "import time; time.sleep(30)" &
BPID=$!
sleep 0.5
echo "child pid $BPID"
cat /proc/$BPID/uid_map || true
cat /proc/$BPID/gid_map || true
kill "$BPID" 2>/dev/null || true
wait "$BPID" 2>/dev/null || true
rm -rf "$TMP"
