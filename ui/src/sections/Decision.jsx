import { decisionStats, findCounterfactual, findFactValue, heroBlock, toneForState } from "../lib/brief.js";

function fmtP(p) {
  return typeof p === "number" ? p.toFixed(3) : "—";
}

export function DecisionSlab({ brief }) {
  const block = heroBlock(brief, "decision");
  const stats = decisionStats(brief);
  const counterfactual = findCounterfactual(brief);
  const tone = toneForState(block?.state);

  return (
    <section aria-label="Decision">
      <div className="decision-grid">
        <div className={`tile verdict-tile t-${tone}`} style={{ "--tone": `var(--${tone})` }}>
          <div className="verdict-eyebrow">
            {block?.title ?? "DECISION"} · {brief?.source?.batch} vs {brief?.source?.reference}
          </div>
          <div className="verdict-word">{block?.state ?? "—"}</div>
          {stats.headline && <p className="verdict-headline">{stats.headline}</p>}
          {stats.fact && <p className="verdict-fact">{stats.fact}</p>}
          {counterfactual && (
            <div className="counterfactual">
              Remove {counterfactual.entity} → {counterfactual.verdict} (p = {fmtP(counterfactual.p)})
            </div>
          )}
          {stats.scope && <div className="verdict-footer">SCOPE · {stats.scope}</div>}
        </div>
        <div className="tile">
          <div className="verdict-eyebrow">Batch p-value (from the brief)</div>
          <div className="verdict-word" style={{ fontSize: "clamp(32px,5vw,72px)" }}>
            {fmtP(stats.p)}
          </div>
          <p className="verdict-fact">vs α = {stats.alpha ?? "—"}</p>
          {stats.rule && <p className="sub-label">{stats.rule}</p>}
        </div>
      </div>
    </section>
  );
}

export function ReadoutsStrip({ brief, hackbench }) {
  const supportQc = heroBlock(brief, "data_support")?.items?.find((c) => c.id === "support.qc");
  const evidenceSummary = heroBlock(brief, "surviving_evidence")?.items?.find(
    (c) => c.id === "evidence.summary",
  );
  const nIndependent = supportQc ? findFactValue(supportQc, "n_independent") : undefined;
  const nSurviving = evidenceSummary ? findFactValue(evidenceSummary, "n_surviving") : undefined;
  const nDeviating = evidenceSummary ? findFactValue(evidenceSummary, "n_deviating") : undefined;

  const tiles = [
    nIndependent !== undefined && {
      label: "Independent micrographs",
      value: nIndependent,
      note: "parallax · support.qc",
    },
    nSurviving !== undefined && {
      label: "Surviving deviations",
      value: `${nSurviving}/${nDeviating ?? "—"}`,
      note: "parallax · evidence.summary",
    },
    hackbench && {
      label: "Driving KPIs (HackBench)",
      value: hackbench.driving?.length ?? 0,
      note: hackbench.driving?.join(", ") || "none",
    },
    hackbench && {
      label: "Fields of view (HackBench)",
      value: hackbench.n_fov,
      note: "n_fov",
    },
  ].filter(Boolean);

  if (tiles.length === 0) return null;

  return (
    <section aria-label="Key readouts">
      <div className="readouts">
        {tiles.map((t) => (
          <div className="readout" key={t.label}>
            <div className="readout-label">{t.label}</div>
            <div className="readout-value">{t.value}</div>
            <div className="readout-note">{t.note}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
