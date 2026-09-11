# Manifest

Required fields match `module-manifest.schema.json`. Module IDs use dotted lowercase identifiers (`integration.demo`). Version is SemVer. `entrypoint` uses `module:callable` import path relative to `module/` on `sys.path` after restart.

## network_hosts

Optional list of HTTPS hostnames the module may reach through the **Network Broker** when running in an isolated worker. Hostnames only — no schemes, paths, or wildcards. EMIC provisions allow rules from this list at runtime start (see `RuntimeBrokerProvisioner`).

Example:

```json
"network_hosts": ["home.sensibo.com"]
```
