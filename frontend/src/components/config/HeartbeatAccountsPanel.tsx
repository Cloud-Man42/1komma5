"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  HeartbeatAccount,
  HeartbeatAccountDiagnostics,
  HeartbeatConfig,
  HeartbeatDiscoveryResult,
  HeartbeatInstallation,
  createHeartbeatAccount,
  discoverHeartbeatAccount,
  fetchHeartbeatAccounts,
  fetchHeartbeatConfig,
  linkHeartbeatAccountSite,
  runHeartbeatAccountDiagnostics,
  saveHeartbeatConfig,
  testHeartbeatAccountConnection,
  updateHeartbeatAccount,
} from "@/lib/api";

const SITE_OPTIONS = [
  { slug: "akarp", label: "Åkarp" },
  { slug: "summer-house-denmark", label: "Bøsserup (Danmark)" },
];

type AccountForm = {
  slug: string;
  name: string;
  username: string;
  password: string;
};

const emptyForm = (): AccountForm => ({
  slug: "",
  name: "",
  username: "",
  password: "",
});

function formatDiagnostics(result: HeartbeatAccountDiagnostics): string {
  if (!result.token_ok) {
    return `Token fel: ${result.last_authentication_error ?? "okänd"}`;
  }
  const probes = result.probes ?? [];
  const probeSummary =
    probes.length > 0
      ? probes.map((p) => `${p.path}: ${p.ok ? "OK" : "fel"}`).join(", ")
      : "Token OK";
  const context = [
    result.api_url ? `API ${result.api_url}` : null,
    result.system_id ? `system ${result.system_id}` : null,
    result.gateway_id ? `gateway ${result.gateway_id}` : null,
    result.linked_sites.length ? `sites ${result.linked_sites.join(", ")}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
  return `${probeSummary}${context ? ` (${context})` : ""}`;
}

function installationLabel(inst: HeartbeatInstallation): string {
  return [
    inst.name,
    inst.serial_number ? `serial ${inst.serial_number}` : null,
    inst.system_id ? `system ${inst.system_id}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

export function HeartbeatAccountsPanel() {
  const [accounts, setAccounts] = useState<HeartbeatAccount[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [diagnostics, setDiagnostics] = useState<Record<number, string>>({});
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [form, setForm] = useState<AccountForm>(emptyForm());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [discovery, setDiscovery] = useState<HeartbeatDiscoveryResult | null>(null);
  const [linkAccountId, setLinkAccountId] = useState<number | null>(null);
  const [linkSiteSlug, setLinkSiteSlug] = useState(SITE_OPTIONS[0]?.slug ?? "");
  const [linkSerial, setLinkSerial] = useState("");
  const [selectedInstallation, setSelectedInstallation] = useState<HeartbeatInstallation | null>(null);
  const [pollConfig, setPollConfig] = useState<HeartbeatConfig | null>(null);
  const [pollInterval, setPollInterval] = useState(60);
  const [dashboardRefresh, setDashboardRefresh] = useState(30);
  const [savingPoll, setSavingPoll] = useState(false);

  const editingAccount = useMemo(
    () => accounts.find((account) => account.id === editingId) ?? null,
    [accounts, editingId],
  );

  const loadAccounts = useCallback(async () => {
    const loaded = await fetchHeartbeatAccounts();
    setAccounts(loaded);
  }, []);

  useEffect(() => {
    loadAccounts().catch((e) =>
      setError(e instanceof Error ? e.message : "Kunde inte ladda Heartbeat-konton"),
    );
    fetchHeartbeatConfig()
      .then((config) => {
        setPollConfig(config);
        setPollInterval(config.poll_interval_seconds);
        setDashboardRefresh(config.dashboard_refresh_seconds);
      })
      .catch(() => undefined);
  }, [loadAccounts]);

  const resetForm = () => {
    setForm(emptyForm());
    setEditingId(null);
    setDiscovery(null);
    setSelectedInstallation(null);
  };

  const startEdit = (account: HeartbeatAccount) => {
    setEditingId(account.id);
    setForm({
      slug: account.slug,
      name: account.name,
      username: "",
      password: "",
    });
    setLinkAccountId(account.id);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSaveMessage(null);

    const name = form.name.trim();
    const username = form.username.trim();
    if (!name) {
      setError("Kontonamn krävs.");
      setSaving(false);
      return;
    }
    if (!username) {
      setError("E-post krävs.");
      setSaving(false);
      return;
    }
    if (!editingAccount && !form.slug.trim()) {
      setError("Slug krävs för nya konton.");
      setSaving(false);
      return;
    }
    if (!editingAccount && !form.password.trim()) {
      setError("Lösenord krävs när kontot skapas.");
      setSaving(false);
      return;
    }

    try {
      if (editingAccount) {
        const payload: { name: string; username: string; password?: string } = { name, username };
        if (form.password.trim()) payload.password = form.password;
        await updateHeartbeatAccount(editingAccount.id, payload);
        setSaveMessage("Kontot uppdaterat.");
      } else {
        await createHeartbeatAccount({
          slug: form.slug.trim(),
          name,
          username,
          password: form.password.trim(),
        });
        setSaveMessage("Kontot skapat och inloggning testad.");
      }
      await loadAccounts();
      resetForm();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte spara kontot");
    } finally {
      setSaving(false);
    }
  };

  const runDiagnostics = async (accountId: number) => {
    setLoadingId(accountId);
    try {
      const result = await runHeartbeatAccountDiagnostics(accountId);
      setDiagnostics((current) => ({
        ...current,
        [accountId]: formatDiagnostics(result),
      }));
    } catch (e) {
      setDiagnostics((current) => ({
        ...current,
        [accountId]: e instanceof Error ? e.message : "Diagnostik misslyckades",
      }));
    } finally {
      setLoadingId(null);
    }
  };

  const runTestConnection = async (accountId: number) => {
    setLoadingId(accountId);
    try {
      const result = await testHeartbeatAccountConnection(accountId);
      setDiagnostics((current) => ({
        ...current,
        [accountId]: result.connected
          ? `Ansluten (${result.visible_installations} installationer)`
          : `Misslyckades: ${result.last_authentication_error ?? "okänd"}`,
      }));
      await loadAccounts();
    } catch (e) {
      setDiagnostics((current) => ({
        ...current,
        [accountId]: e instanceof Error ? e.message : "Test misslyckades",
      }));
    } finally {
      setLoadingId(null);
    }
  };

  const runDiscovery = async (accountId: number) => {
    setLoadingId(accountId);
    setDiscovery(null);
    try {
      const result = await discoverHeartbeatAccount(accountId, linkSerial.trim() || undefined);
      setDiscovery(result);
      setLinkAccountId(accountId);
      if (result.installations.length === 1) {
        setSelectedInstallation(result.installations[0] ?? null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Discovery misslyckades");
    } finally {
      setLoadingId(null);
    }
  };

  const handleLinkSite = async () => {
    if (!linkAccountId || !linkSiteSlug) return;
    setSaving(true);
    setError(null);
    try {
      const inst = selectedInstallation;
      await linkHeartbeatAccountSite(linkAccountId, {
        site_slug: linkSiteSlug,
        heartbeat_serial_number: linkSerial.trim() || inst?.serial_number || null,
        heartbeat_system_id: inst?.system_id || null,
        heartbeat_gateway_id: inst?.gateway_id || null,
        heartbeat_site_id: inst?.site_id || null,
        heartbeat_asset_id: inst?.asset_id || null,
        heartbeat_device_id: inst?.device_id || null,
      });
      setSaveMessage(`Kopplat konto till ${linkSiteSlug}.`);
      await loadAccounts();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte koppla site");
    } finally {
      setSaving(false);
    }
  };

  const savePollSettings = async () => {
    if (!pollConfig) return;
    setSavingPoll(true);
    try {
      const saved = await saveHeartbeatConfig({
        connection_type: pollConfig.connection_type,
        host: pollConfig.host,
        port: pollConfig.port,
        use_tls: pollConfig.use_tls,
        api_path: pollConfig.api_path,
        poll_interval_seconds: pollInterval,
        dashboard_refresh_seconds: dashboardRefresh,
        username: pollConfig.username,
        sites: pollConfig.sites,
      });
      setPollConfig(saved);
      setSaveMessage("Poll-intervall sparade.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kunde inte spara poll-intervall");
    } finally {
      setSavingPoll(false);
    }
  };

  return (
    <section className="config-card" data-testid="heartbeat-accounts-panel">
      <h3>Heartbeat-konton</h3>
      <p className="muted">
        Lägg till 1KOMMA5-konton med e-post och lösenord. EMIC hanterar token och session automatiskt.
      </p>

      <form onSubmit={handleSubmit} className="config-subcard" data-testid="heartbeat-account-form">
        <h4 className="config-section-title">{editingAccount ? "Redigera konto" : "Nytt konto"}</h4>
        <div className="form-grid">
          {!editingAccount && (
            <label className="form-field">
              <span>Slug</span>
              <input
                value={form.slug}
                onChange={(e) => setForm((current) => ({ ...current, slug: e.target.value }))}
                placeholder="akarp"
              />
            </label>
          )}
          <label className="form-field">
            <span>Kontonamn</span>
            <input
              value={form.name}
              onChange={(e) => setForm((current) => ({ ...current, name: e.target.value }))}
              placeholder="Åkarp"
            />
          </label>
          <label className="form-field">
            <span>E-post</span>
            <input
              type="email"
              autoComplete="username"
              value={form.username}
              onChange={(e) => setForm((current) => ({ ...current, username: e.target.value }))}
              placeholder={editingAccount?.username_masked ?? "user@example.com"}
            />
          </label>
          <label className="form-field">
            <span>Lösenord</span>
            <input
              type="password"
              autoComplete={editingAccount ? "new-password" : "current-password"}
              value={form.password}
              onChange={(e) => setForm((current) => ({ ...current, password: e.target.value }))}
              placeholder={editingAccount?.password_configured ? "••••••••" : "Lösenord"}
            />
          </label>
        </div>
        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Sparar…" : editingAccount ? "Uppdatera konto" : "Skapa konto"}
          </button>
          {editingAccount && (
            <button type="button" className="btn-secondary" onClick={resetForm}>
              Avbryt
            </button>
          )}
        </div>
      </form>

      <div className="config-subcard" data-testid="heartbeat-link-form">
        <h4 className="config-section-title">Koppla installation till EMIC-site</h4>
        <div className="form-grid">
          <label className="form-field">
            <span>Konto</span>
            <select
              value={linkAccountId ?? ""}
              onChange={(e) => setLinkAccountId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Välj konto</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>EMIC-site</span>
            <select value={linkSiteSlug} onChange={(e) => setLinkSiteSlug(e.target.value)}>
              {SITE_OPTIONS.map((site) => (
                <option key={site.slug} value={site.slug}>
                  {site.label}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field form-field-wide">
            <span>Serienummer (valfritt)</span>
            <input
              value={linkSerial}
              onChange={(e) => setLinkSerial(e.target.value)}
              placeholder="K183-600-000-021-000-P-X"
            />
          </label>
        </div>
        <div className="form-actions">
          <button
            type="button"
            className="btn-secondary"
            disabled={!linkAccountId || loadingId === linkAccountId}
            onClick={() => linkAccountId && runDiscovery(linkAccountId)}
          >
            {loadingId === linkAccountId ? "Söker…" : "Discover"}
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={!linkAccountId || saving}
            onClick={handleLinkSite}
          >
            Koppla site
          </button>
        </div>
        {discovery && (
          <div className="config-subcard">
            <p className="muted">
              Hittade {discovery.installations.length} installation(er) via {discovery.paths_probed.join(", ")}
            </p>
            <ul className="config-list">
              {discovery.installations.map((inst, index) => (
                <li key={`${inst.system_id ?? index}`} className="config-list-item">
                  <label>
                    <input
                      type="radio"
                      name="installation"
                      checked={selectedInstallation === inst}
                      onChange={() => setSelectedInstallation(inst)}
                    />
                    {installationLabel(inst) || `Installation ${index + 1}`}
                  </label>
                </li>
              ))}
            </ul>
            {discovery.serial_matches.map((match) => (
              <p key={match.serial} className="muted">
                Serial {match.serial}: {match.found ? "FOUND" : "NOT FOUND"}
                {match.resolved_system_id ? ` → system ${match.resolved_system_id}` : ""}
              </p>
            ))}
          </div>
        )}
      </div>

      {pollConfig && (
        <div className="config-subcard">
          <h4 className="config-section-title">Avancerat — poll-intervall</h4>
          <div className="form-grid">
            <label className="form-field">
              <span>Collector poll (sek)</span>
              <input
                type="number"
                min={5}
                max={3600}
                value={pollInterval}
                onChange={(e) => setPollInterval(Number(e.target.value))}
              />
            </label>
            <label className="form-field">
              <span>Dashboard refresh (sek)</span>
              <input
                type="number"
                min={1}
                max={30}
                value={dashboardRefresh}
                onChange={(e) => setDashboardRefresh(Number(e.target.value))}
              />
            </label>
          </div>
          <button type="button" className="btn-secondary" disabled={savingPoll} onClick={savePollSettings}>
            {savingPoll ? "Sparar…" : "Spara intervall"}
          </button>
        </div>
      )}

      {error && <p className="error-text">{error}</p>}
      {saveMessage && <p className="form-success">{saveMessage}</p>}

      {accounts.length === 0 && !error && <p className="muted">Inga konton konfigurerade ännu.</p>}
      <ul className="config-list">
        {accounts.map((account) => (
          <li key={account.id} className="config-list-item">
            <div>
              <strong>{account.name}</strong> ({account.slug})
              <div className="muted">
                {account.status} · {account.username_masked || "—"} ·{" "}
                {account.is_enabled ? "aktivt" : "inaktiverat"}
                {account.password_configured ? " · lösenord sparat" : ""}
                {account.linked_sites.length ? ` · sites: ${account.linked_sites.join(", ")}` : ""}
              </div>
              <div className="muted">{account.api_url ?? "—"}</div>
              {account.last_authentication_error && (
                <div className="error-text">{account.last_authentication_error}</div>
              )}
              {diagnostics[account.id] && <div className="muted">{diagnostics[account.id]}</div>}
            </div>
            <div className="form-actions">
              <button type="button" className="btn-secondary" onClick={() => startEdit(account)}>
                Redigera
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={loadingId === account.id}
                onClick={() => runTestConnection(account.id)}
              >
                Test
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={loadingId === account.id}
                onClick={() => runDiagnostics(account.id)}
              >
                {loadingId === account.id ? "Kör…" : "Diagnostik"}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
