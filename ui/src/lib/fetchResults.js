const SCHEMA = "hackbench-results/1";

// Relative to the page at <site>/results/, so it also works when the site lives under a sub-path.
const RESULTS_URL = "../v1/results";

async function fetchLive() {
  const res = await fetch(RESULTS_URL, { headers: { Accept: "application/json" } });
  if (!res.ok) {
    throw new Error(`GET /v1/results -> ${res.status}`);
  }
  const data = await res.json();
  if (data.schema !== SCHEMA) {
    throw new Error(`Unexpected schema "${data.schema}", expected "${SCHEMA}"`);
  }
  return data;
}

/** Fetch the live results contract. In dev builds only, fall back to the
 * bundled sample fixture when the backend isn't running yet - never in
 * production, where a failed fetch must surface as a visible error state. */
export async function loadResults() {
  try {
    return await fetchLive();
  } catch (err) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.warn("[dev] /v1/results unavailable, using sample-results.json:", err);
      const mod = await import("../sample-results.json");
      return mod.default;
    }
    throw err;
  }
}
