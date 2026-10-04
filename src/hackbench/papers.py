"""Paperclip literature lookups: search + claim support, defensive parsing, capped calls.

Base `https://paperclip.gxl.ai/api/v1`, header `X-API-Key`. Field names beyond `query` /
`num_results` are unverified (the `/claims/support` response schema is unspecified in
Paperclip's own `openapi.json`, checked 2026-10-04), so parsing degrades to empty results
rather than raising. Only ids/titles/DOIs/URLs/citation URLs are kept, never full text.
"""

import os
from collections.abc import Mapping
from typing import Any

import httpx

from hackbench.journal import Journal

BASE_URL = "https://paperclip.gxl.ai/api/v1"
MAX_CALLS = 10

QUERIES = [
    "EDS spatial resolution for sub-micron particles at 5-10 kV",
    "BSE separability of Si / SiOx / carbon-coated Si",
    "representative area or correlation length for graphite porosity",
    "supplier specifications for fine Si/SiOx additives",
]
CLAIMS = [
    "Calendering reduces lithium-ion cathode porosity",
    "LLM agents shown fabricated but professional-looking evidence over-commit to verdicts",
]


def _api_key() -> str | None:
    return os.environ.get("PAPERCLIP_API_KEY") or os.environ.get("GXL_API_KEY")


def _hit(raw: Mapping[str, Any]) -> dict[str, Any]:
    url = raw.get("url")
    return {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "doi": raw.get("doi"),
        "url": url,
        "citation_url": raw.get("citation_url") or url,
    }


def _hits_in(body: Mapping[str, Any], *keys: str) -> list[dict[str, Any]]:
    for key in keys:
        value = body.get(key)
        if isinstance(value, list):
            return [_hit(v) for v in value if isinstance(v, dict)]
    return []


def _post(
    http: httpx.Client, journal: Journal, tool: str, path: str, payload: Mapping[str, Any]
) -> dict[str, Any]:
    """POST one call, journal it, and degrade to `{}` on any transport/parse failure."""
    try:
        r = http.post(path, json=payload)
    except httpx.HTTPError as exc:
        journal.append({"tool": tool, **payload, "error": str(exc)})
        return {}
    journal.append({"tool": tool, **payload, "status_code": r.status_code})
    if r.status_code != 200:
        return {}
    try:
        body = r.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def run_papers(
    journal: Journal, client: httpx.Client | None = None, max_calls: int = MAX_CALLS
) -> dict[str, Any]:
    """Four literature queries plus two claim checks; always journaled, never raises."""
    key = _api_key()
    if not key:
        return {"status": "skipped", "reason": "PAPERCLIP_API_KEY/GXL_API_KEY unset"}

    own_client = client is None
    http = client or httpx.Client(base_url=BASE_URL, headers={"X-API-Key": key}, timeout=10.0)
    calls = 0
    hits: list[dict[str, Any]] = []
    claims_out: list[dict[str, Any]] = []
    try:
        for query in QUERIES:
            if calls >= max_calls:
                break
            calls += 1
            body = _post(
                http, journal, "paperclip.search", "/search", {"query": query, "num_results": 5}
            )
            hits.extend(_hits_in(body, "results", "hits", "data"))

        for claim in CLAIMS:
            if calls >= max_calls:
                break
            calls += 1
            body = _post(
                http, journal, "paperclip.claims_support", "/claims/support", {"claim": claim}
            )
            claims_out.append(
                {
                    "claim": claim,
                    "support": _hits_in(body, "support", "supporting", "evidence_for", "for"),
                    "against": _hits_in(body, "against", "refuting", "evidence_against"),
                }
            )
    finally:
        if own_client:
            http.close()

    return {"status": "ok", "queries": list(QUERIES), "hits": hits, "claims": claims_out}
