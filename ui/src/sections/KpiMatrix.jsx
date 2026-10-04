// Our data contract is per-batch x per-KPI (mean/CI/tolerance), not the
// template's per-micrograph x per-KPI z-scores (we have no per-micrograph
// observations - see spec §4). So this matrix's rows are KPIs, not
// micrographs; the sticky first column is the KPI name instead of a
// micrograph id.

function fmt(n, digits = 3) {
  return typeof n === "number" ? n.toFixed(digits) : "—";
}

export function KpiMatrix({ hackbench }) {
  if (!hackbench) return null;
  const kpis = Object.entries(hackbench.kpis ?? {});

  return (
    <section aria-label="KPI deviation matrix">
      <div className="section-head">
        <h2>
          <span className="num">02</span>KPI deviation matrix
        </h2>
        <div className="matrix-legend">
          <span>n_fov = {hackbench.n_fov}</span>
          <span className="glyph-warn">driving</span>
        </div>
      </div>
      <p className="sub-label">
        {kpis.length} KPIs acquired for this batch · row = batch mean vs baseline, with the 95%
        CI on the difference and the acceptance tolerance
      </p>
      <p className="swipe-hint" aria-hidden="true">
        Swipe the table sideways for all {kpis.length} KPIs →
      </p>
      <div className="matrix-scroll">
        <table className="matrix">
          <thead>
            <tr>
              <th scope="col">KPI</th>
              <th scope="col">Role</th>
              <th scope="col">Baseline</th>
              <th scope="col">Batch</th>
              <th scope="col">Δ</th>
              <th scope="col">95% CI</th>
              <th scope="col">Tolerance</th>
            </tr>
          </thead>
          <tbody>
            {kpis.map(([name, k]) => (
              <tr key={name} className={k.driving ? "driving" : ""}>
                <th scope="row">
                  {name}
                  {k.driving && (
                    <>
                      {" "}
                      <span className="glyph-warn" title="Drives the verdict">
                        ✕ driving
                      </span>
                    </>
                  )}
                </th>
                <td>
                  <span className="role-badge">{k.role ?? "—"}</span>
                </td>
                <td>{fmt(k.base_mean)}</td>
                <td>{fmt(k.batch_mean)}</td>
                <td>{fmt(k.diff)}</td>
                <td>
                  [{fmt(k.ci?.[0])}, {fmt(k.ci?.[1])}]
                </td>
                <td>±{fmt(k.tolerance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
