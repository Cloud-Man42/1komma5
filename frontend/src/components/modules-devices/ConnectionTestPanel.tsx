import type { ConnectionTestResult } from "@/lib/api";

type Props = {
  result: ConnectionTestResult;
};

export function ConnectionTestPanel({ result }: Props) {
  return (
    <div className="config-panel" data-testid="connection-test-panel">
      <p className={result.success ? "config-success" : "config-error"}>{result.message}</p>
      {result.latency_ms != null ? <p className="muted">Svarstid: {result.latency_ms} ms</p> : null}
      {result.capabilities.length ? (
        <ul>
          {result.capabilities.map((cap) => (
            <li key={cap.name}>
              {cap.name} ({cap.kind}) — {cap.available ? "tillgänglig" : "ej tillgänglig"}
            </li>
          ))}
        </ul>
      ) : null}
      {result.devices_found.length ? (
        <div>
          <h3>Hittade enheter</h3>
          <ul>
            {result.devices_found.map((device) => (
              <li key={device.external_id}>{device.name} ({device.device_type})</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
