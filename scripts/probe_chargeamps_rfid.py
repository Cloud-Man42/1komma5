"""Probe Charge Amps RFID tags for remotestart."""
import json
import os
import sys

import httpx

CP = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CHARGEAMPS_PROBE_CHARGER_ID", "")).strip()
if not CP:
    raise SystemExit("Pass charger id as argv[1] or set CHARGEAMPS_PROBE_CHARGER_ID")
BASE = "https://my.charge.space"
email = os.environ.get("CHARGEAMPS_EMAIL", "")
password = os.environ.get("CHARGEAMPS_PASSWORD", "")

r = httpx.post(
    f"{BASE}/api/auth/login",
    json={"email": email, "password": password},
    headers={"Origin": BASE},
    timeout=20,
)
print("login", r.status_code)
token = r.json().get("token", "")
h = {"Authorization": f"Bearer {token}", "Origin": BASE}

data = httpx.get(f"{BASE}/api/chargepoints/{CP}", headers=h, timeout=20).json()
print("chargepoint keys:", sorted(data.keys())[:20])
for c in data.get("connectors", []):
    print("connector", json.dumps(c, indent=2)[:800])

for path in [
    f"/users/chargepoints/owned?expand=settings",
    f"/chargepoints/{CP}/rfidtags",
    f"/users/rfidtags",
]:
    try:
        resp = httpx.get(f"{BASE}/api{path}", headers=h, timeout=20)
        print(path, resp.status_code, resp.text[:500])
    except Exception as exc:
        print(path, exc)

# Try remotestart with various tags (dry - only if vehicle connected)
tags_to_try = ["999999", "123456"]
for c in data.get("connectors", []):
    tag = c.get("defaultNfcTagId")
    if tag:
        tags_to_try.insert(0, str(tag))

seen = set()
for tag in tags_to_try:
    if tag in seen:
        continue
    seen.add(tag)
    resp = httpx.put(
        f"{BASE}/api/chargepoints/{CP}/1/remotestart",
        headers=h,
        params={"rfidTag": tag},
        timeout=20,
    )
    print(f"remotestart tag={tag!r} -> {resp.status_code} {resp.text[:300]}")
