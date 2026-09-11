"""Benign isolated runtime demo module — no energy_core imports."""



from __future__ import annotations



import json

import os

import resource

import socket

import subprocess

import tempfile

import time

from pathlib import Path





def _write_probes(results: dict[str, str]) -> None:

    Path("/data/probes.json").write_text(json.dumps(results, sort_keys=True), encoding="utf-8")





def _try_read(path: str) -> str:

    try:

        with open(path, encoding="utf-8", errors="ignore") as handle:

            content = handle.read(128)

        return "allowed" if content else "empty"

    except OSError as exc:

        return f"denied:{exc.__class__.__name__}"





def _try_write(path: str) -> str:

    try:

        Path(path).write_text("probe", encoding="utf-8")

        return "allowed"

    except OSError as exc:

        return f"denied:{exc.__class__.__name__}"





def _probe_network_targets() -> dict[str, str]:

    results: dict[str, str] = {}

    targets = (

        ("127.0.0.1:80", ("127.0.0.1", 80)),

        ("localhost:443", ("localhost", 443)),

        ("backend:5432", ("backend", 5432)),

        ("postgres:5432", ("postgres", 5432)),

        ("redis:6379", ("redis", 6379)),

        ("8.8.8.8:53", ("8.8.8.8", 53)),

    )

    for label, (host, port) in targets:

        try:

            socket.create_connection((host, port), timeout=1)

            results[label] = "allowed"

        except OSError as exc:

            results[label] = f"denied:{exc.__class__.__name__}"

    try:

        socket.getaddrinfo("example.com", 443)

        results["dns"] = "allowed"

    except OSError as exc:

        results["dns"] = f"denied:{exc.__class__.__name__}"

    return results





def _probe_caps() -> dict[str, str]:

    status = _try_read("/proc/self/status")

    if status.startswith("denied"):

        return {"caps": status}

    try:

        text = Path("/proc/self/status").read_text(encoding="utf-8", errors="ignore")

        for line in text.splitlines():

            if line.startswith("CapEff:"):

                eff = line.split(":", 1)[1].strip()

                return {"CapEff": eff, "caps_none": "yes" if eff in {"0", "0000000000000000"} else "no"}

    except OSError as exc:

        return {"caps": f"denied:{exc.__class__.__name__}"}

    return {"caps": "unknown"}





def _probe_privesc() -> dict[str, str]:

    results: dict[str, str] = {}

    for name, cmd in (

        ("setuid", ["python3", "-c", "import os; os.setuid(0)"]),

        ("setgid", ["python3", "-c", "import os; os.setgid(0)"]),

        ("mount", ["mount", "-t", "tmpfs", "none", "/tmp/emic-mount-probe"]),

        ("ptrace", ["python3", "-c", "import ctypes; libc=ctypes.CDLL('libc.so.6'); rc=libc.ptrace(16, 1, 0, 0); raise SystemExit(0 if rc == 0 else 1)"]),

        ("unshare", ["unshare", "--net", "true"]),

    ):

        try:

            completed = subprocess.run(cmd, check=False, capture_output=True, timeout=2)

            results[name] = "allowed" if completed.returncode == 0 else f"denied:exit:{completed.returncode}"

        except (OSError, subprocess.TimeoutExpired) as exc:

            results[name] = f"denied:{exc.__class__.__name__}"

    return results





