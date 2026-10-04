import { safeUrl } from "../lib/safeUrl.js";

const pct = (x) => (typeof x === "number" ? `${Math.round(x * 100)}%` : "—");
const short = (id) => String(id ?? "").replace(/^(paper|marker|capability):/, "");

function Skipped({ reason }) {
  return <p className="status-skipped">skipped: {reason}</p>;
}

// The literature loop as it actually ran: queries -> papers -> claim checks -> Paperclip vs
// curated -> LLM judge of Paperclip's output. Ids, titles and verdicts only; no full text.
export function LiteraturePanel({ papers, paperJudge }) {
  const judge = paperJudge?.judge;
  const rows = paperJudge?.rows ?? [];
  return (
    <section aria-label="Literature loop">
      <div className="section-head">
        <h2>
          <span className="num">07</span>Literature loop
        </h2>
        <p className="section-sub">
          Agents search the literature (GXL Paperclip), check claims, and an LLM judge grades the
          search tool's own output.
        </p>
      </div>
      <div className="panel-grid">
        <div className="tile">
          <h3>1 · Papers found</h3>
          {papers?.status !== "ok" ? (
            <Skipped reason={papers?.reason ?? "no data"} />
          ) : (
            <>
              <p>
                {papers.queries?.length ?? 0} queries → {papers.hits?.length ?? 0} papers
              </p>
              <ul>
                {(papers.hits ?? []).slice(0, 8).map((h) => (
                  <li key={h.id}>
                    {safeUrl(h.citation_url ?? h.url) ? (
                      <a href={safeUrl(h.citation_url ?? h.url)} rel="noopener noreferrer">
                        {h.title}
                      </a>
                    ) : (
                      h.title
                    )}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <div className="tile">
          <h3>2 · Claims checked</h3>
          {papers?.status !== "ok" ? (
            <Skipped reason={papers?.reason ?? "no data"} />
          ) : (
            <div className="kv-list">
              {(papers.claims ?? []).map((c) => (
                <div key={c.claim}>
                  <span>{c.claim}</span>
                  <span>
                    for {c.support?.length ?? 0} · against {c.against?.length ?? 0}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="tile">
          <h3>3 · Paperclip vs curated papers</h3>
          {paperJudge?.status !== "ok" ? (
            <Skipped reason={paperJudge?.reason ?? "no data"} />
          ) : (
            <div className="kv-list">
              <div>
                <span>calls / errors</span>
                <span>
                  {paperJudge.n} / {paperJudge.errors}
                </span>
              </div>
              <div>
                <span>our papers found in Paperclip</span>
                <span>{pct(paperJudge.paperclip_resolved_rate)}</span>
              </div>
              <div>
                <span>Paperclip direction = curated</span>
                <span>{pct(paperJudge.paperclip_agreement)}</span>
              </div>
            </div>
          )}
        </div>

        <div className="tile">
          <h3>4 · LLM judge of Paperclip</h3>
          {judge?.status !== "ok" ? (
            <Skipped reason={judge?.reason ?? paperJudge?.reason ?? "no data"} />
          ) : (
            <div className="kv-list">
              <div>
                <span>judge</span>
                <span>
                  {judge.provider} · {judge.model}
                </span>
              </div>
              <div>
                <span>calls / errors</span>
                <span>
                  {judge.n} / {judge.errors}
                </span>
              </div>
              <div>
                <span>evidence grounded</span>
                <span>{pct(judge.grounded_rate)}</span>
              </div>
              <div>
                <span>judge = curated</span>
                <span>{pct(judge.judge_agreement)}</span>
              </div>
              <div>
                <span>judge = Paperclip</span>
                <span>{pct(judge.judge_paperclip_agreement)}</span>
              </div>
              <div>
                <span>Brier (calibration)</span>
                <span>{typeof judge.brier === "number" ? judge.brier.toFixed(3) : "—"}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {rows.length > 0 && (
        <div className="matrix-scroll" role="region" aria-label="Per-claim verdicts" tabIndex={0}>
          <p className="swipe-hint">Swipe the table sideways for all columns →</p>
          <table className="matrix">
            <thead>
              <tr>
                <th scope="col">Paper</th>
                <th scope="col">Target</th>
                <th scope="col">Curated</th>
                <th scope="col">Paperclip</th>
                <th scope="col">Judge</th>
                <th scope="col">Grounded</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={`${r.paper_id}-${r.target}-${i}`}>
                  <th scope="row">{short(r.paper_id)}</th>
                  <td>{short(r.target)}</td>
                  <td>{r.curated}</td>
                  <td>{r.paperclip}</td>
                  <td>
                    {r.judge
                      ? `${r.judge.direction} (${Math.round((r.judge.confidence ?? 0) * 100)}%)`
                      : "—"}
                  </td>
                  <td>{r.judge ? (r.judge.grounded ? "yes" : "no") : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
