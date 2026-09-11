"use client";



import { useState } from "react";

import { getApiBaseUrl } from "@/lib/api";

import { adminAuthHeaders, adminFetch } from "@/lib/adminAuth";

import { ApiRequestError, formatDependencyConflict, parseApiError } from "@/lib/apiError";



type Props = {

  siteSlug: string;

  moduleId: string;

  enabled: boolean;

  canDisable?: boolean;

  moduleNames?: Record<string, string>;

  onChanged: () => void;

};



export function EnableDisableControl({

  siteSlug,

  moduleId,

  enabled,

  canDisable = true,

  moduleNames,

  onChanged,

}: Props) {

  const [busy, setBusy] = useState(false);

  const [conflict, setConflict] = useState<string | null>(null);



  async function toggle() {

    setBusy(true);

    setConflict(null);

    try {

      const res = await adminFetch(`${getApiBaseUrl()}/api/sites/${siteSlug}/modules/${moduleId}`, {

        method: "PUT",

        headers: { ...adminAuthHeaders(), "Content-Type": "application/json" },

        body: JSON.stringify({ enabled: !enabled }),

      });

      if (!res.ok) throw await parseApiError(res);

      onChanged();

    } catch (err) {

      if (err instanceof ApiRequestError) {

        setConflict(formatDependencyConflict(err.detail, moduleNames));

      } else {

        setConflict(err instanceof Error ? err.message : "Kunde inte uppdatera modul");

      }

    } finally {

      setBusy(false);

    }

  }



  if (!canDisable && enabled) {

    return <span className="muted">Kärnmodul</span>;

  }



  return (

    <div>

      <button

        type="button"

        className="config-button-secondary"

        disabled={busy}

        onClick={() => void toggle()}

      >

        {enabled ? "Inaktivera" : "Aktivera"}

      </button>

      {conflict ? <p className="config-error-inline" role="alert" style={{ whiteSpace: "pre-line" }}>{conflict}</p> : null}

    </div>

  );

}