def _probe_resource_abuse(kind: str) -> dict[str, str]:

    if kind == "fork":

        count = 0

        try:

            for _ in range(256):

                pid = os.fork()

                if pid == 0:

                    os._exit(0)

                count += 1

        except OSError as exc:

            return {"fork": f"stopped:{count}:{exc.__class__.__name__}"}

        return {"fork": f"allowed:{count}"}

    if kind == "fd":

        fds: list[int] = []

        try:

            for _ in range(512):

                fds.append(os.open("/dev/null", os.O_RDONLY))

        except OSError as exc:

            for fd in fds:

                try:

                    os.close(fd)

                except OSError:

                    pass

            return {"fd": f"stopped:{len(fds)}:{exc.__class__.__name__}"}

        for fd in fds:

            os.close(fd)

        return {"fd": f"allowed:{len(fds)}"}

    if kind == "memory":

        chunks: list[bytearray] = []

        try:

            for _ in range(512):

                chunks.append(bytearray(1024 * 1024))

        except MemoryError:

            return {"memory": f"stopped:{len(chunks)}MB"}

        return {"memory": f"allowed:{len(chunks)}MB"}

    if kind == "cpu":

        deadline = time.time() + 2.0

        spins = 0

        while time.time() < deadline:

            spins += 1

        return {"cpu_spin_2s": str(spins)}

    if kind == "disk":

        written = 0

        try:

            for i in range(1024):

                Path(f"/data/disk-probe-{i}.bin").write_bytes(b"x" * 1024)

                written += 1

        except OSError as exc:

            return {"disk": f"stopped:{written}:{exc.__class__.__name__}"}

        return {"disk": f"allowed:{written}"}

    return {"resource": "unknown"}





