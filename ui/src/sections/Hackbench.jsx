function fmt(n, digits = 3) {
  return typeof n === "number" ? n.toFixed(digits) : "—";
}

export function HackbenchStrip({ batchId, hackbench, agree, parallaxState }) {
  if (!hackbench) {
    return (
      <section aria-label="Second method: HackBench" className="hackbench-strip">
        <h2 style={{ marginBottom: 8 }}>Second method: HackBench</h2>
        <p className="sub-label">
          {batchId} is the approved reference — no independent HackBench verdict is computed
          against itself.
        </p>
      </section>
    );
  }

  const drivingKpis = hackbench.driving ?? [];

  return (
    <section aria-label="Second method: HackBench" className="hackbench-strip">
      <h2 style={{ marginBottom: 8 }}>Second method: HackBench</h2>
      <p>
        HackBench verdict: <strong>{hackbench.verdict?.toUpperCase()}</strong> · n_fov ={" "}
        {hackbench.n_fov}
      </p>
      {drivingKpis.length > 0 && (
        <ul>
          {drivingKpis.map((name) => {
            const k = hackbench.kpis?.[name];
            return (
              <li key={name} className="sub-label">
                {name}: Δ {fmt(k?.diff)} · 95% CI [{fmt(k?.ci?.[0])}, {fmt(k?.ci?.[1])}] vs
                tolerance ±{fmt(k?.tolerance)}
              </li>
            );
          })}
        </ul>
      )}
      {agree === false && (
        <div className="disagree-banner">
          Methods disagree: Parallax calls <strong>{parallaxState}</strong> on whole micrographs;
          HackBench calls <strong>{hackbench.verdict?.toUpperCase()}</strong> on per-tile KPI
          statistics. The two methods test different units of analysis (micrograph vs. tile), so
          an exact match isn't expected — treat this as two independent readings, not a
          contradiction to resolve by picking one.
        </div>
      )}
      {agree === true && <p className="sub-label">Both methods agree on this batch.</p>}
    </section>
  );
}
