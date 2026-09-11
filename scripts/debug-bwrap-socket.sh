#!/usr/bin/env bash
set -eu
SOCKDIR="/tmp/bwrap-sock-test-$$"
mkdir -p "$SOCKDIR"
PY="/home/hm/energy-monitoring/.venv-linux-isolation/bin/python3"
export SOCKDIR

SOCKDIR="$SOCKDIR" "$PY" -c "
import asyncio, os
from pathlib import Path
async def main():
    path = Path(os.environ['SOCKDIR']) / 'test.sock'
    if path.exists(): path.unlink()
    server = await asyncio.start_unix_server(lambda r,w: None, path=str(path))
    os.chmod(path, 0o600)
    os.chown(path, 10001, 10001)
    print('socket ready', path)
    await asyncio.sleep(30)
asyncio.run(main())
" &
SERVER_PID=$!
sleep 1
if [ -z "${EMIC_DEPLOY_SUDO_PASSWORD:-}" ]; then
  echo "Set EMIC_DEPLOY_SUDO_PASSWORD for sudo access" >&2
  exit 1
fi
echo "$EMIC_DEPLOY_SUDO_PASSWORD" | sudo -S bwrap \
  --unshare-user --uid 10001 --gid 10001 \
  --unshare-net --cap-drop ALL \
  --dev /dev \
  --bind "$SOCKDIR" "$SOCKDIR" \
  --ro-bind "$PY" "$PY" \
  --ro-bind /lib /lib --ro-bind /lib64 /lib64 --ro-bind /usr/lib /usr/lib \
  --setenv SOCKDIR "$SOCKDIR" \
  "$PY" -c "import os,socket; s=socket.socket(socket.AF_UNIX); s.connect(os.environ['SOCKDIR']+'/test.sock'); print('connected')"
kill "$SERVER_PID" 2>/dev/null || true
rm -rf "$SOCKDIR"
