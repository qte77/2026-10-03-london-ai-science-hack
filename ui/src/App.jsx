import { useEffect, useMemo, useState } from "react";
import ThemeSwitcher from "./ThemeSwitcher.jsx";
import { loadResults } from "./lib/fetchResults.js";
import { DecisionSlab, ReadoutsStrip } from "./sections/Decision.jsx";
import { KpiMatrix } from "./sections/KpiMatrix.jsx";
import { SupportAndLimits, NextCapture } from "./sections/BriefPanels.jsx";
import { HackbenchStrip } from "./sections/Hackbench.jsx";
import { ValidationPanel } from "./sections/Validation.jsx";
import { InfraPanel } from "./sections/Infra.jsx";
import { AppFooter } from "./sections/Footer.jsx";

function readInitialBatch(batchIds) {
  const fromUrl = new URLSearchParams(location.search).get("batch");
  return fromUrl && batchIds.includes(fromUrl) ? fromUrl : batchIds[0];
}

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [batchId, setBatchId] = useState(null);

  useEffect(() => {
    loadResults()
      .then((d) => {
        setData(d);
        const ids = Object.keys(d.batches ?? {});
        setBatchId(readInitialBatch(ids));
      })
      .catch((err) => setError(err.message ?? String(err)));
  }, []);

  const batchIds = useMemo(() => Object.keys(data?.batches ?? {}), [data]);

  function selectBatch(id) {
    setBatchId(id);
    const url = new URL(location.href);
    url.searchParams.set("batch", id);
    history.replaceState(null, "", url);
  }

  if (error) {
    return (
      <div className="page">
        <div className="error-state" role="alert">
          Could not load evidence: {error}
        </div>
      </div>
    );
  }

  if (!data || !batchId) {
    return (
      <div className="page">
        <p className="sub-label">Loading…</p>
      </div>
    );
  }

  const batch = data.batches[batchId];

  return (
    <div className="page">
      <header className="rail">
        <div className="brand">
          <div className="brand-mark">HB</div>
          <div>
            <div className="brand-eyebrow">POLARON · HACKBENCH</div>
            <h1 className="brand-title">ELECTRODE BATCH QC</h1>
          </div>
        </div>
        <div className="rail-controls">
          <label>
            BATCH{" "}
            <select value={batchId} onChange={(e) => selectBatch(e.target.value)}>
              {batchIds.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </label>
          <ThemeSwitcher />
        </div>
      </header>

      <DecisionSlab brief={batch.parallax_brief} />
      <ReadoutsStrip brief={batch.parallax_brief} hackbench={batch.hackbench} />
      <KpiMatrix hackbench={batch.hackbench} />
      <SupportAndLimits brief={batch.parallax_brief} />
      <NextCapture brief={batch.parallax_brief} />
      <HackbenchStrip
        batchId={batchId}
        hackbench={batch.hackbench}
        agree={batch.agree}
        parallaxState={batch.parallax_brief?.hero?.decision?.state}
      />
      <ValidationPanel
        suite={data.suite}
        kpiRobustness={data.kpi_robustness}
        agents={data.agents}
        papers={data.papers}
      />
      <InfraPanel cycle={data.cycle} prereg={data.prereg} />
      <AppFooter commit={data.commit} generatedAt={data.generated_at} />
    </div>
  );
}
