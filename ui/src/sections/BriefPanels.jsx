import { heroBlock } from "../lib/brief.js";

function ClaimList({ items }) {
  return (
    <dl className="fact-list">
      {items.map((c) => (
        <div key={c.id}>
          <dt>
            {c.label}
            {c.state_label ? ` · ${c.state_label}` : ""}
          </dt>
          <dd>{c.text}</dd>
        </div>
      ))}
    </dl>
  );
}

export function SupportAndLimits({ brief }) {
  const support = heroBlock(brief, "data_support");
  const limits = heroBlock(brief, "limits");
  if (!support && !limits) return null;

  return (
    <section aria-label="Data support and limits">
      <div className="brief-grid">
        <div>
          <div className="section-head">
            <h2>
              <span className="num">03</span>
              {support?.title ?? "Data support"}
            </h2>
          </div>
          <div className="brief-state">{support?.state}</div>
          {support?.qualifier && <div className="brief-qualifier">{support.qualifier}</div>}
          <ClaimList items={support?.items ?? []} />
        </div>
        <div>
          <div className="section-head">
            <h2>
              <span className="num">04</span>
              {limits?.title ?? "Limits"}
            </h2>
          </div>
          <div className="brief-state">{limits?.state}</div>
          <ClaimList items={limits?.items ?? []} />
        </div>
      </div>
    </section>
  );
}

export function NextCapture({ brief }) {
  const policy = heroBlock(brief, "acquisition_policy");
  if (!policy) return null;

  return (
    <section aria-label="Next capture">
      <div className="section-head">
        <h2>
          <span className="num">05</span>Next capture
        </h2>
      </div>
      <p className="sub-label">
        policy: <strong>{policy.state}</strong> · run in order
        {policy.sequence ? ` · ${policy.sequence}` : ""}
      </p>
      <ol className="policy-steps">
        {policy.items.map((c, i) => (
          <li key={c.id}>
            <span className="kind-badge">{(c.status ?? "").toUpperCase()}</span>
            <span>
              {i + 1}. {c.text}
            </span>
          </li>
        ))}
      </ol>
      {policy.later?.length > 0 && (
        <p className="policy-later">
          THEN, LOWER TIERS → {policy.later.map((l) => l.step).join(" · ")}
        </p>
      )}
    </section>
  );
}
