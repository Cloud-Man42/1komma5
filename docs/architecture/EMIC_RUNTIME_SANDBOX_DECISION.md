# EMIC Runtime Sandbox Decision

## Production (Linux collector)

**bubblewrap (`bwrap`) + layered hardening**

| Layer | Mechanism |
|-------|-----------|
| Process boundary | `python -I [-s] isolated_runtime_bootstrap.py` in dedicated worker |
| OS sandbox | `bwrap --unshare-net --unshare-pid --die-with-parent --new-session --cap-drop ALL` |
| Filesystem | `--ro-bind` verified package; `--bind` module data dir; `--tmpfs /tmp` |
| Identity | Dedicated `emic-module` UID/GID (10001) in collector image |
| Network | Default deny (`--unshare-net`); brokered HTTP via `NetworkBroker` + `url_policy` |
| Resources | Configurable memory/CPU/RPC limits; Linux prlimit/cgroups in hard-security CI |

## Windows development

- `SubprocessSandboxLauncher` + TCP localhost RPC (functional tests only)
- **Not** production security proof; OS-level isolation tests are `@pytest.mark.integration` and skipped on Windows

## Non-goals

- No Docker socket or nested containers for modules
- No unrestricted runtime start API while gate closed
