import type { SpaStatus } from "@/lib/api";
import { SPA_TUB_TOPDOWN } from "@/lib/spaScenePhoto";
import { SpaComponentCard } from "./SpaComponentCard";
import { buildComponentRows, formatKwFromW } from "./spaDashboardHelpers";

export function SpaComponentsPanel({ status }: { status: SpaStatus }) {
  const rows = buildComponentRows(status);
  const pumps = rows.filter((row) => row.id.startsWith("pump"));
  const equipment = rows.filter((row) => !row.id.startsWith("pump"));
  const totalW = rows.reduce((sum, row) => sum + row.powerW, 0);

  return (
    <section className="sdash-panel sdash-components-panel">
      <h2 className="sdash-panel-title">KOMPONENTER</h2>
      <div className="sdash-components-stage">
        <ul className="sdash-components-col" aria-label="Pumpar">
          {pumps.map((row) => (
            <SpaComponentCard key={row.id} row={row} />
          ))}
        </ul>

        <div className="sdash-tub-stage" aria-hidden="true">
          <div className="sdash-tub-frame">
            <div className="sdash-tub-glow" />
            <img src={SPA_TUB_TOPDOWN} alt="" className="sdash-tub-photo" />
          </div>
          <div className="sdash-tub-total">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M13 2L4 14h7l-1 8 10-14h-7l0-6z"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinejoin="round"
              />
            </svg>
            <div>
              <span>Totalt just nu</span>
              <strong>{formatKwFromW(totalW)}</strong>
            </div>
          </div>
        </div>

        <ul className="sdash-components-col" aria-label="Utrustning">
          {equipment.map((row) => (
            <SpaComponentCard key={row.id} row={row} />
          ))}
        </ul>
      </div>
    </section>
  );
}