class SandboxDemoRuntime:

    def __init__(self, ctx: dict) -> None:

        self._ctx = ctx

        self._mode = os.environ.get("EMIC_SANDBOX_MODE", "benign")

        self._started = False



    def _probe_broker_live(self) -> dict[str, str]:
        ctx = self._ctx
        session_token = str(ctx.get("session_token", ""))
        runtime_instance_id = str(ctx.get("runtime_instance_id", ""))
        module_id = str(ctx.get("module_id", ""))
        site_id = int(ctx.get("site_id", 1))
        rpc_socket = str(ctx.get("rpc_socket", ""))
        results: dict[str, str] = {}

        def rpc(method: str, params: dict) -> dict:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": {**params, "_session_token": session_token},
            }
            data = (json.dumps(payload) + "\n").encode("utf-8")
            if rpc_socket.startswith("tcp:"):
                _, host, port = rpc_socket.split(":", 2)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, int(port)))
            else:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(rpc_socket)
            try:
                sock.sendall(data)
                raw = sock.recv(65536).split(b"\n", 1)[0]
                response = json.loads(raw.decode("utf-8"))
            finally:
                sock.close()
            if "error" in response:
                err = response["error"]
                raise RuntimeError(str(err.get("message", "rpc error")))
            result = response.get("result")
            if not isinstance(result, dict):
                raise RuntimeError("invalid rpc result")
            return result

        base = {
            "runtime_instance_id": runtime_instance_id,
            "module_id": module_id,
            "site_id": site_id,
        }
        try:
            rpc("NetworkRequest", {**base, "url": os.environ.get("EMIC_BROKER_ALLOW_URL", "https://example.com/")})
            results["network_allow"] = "allowed"
        except Exception as exc:
            results["network_allow"] = f"denied:{exc.__class__.__name__}"
        try:
            rpc("NetworkRequest", {**base, "url": "https://evil-not-allowlisted.test/"})
            results["network_deny"] = "allowed"
        except Exception as exc:
            results["network_deny"] = f"denied:{exc.__class__.__name__}"
        try:
            rpc("GetSecret", {**base, "secret_ref": os.environ.get("EMIC_BROKER_OWN_SECRET", "own-test-secret")})
            results["secret_own"] = "allowed"
        except Exception as exc:
            results["secret_own"] = f"denied:{exc.__class__.__name__}"
        try:
            rpc("GetSecret", {**base, "secret_ref": "unrelated-secret"})
            results["secret_enum"] = "allowed"
        except Exception as exc:
            results["secret_enum"] = f"denied:{exc.__class__.__name__}"
        try:
            rpc("Read", {**base, "capability": "read_status", "params": {"site_id": site_id}})
            results["read_own_site"] = "allowed"
        except Exception as exc:
            results["read_own_site"] = f"denied:{exc.__class__.__name__}"
        try:
            rpc("Read", {**base, "capability": "read_status", "params": {"site_id": site_id + 99}})
            results["read_cross_site"] = "allowed"
        except Exception as exc:
            results["read_cross_site"] = f"denied:{exc.__class__.__name__}"
        return results



    def start(self) -> None:

        self._started = True

        if self._mode == "probe_filesystem":

            foreign = os.environ.get("EMIC_PROBE_FOREIGN_DATA", "/tmp/other-module-secret")

            _write_probes(

                {

                    "/etc/passwd": _try_read("/etc/passwd"),

                    "/etc/shadow": _try_read("/etc/shadow"),

                    "/home": _try_read("/home"),

                    "/root": _try_read("/root"),

                    "/proc/1/environ": _try_read("/proc/1/environ"),

                    "/proc/1/cmdline": _try_read("/proc/1/cmdline"),

                    "/var/run/docker.sock": _try_read("/var/run/docker.sock"),

                    "/package/manifest.json": _try_read("/package/manifest.json"),

                    "/package/manifest.json.write": _try_write("/package/manifest.json"),

                    "/data/probes.json.write": _try_write("/data/probes.json"),

                    "foreign_data": _try_read(foreign),

                    "tmp_private": _try_write("/tmp/emic-probe.txt"),

                }

            )

        elif self._mode == "probe_env":

            forbidden = (

                "DATABASE_URL",

                "REDIS_URL",

                "EMIC_ADMIN_TOKEN",

                "HEARTBEAT_API_KEY",

                "CHARGEAMPS_PASSWORD",

                "POSTGRES_PASSWORD",

                "SSH_AUTH_SOCK",

                "MERCEDES_PASSWORD",

            )

            present = {key: ("present" if os.environ.get(key) else "absent") for key in forbidden}

            _write_probes(present)

        elif self._mode == "probe_uid":

            _write_probes({"uid": str(os.getuid()), "euid": str(os.geteuid()), "gid": str(os.getgid())})

        elif self._mode == "probe_rlimits":

            results: dict[str, str] = {}

            for name in ("AS", "NPROC", "NOFILE", "CPU"):

                attr = f"RLIMIT_{name}"

                if not hasattr(resource, attr):

                    continue

                soft, hard = resource.getrlimit(getattr(resource, attr))

                results[name] = f"{soft}:{hard}"

            _write_probes(results)

        elif self._mode == "probe_caps":

            _write_probes(_probe_caps())

        elif self._mode == "probe_network_full":

            _write_probes(_probe_network_targets())

        elif self._mode == "probe_privesc":

            _write_probes(_probe_privesc())

        elif self._mode == "probe_fork":

            _write_probes(_probe_resource_abuse("fork"))

        elif self._mode == "probe_fd":

            _write_probes(_probe_resource_abuse("fd"))

        elif self._mode == "probe_memory":

            _write_probes(_probe_resource_abuse("memory"))

        elif self._mode == "probe_cpu":

            _write_probes(_probe_resource_abuse("cpu"))

        elif self._mode == "probe_disk":

            _write_probes(_probe_resource_abuse("disk"))

        elif self._mode == "evil_read_etc":

            _write_probes({"/etc/passwd": _try_read("/etc/passwd")})

        elif self._mode == "evil_network":
            results = _probe_network_targets()
            if all(value.startswith("denied") for value in results.values()):
                _write_probes({"network": "denied:all"})
            else:
                allowed = next(key for key, value in results.items() if not value.startswith("denied"))
                _write_probes({"network": f"allowed:{allowed}"})

        elif self._mode == "evil_subprocess":

            try:

                completed = subprocess.run(["/bin/sh", "-c", "id"], check=False, capture_output=True, timeout=2)

                _write_probes({"subprocess": "allowed" if completed.returncode == 0 else f"exit:{completed.returncode}"})

            except OSError as exc:

                _write_probes({"subprocess": f"denied:{exc.__class__.__name__}"})

        elif self._mode == "evil_hang":

            _write_probes({"state": "hanging"})

        elif self._mode == "evil_crash":

            _write_probes({"state": "crashing"})

            os._exit(1)

        elif self._mode == "probe_broker_live":

            _write_probes(self._probe_broker_live())



    def tick(self) -> None:

        if self._mode == "evil_cpu":

            while True:

                pass

        if self._mode == "evil_hang":

            time.sleep(3600)



    def stop(self) -> None:

        self._started = False





def build_module(ctx: dict):

    return SandboxDemoRuntime(ctx)


