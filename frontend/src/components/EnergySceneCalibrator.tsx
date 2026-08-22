"use client";



import { useCallback, useState } from "react";

import { EnergySceneCanvas } from "@/components/EnergySceneCanvas";

import { EQUIPMENT_PICKER_OPTIONS } from "@/components/EnergyEquipmentOverlay";

import {

  SCENE_WIRE_IDS,

  WIRE_COLORS,

  WIRE_LABELS,

  buildExportJson,

  buildSpecSnippet,

  clonePaths,

  type CalibratorPaths,

} from "@/lib/energySceneCalibrator";

import { DEFAULT_SCENE_PHOTO } from "@/lib/energyScenePhoto";

import { cropPhotoToScene } from "@/lib/energyScenePhoto";

import type { ScenePoint, SceneWireId } from "@/lib/energyFlowSceneLayout";

import { useEnergySceneConfig } from "@/lib/useEnergySceneConfig";

import type { EquipmentVariants } from "@/lib/energySceneEquipment";



function downloadText(filename: string, content: string, mime = "text/plain") {

  const blob = new Blob([content], { type: mime });

  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");

  anchor.href = url;

  anchor.download = filename;

  anchor.click();

  URL.revokeObjectURL(url);

}



interface EnergySceneCalibratorProps {

  siteSlug?: string;

}



