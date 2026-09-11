"use client";

import { useCallback, useEffect, useState } from "react";
import { ModulesDevicesNav } from "@/components/modules-devices/ModulesDevicesNav";
import { getAdminToken } from "@/lib/adminAuth";
import {
  fetchModuleRuntimes,
  fetchRuntimeAuthorizations,
  grantRuntimeAuthorization,
  ModuleRuntimeListResponse,
  revokeRuntimeAuthorization,
  RuntimeAuthorizationView,
} from "@/lib/api";

export function RuntimeIsolationPanel() {
  const [data, setData] = useState<ModuleRuntimeListResponse | null>(null);
  const [authorizations, setAuthorizations] = useState<RuntimeAuthorizationView[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [grantError, setGrantError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const token = getAdminToken();
    if (!token) {
      setError("Admin token required");
      return;
    }
    try {
      const [runtimeData, authData] = await Promise.all([
        fetchModuleRuntimes(),
        fetchRuntimeAuthorizations(),
      ]);
      setData(runtimeData);
      setAuthorizations(authData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load runtime data");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function handleRevoke(authId: number) {
    try {
      await revokeRuntimeAuthorization(authId);
      await reload();
    } catch (err) {
      setGrantError(err instanceof Error ? err.message : "Revoke failed");
    }
  }

  return (
    <div data-testid="runtime-isolation-panel">
      <ModulesDevicesNav />
      <h2>Runtime Isolation</h2>
      {error ? <p role="alert">{error}</p> : null}
      {grantError ? <p role="alert">{grantError}</p> : null}
      {data ? (
        <>
          <p>{data.message}</p>
          <p data-testid="runtime-global-blocked">Global runtime blocked: {String(data.runtime_blocked)}</p>
          <p data-testid="runtime-selective-auth">
            Selective authorizations: {data.active_authorizations ?? 0}
          </p>
          <table>
            <thead>
              <tr>
                <th>Module</th>
                <th>Site</th>
                <th>State</th>
                <th>Digest</th>
              </tr>
            </thead>
            <tbody>
              {data.runtimes.map((runtime) => (
                <tr key={runtime.runtime_instance_id}>
                  <td>{runtime.module_id}</td>
                  <td>{runtime.site_id}</td>
                  <td>{runtime.state}</td>
                  <td>{runtime.artifact_sha256.slice(0, 12)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}

      <section data-testid="runtime-authorizations">
        <h3>Pilot Authorizations</h3>
        <p>Exact module identity required — no wildcards.</p>
        <table>
          <thead>
            <tr>
              <th>Module</th>
              <th>Version</th>
              <th>Site</th>
              <th>Publisher</th>
              <th>Expires</th>
              <th>Active</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {authorizations.map((auth) => (
              <tr key={auth.id} data-testid={`auth-row-${auth.id}`}>
                <td>{auth.module_id}</td>
                <td>{auth.version}</td>
                <td>{auth.site_id}</td>
                <td>{auth.publisher_id}</td>
                <td>{auth.expires_at.slice(0, 10)}</td>
                <td>{String(auth.active)}</td>
                <td>
                  {auth.active ? (
                    <button type="button" onClick={() => void handleRevoke(auth.id)}>
                      Revoke
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

export async function grantRuntimeAuthorizationFromForm(
  body: Parameters<typeof grantRuntimeAuthorization>[0],
): Promise<RuntimeAuthorizationView> {
  return grantRuntimeAuthorization(body);
}
