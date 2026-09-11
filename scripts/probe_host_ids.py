import os
from pathlib import Path
Path("/data/hostids.txt").write_text(f"uid={os.getuid()} euid={os.geteuid()} gid={os.getgid()}\n", encoding="utf-8")
print(os.getuid(), os.getgid())
