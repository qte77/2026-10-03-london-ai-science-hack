import { safeUrl } from "../lib/safeUrl.js";

function Skipped({ reason }) {
  return <p className="status-skipped">skipped: {reason}</p>;
}

export function ValidationPanel({ suite, kpiRobustness, agents, papers }) {
  return (
    <section aria-label="Validation">
      <div className="section-head">
        <h2>
          <span className="num">06</span>Validation
        </h2>
      </div>
      <div className="panel-grid">
        <div className="tile">
          <h3>Held-out suite</h3>
          {suite ? (
            <div className="kv-list">
              <div>
                <span>chosen_k</span>
                <span>{suite.chosen_k}</span>
              </div>
              <div>
                <span>held-out accuracy</span>
                <span>{(suite.heldout_accuracy * 100).toFixed(1)}%</span>
              </div>
              <div>
                <span>items scored</span>
                <span>{Object.keys(suite.items ?? {}).length}</span>
              </div>
            </div>
          ) : (
            <Skipped reason="no suite run recorded" />
          )}
        </div>

        <div className="tile">
          <h3>KPI robustness</h3>
          {kpiRobustness && !kpiRobustness.status ? (
            <div className="kv-list">
              {Object.entries(kpiRobustness).map(([kpi, v]) => (
                <div key={kpi}>
                  <span>{kpi}</span>
                  <span>
                    imaging {v.imaging_shift} · material {v.material_shift}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <Skipped reason={kpiRobustness?.reason ?? "no data"} />
          )}
        </div>

        <div className="tile">
          <h3>Agents</h3>
          {agents?.status === "skipped" || !agents?.configs ? (
            <Skipped reason={agents?.reason ?? "no data"} />
          ) : (
            <div className="kv-list">
              {Object.entries(agents.configs).map(([name, c]) => (
                <div key={name}>
                  <span>{name}</span>
                  <span>
                    n={c.n} · acc={(c.accuracy * 100).toFixed(0)}% · trips={c.trips}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="tile">
          <h3>Papers</h3>
          {papers?.status === "skipped" || !papers?.hits ? (
            <Skipped reason={papers?.reason ?? "no data"} />
          ) : (
            <ul>
              {papers.hits.map((h) => (
                <li key={h.id}>
                  {safeUrl(h.url) ? (
                    <a href={safeUrl(h.url)} rel="noopener noreferrer">
                      {h.title}
                    </a>
                  ) : (
                    h.title
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
