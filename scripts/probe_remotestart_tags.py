import json
import os

import httpx

BASE = "https://my.charge.space"
CP = os.environ.get("CHARGEAMPS_PROBE_CHARGER_ID", "").strip()
if not CP:
    raise SystemExit("Set CHARGEAMPS_PROBE_CHARGER_ID")
r = httpx.post(
    f"{BASE}/api/auth/login",
    json={"email": os.environ["CHARGEAMPS_EMAIL"], "password": os.environ["CHARGEAMPS_PASSWORD"]},
    headers={"Origin": BASE},
    timeout=20,
)
h = {"Authorization": f"Bearer {r.json()['token']}", "Origin": BASE}
for path in [f"/chargepoints/{CP}/1/remotestart/tags", "/users/nfctags/own"]:
    resp = httpx.get(f"{BASE}/api{path}", headers=h, timeout=20)
    print(path, resp.status_code, resp.text[:1000])
