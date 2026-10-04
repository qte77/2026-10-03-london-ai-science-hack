// Generic reader for the teammate's decision-brief/1 schema (see
// decision_brief.Batch_*.json). We never hardcode entity ids or per-batch
// prose: every batch's hero blocks list their own claim ids, and every
// claim already carries its own rendered `text`/`fact` strings plus
// structured `values`/`fact_values` ({ref:{path}, value}) we can look up by
// ref-path suffix. This lets one renderer work for Batch_1 (REFERENCE,
// different block titles/claim set) and Batch_2/3 (ACCEPT/REJECT) alike.

export function claimsIndex(brief) {
  const map = new Map();
  for (const c of brief?.claims ?? []) map.set(c.id, c);
  return map;
}

export function heroBlock(brief, key) {
  const claimsById = claimsIndex(brief);
  const block = brief?.hero?.[key];
  if (!block) return null;
  const items = (block.claims ?? []).map((id) => claimsById.get(id)).filter(Boolean);
  const footer = block.footer ? claimsById.get(block.footer) : null;
  return { ...block, items, footer };
}

/** Scan one claim (or a list of claims) for a fact_value/value whose ref.path
 * ends with `suffix`. Returns the raw value, or undefined if absent. */
export function findFactValue(claimOrList, suffix) {
  const claims = Array.isArray(claimOrList) ? claimOrList : [claimOrList];
  for (const c of claims) {
    if (!c) continue;
    const pool = [...(c.fact_values ?? []), ...(c.values ?? [])];
    for (const fv of pool) {
      const path = fv.ref?.path;
      if (path === suffix || path?.endsWith(`.${suffix}`)) return fv.value;
    }
  }
  return undefined;
}

export function decisionStats(brief) {
  const claimsById = claimsIndex(brief);
  const verdictClaim = claimsById.get("decision.verdict");
  const scopeClaim = claimsById.get("decision.scope");
  return {
    p: findFactValue(verdictClaim, "p_batch"),
    alpha: findFactValue(verdictClaim, "thresholds.alpha_reject"),
    rule: verdictClaim?.details?.[0]?.text ?? null,
    headline: verdictClaim?.text ?? null,
    fact: verdictClaim?.fact ?? null,
    scope: scopeClaim?.text ?? null,
  };
}

/** The brief's structural leave-one-out counterfactual (entities[].leverage),
 * if this batch has one: {entity, verdict, p}. Null for batches with no
 * pivotal/consistent-out entity (e.g. ACCEPT with no deviation). */
export function findCounterfactual(brief) {
  for (const c of brief?.claims ?? []) {
    const verdict = findFactValue(c, "leverage.verdict_without");
    const p = findFactValue(c, "leverage.p_without");
    if (verdict !== undefined && p !== undefined) {
      const entity = findFactValue(c, "entities.id") ?? c.scope;
      return { entity, verdict, p };
    }
  }
  return null;
}

export function toneForState(state) {
  const s = (state ?? "").toUpperCase();
  if (s.includes("REJECT")) return "crit";
  if (s.includes("INVESTIGATE")) return "warn";
  if (s.includes("ACCEPT")) return "ok";
  return "ref"; // REFERENCE and anything unrecognised
}
