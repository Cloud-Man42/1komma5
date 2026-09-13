import base64
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "generate-emic-mobileconfig.py"
FIXTURE_CERT = """-----BEGIN CERTIFICATE-----
MIIBozCCAUqgAwIBAgIRAPi08c1uiO7zSKfBZMN00NAwCgYIKoZIzj0EAwIwMDEu
MCwGA1UEAxMlQ2FkZHkgTG9jYWwgQXV0aG9yaXR5IC0gMjAyNiBFQ0MgUm9vdDAe
Fw0yNjA4MTMwNjM4MzNaFw0zNjA2MjEwNjM4MzNaMDAxLjAsBgNVBAMTJUNhZGR5
IExvY2FsIEF1dGhvcml0eSAtIDIwMjYgRUNDIFJvb3QwWTATBgcqhkjOPQIBBggq
hkjOPQMBBwNCAAT4beoLFd+xuguYjxN00vUmpZ5EOzmVFpgdCvr8Iz0K/0HMUdac
jb7auy5Xa01AyKro7GjOxxOmHDdOA0UYeHefo0UwQzAOBgNVHQ8BAf8EBAMCAQYw
EgYDVR0TAQH/BAgwBgEB/wIBATAdBgNVHQ4EFgQU11VdLqP8UjnziTScvCCOBCXI
IzAwCgYIKoZIzj0EAwIDRwAwRAIgJGms2MpFA2OgWLuDiG7GMAvKpwZs5S4zuACA
TYzuNM8CIE2pxt34iITRE0uz6+jGRo+ZrzstM4KRHi4a++K//mOA
-----END CERTIFICATE-----
"""


def test_generate_emic_mobileconfig(tmp_path: Path) -> None:
    cert = tmp_path / "emic-ca.crt"
    out = tmp_path / "emic-ca.mobileconfig"
    cert.write_text(FIXTURE_CERT, encoding="utf-8")

    subprocess.run([sys.executable, str(SCRIPT), str(cert), str(out)], check=True)

    body = out.read_text(encoding="utf-8")
    assert "com.apple.security.root" in body
    assert "se.inacloud.emic.profile" in body
    cert_b64 = base64.b64encode(cert.read_bytes()).decode("ascii")
    assert cert_b64[:40] in body.replace("\n", "").replace(" ", "")


def test_generate_emic_mobileconfig_rejects_invalid(tmp_path: Path) -> None:
    cert = tmp_path / "bad.crt"
    out = tmp_path / "out.mobileconfig"
    cert.write_text("not a cert", encoding="utf-8")
    proc = subprocess.run([sys.executable, str(SCRIPT), str(cert), str(out)], capture_output=True, text=True)
    assert proc.returncode != 0
