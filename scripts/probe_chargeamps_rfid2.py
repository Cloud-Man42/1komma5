"""Probe Charge Amps user NFC tags and charging state."""

import json
import os
import sys

import httpx

CP = (
    sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CHARGEAMPS_PROBE_CHARGER_ID", "")
).strip()
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
token = r.json().get("token", "")
h = {"Authorization": f"Bearer {token}", "Origin": BASE}

owned = httpx.get(
    f"{BASE}/api/users/chargepoints/owned?expand=settings", headers=h, timeout=20
).json()
for cp in owned:
    if cp.get("id") != CP:
        continue
    print("=== owned cp match ===")
    for key in sorted(cp.keys()):
        val = cp[key]
        if (
            "nfc" in key.lower()
            or "tag" in key.lower()
            or key in {"connectors", "id", "name", "ip"}
        ):
            print(key, val if key != "connectors" else "...")
    for c in cp.get("connectors", []):
        if c.get("connectorId") == 1:
            print("connector1 full:", json.dumps(c, indent=2))

# user endpoints
import base64

payload = token.split(".")[1]
payload += "=" * (-len(payload) % 4)
claims = json.loads(base64.urlsafe_b64decode(payload))
uid = claims.get("unique_name") or claims.get("sub")
print("user_id", uid)

for path in [
    f"/users/{uid}",
    f"/users/{uid}/nfctags",
    f"/users/{uid}/nfcTags",
    f"/users/{uid}/tags",
]:
    resp = httpx.get(f"{BASE}/api{path}", headers=h, timeout=20)
    print(path, resp.status_code, resp.text[:600])

data = httpx.get(f"{BASE}/api/chargepoints/{CP}", headers=h, timeout=20).json()
c1 = next(c for c in data["connectors"] if c["connectorId"] == 1)
print(
    "status fields:",
    {
        k: c1.get(k)
        for k in c1
        if "status" in k.lower()
        or k in {"isCharging", "ocppStatus", "mode", "remoteStartRequested"}
    },
)
