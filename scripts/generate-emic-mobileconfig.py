#!/usr/bin/env python3
"""Build an iOS/mobileconfig profile that trusts the EMIC Caddy root CA."""

from __future__ import annotations

import argparse
import base64
import pathlib
import uuid


def build_mobileconfig(cert_pem: bytes, display_name: str = "EMIC Local HTTPS") -> bytes:
    cert_b64 = base64.b64encode(cert_pem).decode("ascii")
    payload_uuid = str(uuid.uuid4()).upper()
    root_uuid = str(uuid.uuid4()).upper()
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>PayloadContent</key>
  <array>
    <dict>
      <key>PayloadCertificateFileName</key>
      <string>emic-ca.crt</string>
      <key>PayloadContent</key>
      <data>
{cert_b64}
      </data>
      <key>PayloadDescription</key>
      <string>Root certificate for EMIC on your home network.</string>
      <key>PayloadDisplayName</key>
      <string>{display_name}</string>
      <key>PayloadIdentifier</key>
      <string>se.inacloud.emic.ca.root</string>
      <key>PayloadType</key>
      <string>com.apple.security.root</string>
      <key>PayloadUUID</key>
      <string>{root_uuid}</string>
      <key>PayloadVersion</key>
      <integer>1</integer>
    </dict>
  </array>
  <key>PayloadDescription</key>
  <string>Install to trust https://emic.inacloud.se on iPhone and iPad.</string>
  <key>PayloadDisplayName</key>
  <string>{display_name}</string>
  <key>PayloadIdentifier</key>
  <string>se.inacloud.emic.profile</string>
  <key>PayloadOrganization</key>
  <string>EMIC</string>
  <key>PayloadRemovalDisallowed</key>
  <false/>
  <key>PayloadType</key>
  <string>Configuration</string>
  <key>PayloadUUID</key>
  <string>{payload_uuid}</string>
  <key>PayloadVersion</key>
  <integer>1</integer>
</dict>
</plist>
""".encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cert", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args()
    cert_pem = args.cert.read_bytes()
    if b"BEGIN CERTIFICATE" not in cert_pem:
        raise SystemExit(f"Not a PEM certificate: {args.cert}")
    args.output.write_bytes(build_mobileconfig(cert_pem))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
