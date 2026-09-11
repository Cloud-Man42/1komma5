# If executed during interpreter startup, record marker.
import json
import os
from pathlib import Path

Path("/data/usercustomize_probe.json").write_text(
    json.dumps({"uid": os.getuid(), "euid": os.geteuid(), "gid": os.getgid()}),
    encoding="utf-8",
)