function formatSavedAt(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("sv-SE", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

export function EnergySceneCalibrator({ siteSlug = "default" }: EnergySceneCalibratorProps) {

  const { config, patchConfig, updatePaths, resetConfig, ready } = useEnergySceneConfig(siteSlug);

  const [editMode, setEditMode] = useState(true);

  const [activeWire, setActiveWire] = useState<SceneWireId>("solar-inverter");

  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  const [showPreview, setShowPreview] = useState(true);

  const [copyStatus, setCopyStatus] = useState<string | null>(null);

  const [photoStatus, setPhotoStatus] = useState<string | null>(null);



  const paths = config.paths;



  const setPaths = useCallback(
    (updater: CalibratorPaths | ((current: CalibratorPaths) => CalibratorPaths)) => {
      updatePaths(updater);
    },
    [updatePaths],
  );



  const updatePoint = useCallback(

    (wire: SceneWireId, index: number, point: ScenePoint) => {

      setPaths((current) => {

        const next = clonePaths(current);

        next[wire][index] = point;

        return next;

      });

    },

    [setPaths],

  );



  const appendPoint = useCallback(

    (point: ScenePoint) => {

      setPaths((current) => {

        const next = clonePaths(current);

        next[activeWire] = [...next[activeWire], point];

        setSelectedIndex(next[activeWire].length - 1);

        return next;

      });

    },

    [activeWire, setPaths],

  );



  const undoLastPoint = () => {

    setPaths((current) => {

      const next = clonePaths(current);

      if (next[activeWire].length <= 2) return current;

      next[activeWire] = next[activeWire].slice(0, -1);

      return next;

    });

    setSelectedIndex(null);

  };



  const clearWire = () => {

    setPaths((current) => {

      const next = clonePaths(current);

      next[activeWire] = [next[activeWire][0]];

      return next;

    });

    setSelectedIndex(0);

  };



  const removeSelectedPoint = () => {

    if (selectedIndex === null) return;

    setPaths((current) => {

      const wirePoints = current[activeWire];

      if (wirePoints.length <= 2) return current;

      const next = clonePaths(current);

      next[activeWire] = wirePoints.filter((_, index) => index !== selectedIndex);

      return next;

    });

    setSelectedIndex(null);

  };



  const exportJson = () => {

    downloadText(

      "energyFlowPaths.generated.json",

      JSON.stringify(buildExportJson(paths), null, 2),

      "application/json",

    );

  };



  const copySpec = async () => {

    const snippet = buildSpecSnippet(paths);

    await navigator.clipboard.writeText(snippet);

    setCopyStatus("Spec kopierad till urklipp");

    window.setTimeout(() => setCopyStatus(null), 2500);

  };



  const handlePhotoUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {

    const file = event.target.files?.[0];

    if (!file) return;

    try {

      const dataUrl = await cropPhotoToScene(file);

      patchConfig({ photoUrl: dataUrl });

      setPhotoStatus("Egen bild uppladdad (beskuren till 3:2)");

    } catch {

      setPhotoStatus("Kunde inte ladda bilden");

    }

    window.setTimeout(() => setPhotoStatus(null), 3000);

    event.target.value = "";

  };



  const setEquipmentVariant = <K extends keyof EquipmentVariants>(

    key: K,

    value: EquipmentVariants[K],

  ) => {

    patchConfig({ equipment: { ...config.equipment, [key]: value } });

  };



  const activePoints = paths[activeWire];

  const canUndo = activePoints.length > 2;



  return (

    <div className="calibrator">

      <aside className="calibrator-sidebar">

        {ready ? (
          <p className="calibrator-save-status">
            Sparas automatiskt i webbläsaren och används överallt — dashboard, site-sidor och
            animationer delar samma kalibrering.
            {config.updatedAt ? (
              <span className="calibrator-save-time">
                {" "}
                Senast sparad {formatSavedAt(config.updatedAt)}.
              </span>
            ) : null}
          </p>
        ) : (
          <p className="calibrator-save-status">Laddar sparad kalibrering…</p>
        )}

        <div className="calibrator-mode-bar">

          <button

            type="button"

            className={`calibrator-mode-btn ${!editMode ? "calibrator-mode-btn-active" : ""}`}

            onClick={() => setEditMode(false)}

          >

            Visningsläge

          </button>

          <button

            type="button"

            className={`calibrator-mode-btn ${editMode ? "calibrator-mode-btn-active" : ""}`}

            onClick={() => setEditMode(true)}

          >

            Redigeringsläge

          </button>

        </div>



        <div className="calibrator-section">

          <h2 className="calibrator-title">Bakgrundsbild</h2>

          <label className="calibrator-file-input">

            <span>Ladda upp egen husfacad</span>

            <input type="file" accept="image/*" onChange={(event) => void handlePhotoUpload(event)} />

          </label>

          <button

            type="button"

            className="calibrator-btn-muted"

            onClick={() => patchConfig({ photoUrl: DEFAULT_SCENE_PHOTO })}

          >

            Återställ standardbild

          </button>

          {photoStatus ? <p className="calibrator-status">{photoStatus}</p> : null}

        </div>



        <div className="calibrator-section">

          <h2 className="calibrator-title">Utrustning</h2>

          <label className="calibrator-toggle">
            <input
              type="checkbox"
              checked={config.showEquipmentOverlay}
              onChange={(event) => patchConfig({ showEquipmentOverlay: event.target.checked })}
            />
            Visa utrustning i scenen
          </label>
          <p className="calibrator-help">
            Stäng av om ditt foto redan visar solpaneler, växelriktare och batteri.
          </p>

          {(Object.keys(EQUIPMENT_PICKER_OPTIONS) as Array<keyof EquipmentVariants>).map((type) => (

            <label
              key={type}
              className={`calibrator-select-row ${config.showEquipmentOverlay ? "" : "calibrator-select-row-disabled"}`}
            >

              <span>

                {type === "solar" ? "Solpaneler" : type === "inverter" ? "Växelriktare" : "Batteri"}

              </span>

              <select

                value={config.equipment[type]}

                disabled={!config.showEquipmentOverlay}

                onChange={(event) =>

                  setEquipmentVariant(type, event.target.value as EquipmentVariants[typeof type])

                }

              >

                {EQUIPMENT_PICKER_OPTIONS[type].map((option) => (

                  <option key={option.id} value={option.id}>

                    {option.label}

                  </option>

                ))}

              </select>

            </label>

          ))}

        </div>



        {editMode ? (
          ready ? (
          <>
            <h2 className="calibrator-title">Kablar</h2>

            <p className="calibrator-help">

              Välj kabel, klicka på bilden för att lägga till waypoints. Dra punkter för att justera.

            </p>



            <div className="calibrator-wire-list">

              {SCENE_WIRE_IDS.map((id) => (

                <button

                  key={id}

                  type="button"

                  className={`calibrator-wire-btn ${activeWire === id ? "calibrator-wire-btn-active" : ""}`}

                  style={{ "--wire-color": WIRE_COLORS[id] } as React.CSSProperties}

                  onClick={() => {

                    setActiveWire(id);

                    setSelectedIndex(null);

                  }}

                >

                  <span className="calibrator-wire-dot" />

                  {WIRE_LABELS[id]}

                  <span className="calibrator-wire-count">{paths[id].length} pkt</span>

                </button>

              ))}

            </div>



            <div className="calibrator-actions">

              <button type="button" onClick={undoLastPoint} disabled={!canUndo}>

                Ångra sista punkt

              </button>

              <button

                type="button"

                onClick={removeSelectedPoint}

                disabled={selectedIndex === null || !canUndo}

              >

                Ta bort vald punkt

              </button>

              <button type="button" onClick={clearWire} disabled={activePoints.length <= 1}>

                Rensa kabel

              </button>

              <button type="button" className="calibrator-btn-muted" onClick={resetConfig}>

                Återställ allt

              </button>

            </div>



            <div className="calibrator-points">

              <h3>Aktiva punkter</h3>

              <ol>

                {activePoints.map((point, index) => (

                  <li key={`${activeWire}-${index}`}>

                    <button

                      type="button"

                      className={selectedIndex === index ? "calibrator-point-selected" : ""}

                      onClick={() => setSelectedIndex(index)}

                    >

                      {index + 1}. x={point.x}, y={point.y}

                    </button>

                  </li>

                ))}

              </ol>

            </div>



            <div className="calibrator-export">

              <h3>Exportera (valfritt)</h3>

              <p className="calibrator-export-note">
                Waypoints sparas redan automatiskt. Exportera bara om du vill checka in ändringar i
                kodbasen.
              </p>

              <button type="button" onClick={exportJson}>

                Ladda ner JSON

              </button>

              <button type="button" onClick={() => void copySpec()}>

                Kopiera spec-snippet

              </button>

              {copyStatus ? <p className="calibrator-status">{copyStatus}</p> : null}

            </div>



            <label className="calibrator-toggle">

              <input

                type="checkbox"

                checked={showPreview}

                onChange={(event) => setShowPreview(event.target.checked)}

              />

              Visa glöd-preview på kablar

            </label>

          </>
          ) : (
            <p className="calibrator-help">Laddar sparad kalibrering…</p>
          )

        ) : (

          <p className="calibrator-help">

            Visningsläge — kablar och utrustning visas utan redigeringshandtag. Växla till

            redigeringsläge för att justera waypoints.

          </p>

        )}

      </aside>



      <div className="calibrator-scene-wrap">

        {!ready ? (
          <div className="energy-flow-loading calibrator-scene-loading">Laddar scen…</div>
        ) : (
        <EnergySceneCanvas

          photoUrl={config.photoUrl}

          paths={paths}

          equipment={config.equipment}

          showEquipment={config.showEquipmentOverlay}

          editMode={editMode}
          showWireGuides={!editMode && showPreview}

          activeWire={activeWire}

          selectedIndex={selectedIndex}

          showWirePreview={showPreview}

          onCanvasClick={appendPoint}

          onPointMove={updatePoint}

          onPointSelect={(wire, index) => {

            setActiveWire(wire);

            setSelectedIndex(index);

          }}

          ariaLabel="Kalibreringsyta för energikablar"

        />
        )}

      </div>

    </div>

  );

}


