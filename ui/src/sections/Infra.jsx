function PreregRow({ label, prereg }) {
  if (!prereg) {
    return (
      <div>
        <span>{label}</span>
        <span className="status-skipped">no prereg tag recorded</span>
      </div>
    );
  }
  return (
    <div>
      <span>{label}</span>
      <span>
        <code>{prereg.tag}</code> · {prereg.sha?.slice(0, 10)} ·{" "}
        {prereg.created_at ? new Date(prereg.created_at).toISOString() : "—"}
        {prereg.release_url ? (
          <>
            {" "}
            · <a href={prereg.release_url}>release</a>
          </>
        ) : (
          " · release pending"
        )}
      </span>
    </div>
  );
}

export function InfraPanel({ cycle, prereg }) {
  return (
    <section aria-label="Infrastructure">
      <div className="section-head">
        <h2>
          <span className="num">07</span>Infrastructure
        </h2>
      </div>
      <div className="panel-grid">
        <div className="tile">
          <h3>Run cycle</h3>
          {cycle ? (
            <>
              <ul className="stage-list">
                {cycle.stages?.map((s) => (
                  <li key={s.name}>
                    <span>
                      {s.name} ({s.status}
                      {s.reason ? `: ${s.reason}` : ""})
                    </span>
                    <span>{typeof s.seconds === "number" ? `${s.seconds}s` : "—"}</span>
                  </li>
                ))}
              </ul>
              <p className="sub-label">journal_sha: {cycle.journal_sha?.slice(0, 16)}…</p>
            </>
          ) : (
            <p className="status-skipped">no cycle data recorded</p>
          )}
        </div>
        <div className="tile">
          <h3>Pre-registration</h3>
          <div className="kv-list">
            <PreregRow label="HackBench" prereg={prereg?.hackbench} />
            <PreregRow label="Parallax" prereg={prereg?.parallax} />
          </div>
        </div>
      </div>
    </section>
  );
}
