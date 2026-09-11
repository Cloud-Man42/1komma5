#!/usr/bin/env bash
set -eu
TMP="/tmp/bwrap-sock3-$$"
mkdir -p "$TMP"
PY="/home/hm/energy-monitoring/.venv-linux-isolation/bin/python3"
SOCK="$TMP/test.sock"
python3 - <<PY &
import asyncio, os
from pathlib import Path
async def main():
    p = Path("$SOCK")
    if p.exists(): p.unlink()
    await asyncio.start_unix_server(lambda r,w: None, path=str(p))
    os.chmod(p, 0o666)
    await asyncio.sleep(20)
asyncio.run(main())
PY
sleep 1
bwrap \
  --unshare-net --cap-drop ALL \
  --dev /dev \
  --bind "$TMP" "$TMP" \
  --ro-bind "$PY" "$PY" \
  --ro-bind /lib /lib --ro-bind /lib64 /lib64 --ro-bind /usr/lib /usr/lib \
  "$PY" -c "import os,socket; print('uid', os.getuid()); s=socket.socket(socket.AF_UNIX); s.connect('$SOCK'); print('connected')"
kill %1 2>/dev/null || true
rm -rf "$TMP"
